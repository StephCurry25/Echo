import os
import logging
from flask import Flask, request, jsonify

# Disable default Flask logging to keep console clean
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

# We removed the manual thread starter functions here 
# because Gunicorn will now manage the web process directly.import os
import logging
from flask import Flask, request, jsonify

# Disable default Flask logging to keep console clean
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

# We removed the manual thread starter functions here 
# because Gunicorn will now manage the web process directly.
