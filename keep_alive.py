import logging
from flask import Flask, request, jsonify

# Suppress noisy routing logs
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
