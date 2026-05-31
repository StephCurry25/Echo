import logging
from flask import Flask, request, jsonify
from threading import Thread

# Disable default Flask startup messages to keep E.D.I.T.H.'s console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    # Detect the true request origin behind Cloudflare's network proxy
    client_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown Ping Engine')
    
    # Return structured JSON to keep cron monitors and edge workers satisfied
    return jsonify({
        "status": "online",
        "system": "E.D.I.T.H. Mainframe",
        "origin_verified": client_ip,
        "agent": user_agent
    }), 200

@app.route('/pulse')
def pulse():
    """Alternative endpoint specifically for rigid uptime cron jobs."""
    return "PULSE_OK", 200

def run():
    # Bind to 0.0.0.0 and port 8080 as required by cloud runtime environments
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Starts the web server thread to intercept external cron pings."""
    server_thread = Thread(target=run, daemon=True)
    server_thread.start()
    print("🌐 Keep-Alive Web Server injected. Ready for Cloudflare edge routing.")
