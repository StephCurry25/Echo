import os
import logging
from flask import Flask, request, jsonify

# Suppress noisy routing logs in the Render console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return jsonify({
        "status": "online",
        "system": "E.D.I.T.H. Mainframe",
        "origin_verified": client_ip
    }), 200

@app.route('/pulse')
def pulse():
    return "PULSE_OK", 200

def run_server():
    # Render assigns a dynamic port via environment variables. We must capture it.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
