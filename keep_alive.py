import logging
from flask import Flask, request, jsonify
from threading import Thread

# Disable default Flask startup messages to keep E.D.I.T.H.'s console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    client_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown Ping Engine')
    
    return jsonify({
        "status": "online",
        "system": "E.D.I.T.H. Mainframe",
        "origin_verified": client_ip,
        "agent": user_agent
    }), 200

@app.route('/pulse')
def pulse():
    return "PULSE_OK", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server_thread = Thread(target=run, daemon=True)
    server_thread.start()
    print("🌐 Keep-Alive Web Server injected. Ready for Cloudflare edge routing.")
