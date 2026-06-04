import os
import discord
import sqlite3
import asyncio
import logging
from discord.ext import commands
from flask import Flask, jsonify
import werkzeug.serving

# Configuration
TOKEN = os.environ.get('TOKEN')
PORT = 8080
app = Flask('')

@app.route('/')
def home():
    return jsonify({"status": "online"}), 200

# Setup Bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"🚀 𝐄𝐜𝐡𝐨 IS ONLINE")

# ... [Keep your existing SetupWizard and command logic here] ...

async def main():
    # Ensure DB file is created in a safe location
    db_path = 'edith_mainframe.db'
    db = sqlite3.connect(db_path)
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, role_name TEXT, welcome_dm TEXT)')
    db.commit()
    db.close()
    
    # Start Flask
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    
    if not TOKEN:
        print("CRITICAL: TOKEN not found in environment variables.")
        return

    try:
        await bot.start(TOKEN.strip())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
