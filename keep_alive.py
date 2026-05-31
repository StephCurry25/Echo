import logging
from flask import Flask, request, jsonify
from asgiref.wsgi import WsgiToAsgi

# Suppress noisy logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

flask_app = Flask('')

@flask_app.route('/')
def home():
    client_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown Ping Engine')
    return jsonify({
        "status": "online",
        "system": "E.D.I.T.H. Mainframe",
        "origin_verified": client_ip,
        "agent": user_agent
    }), 200

@flask_app.route('/pulse')
def pulse():
    return "PULSE_OK", 200

# Wrap the Flask WSGI app into an ASGI app so it fits into the async event loop
app = WsgiToAsgi(flask_app)import logging
from flask import Flask, request, jsonify
from asgiref.wsgi import WsgiToAsgi

# Suppress noisy logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

flask_app = Flask('')

@flask_app.route('/')
def home():
    client_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown Ping Engine')
    return jsonify({
        "status": "online",
        "system": "E.D.I.T.H. Mainframe",
        "origin_verified": client_ip,
        "agent": user_agent
    }), 200

@flask_app.route('/pulse')
def pulse():
    return "PULSE_OK", 200

# Wrap the Flask WSGI app into an ASGI app so it fits into the async event loop
app = WsgiToAsgi(flask_app)
