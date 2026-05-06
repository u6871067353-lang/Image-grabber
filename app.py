from flask import Flask, request, jsonify, Response
import os
import json
import secrets
from datetime import datetime
import urllib.request

app = Flask(__name__)

# Erstelle notwendige Verzeichnisse
os.makedirs('tracking_data', exist_ok=True)

@app.route('/')
def index():
    """Direkt HTML zurückgeben (ohne Templates)"""
    return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IP Tracker - Bild-Link Tracking</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            padding: 40px;
            max-width: 600px;
            width: 100%;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            background: rgba(102, 126, 234, 0.05);
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .upload-area:hover {
            border-color: #764ba2;
            background: rgba(118, 75, 162, 0.1);
            transform: translateY(-2px);
        }

        .upload-area.dragover {
            border-color: #764ba2;
            background: rgba(118, 75, 162, 0.2);
        }

        .upload-icon {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 20px;
        }

        .upload-text {
            color: #666;
            font-size: 18px;
            margin-bottom: 10px;
        }

        .upload-subtext {
            color: #999;
            font-size: 14px;
        }

        .url-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            margin-bottom: 20px;
            transition: border-color 0.3s ease;
        }

        .url-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .webhook-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            margin-bottom: 30px;
            transition: border-color 0.3s ease;
        }

        .webhook-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .generate-btn {
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .generate-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        .generate-btn:active {
            transform: translateY(0);
        }

        .generate-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .result-container {
            margin-top: 30px;
            padding: 25px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 15px;
            border: 1px solid rgba(102, 126, 234, 0.2);
            display: none;
        }

        .result-link {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }

        .result-link input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            background: white;
        }

        .copy-btn {
            padding: 12px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 14px;
        }

        .copy-btn:hover {
            background: #764ba2;
        }

        .message {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: 500;
        }

        .message.success {
            background: rgba(76, 175, 80, 0.1);
            color: #4caf50;
            border: 1px solid rgba(76, 175, 80, 0.3);
        }

        .message.error {
            background: rgba(244, 67, 54, 0.1);
            color: #f44336;
            border: 1px solid rgba(244, 67, 54, 0.3);
        }

        .loading {
            display: none;
            text-align: center;
            color: #667eea;
            font-weight: 500;
        }

        .preview {
            margin-top: 20px;
            text-align: center;
        }

        .preview img {
            max-width: 100%;
            max-height: 200px;
            border-radius: 10px;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }

        @media (max-width: 768px) {
            .container {
                padding: 30px 20px;
            }
            
            h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 IP Tracker</h1>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">🖼️</div>
            <div class="upload-text">Bild-Link hier eingeben</div>
            <div class="upload-subtext">Füge einen Link zu einem Bild ein</div>
        </div>

        <input type="url" id="imageUrl" class="url-input" placeholder="https://example.com/bild.jpg" required>
        
        <input type="url" id="webhookUrl" class="webhook-input" placeholder="Discord Webhook URL" required>
        
        <button id="generateBtn" class="generate-btn">🚀 Tracking-Link generieren</button>
        
        <div id="loading" class="loading">⏳ Wird generiert...</div>
        
        <div id="resultContainer" class="result-container">
            <div class="message success">✅ Tracking-Link erfolgreich erstellt!</div>
            <div class="result-link">
                <input type="text" id="trackingLink" readonly>
                <button id="copyBtn" class="copy-btn">📋 Kopieren</button>
            </div>
            <div class="preview" id="preview"></div>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const imageUrlInput = document.getElementById('imageUrl');
        const webhookUrlInput = document.getElementById('webhookUrl');
        const generateBtn = document.getElementById('generateBtn');
        const loading = document.getElementById('loading');
        const resultContainer = document.getElementById('resultContainer');
        const trackingLinkInput = document.getElementById('trackingLink');
        const copyBtn = document.getElementById('copyBtn');
        const preview = document.getElementById('preview');

        // URL-Validierung
        function isValidUrl(string) {
            try {
                new URL(string);
                return true;
            } catch (_) {
                return false;
            }
        }

        // Bild-Vorschau
        function showPreview(url) {
            if (isValidUrl(url)) {
                preview.innerHTML = `<img src="${url}" alt="Vorschau" onerror="this.style.display='none'">`;
            } else {
                preview.innerHTML = '';
            }
        }

        // Event Listener
        imageUrlInput.addEventListener('input', () => {
            showPreview(imageUrlInput.value);
        });

        uploadArea.addEventListener('click', () => {
            imageUrlInput.focus();
        });

        generateBtn.addEventListener('click', async () => {
            const imageUrl = imageUrlInput.value.trim();
            const webhookUrl = webhookUrlInput.value.trim();

            if (!imageUrl || !webhookUrl) {
                showMessage('Bitte füllen Sie alle Felder aus', 'error');
                return;
            }

            if (!isValidUrl(imageUrl)) {
                showMessage('Bitte geben Sie eine gültige Bild-URL ein', 'error');
                return;
            }

            if (!isValidUrl(webhookUrl)) {
                showMessage('Bitte geben Sie eine gültige Webhook-URL ein', 'error');
                return;
            }

            // UI State
            generateBtn.disabled = true;
            loading.style.display = 'block';
            resultContainer.style.display = 'none';

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        image_url: imageUrl,
                        webhook_url: webhookUrl
                    })
                });

                const data = await response.json();

                if (data.success) {
                    trackingLinkInput.value = data.tracking_url;
                    resultContainer.style.display = 'block';
                    showMessage('Tracking-Link erfolgreich erstellt!', 'success');
                } else {
                    showMessage(data.error || 'Fehler bei der Erstellung', 'error');
                }
            } catch (error) {
                showMessage('Server-Fehler: ' + error.message, 'error');
            } finally {
                generateBtn.disabled = false;
                loading.style.display = 'none';
            }
        });

        copyBtn.addEventListener('click', () => {
            trackingLinkInput.select();
            document.execCommand('copy');
            copyBtn.textContent = '✅ Kopiert!';
            setTimeout(() => {
                copyBtn.textContent = '📋 Kopieren';
            },2000);
        });

        function showMessage(text, type) {
            const existingMessage = resultContainer.querySelector('.message');
            if (existingMessage) {
                existingMessage.remove();
            }
            
            const message = document.createElement('div');
            message.className = `message ${type}`;
            message.textContent = text;
            resultContainer.insertBefore(message, resultContainer.firstChild);
        }
    </script>
</body>
</html>
    """

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
