import logging
from flask import Flask, request, jsonify

# Keep the console output clear of standard web requests
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

def run_server():
    # Bind directly to Render's public network port
    app.run(host='0.0.0.0', port=8080)import logging
from flask import Flask, request, jsonify

# Keep the console output clear of standard web requests
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

def run_server():
    # Bind directly to Render's public network port
    app.run(host='0.0.0.0', port=8080
