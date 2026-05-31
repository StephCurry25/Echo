import os
import discord
import sqlite3
import asyncio
import logging
from flask import Flask, request, jsonify
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import werkzeug.serving

# ==============================================================================
# --- LOCAL STORAGE DATABASE ---
# ==============================================================================
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, channel_id INTEGER, end_time TEXT, reason TEXT)')
db.commit()

# ==============================================================================
# --- PRODUCTION FLASK ENGINE (KEEP ALIVE) ---
# ==============================================================================
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask('')

@app.route('/')
def home():
    return jsonify({"status": "online", "system": "E.D.I.T.H. Mainframe"}), 200

@app.route('/pulse')
def pulse():
    return "PULSE_OK", 200

# ==============================================================================
# --- BOT INITIALIZATION ---
# ==============================================================================
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
TOKYO_TZ = timezone(timedelta(hours=9))

class EdithBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)
        self.lockdown_active = False

    async def setup_hook(self):
        await self.tree.sync()
        if not self.lockdown_monitor.is_running():
            self.lockdown_monitor.start()
        if not self.reminder_scheduler.is_running():
            self.reminder_scheduler.start()

bot = EdithBot()

@bot.event
async def on_ready():
    print("=" * 40)
    print(f"🛰️ SUCCESS! Mainframe is active on Discord: {bot.user.name}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"👥 Connected to {len(bot.guilds)} servers.")
    for guild in bot.guilds:
        print(f"   -> Connected Server Name: {guild.name}")
    print("=" * 40)

@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# ==============================================================================
# --- CORE COMMANDS & LOOPS (Same as previous) ---
# ==============================================================================
# [Insert your existing command/task code here]

# ==============================================================================
# --- CONCURRENT ASYNC RUNTIME LIFECYCLE ---
# ==============================================================================
async def main():
    if not TOKEN:
        print("❌ FATAL: TOKEN configuration environment missing.")
        return

    # 1. Prepare and configure the asynchronous web server engine
    port = int(os.environ.get("PORT", 5000))
    web_server = werkzeug.serving.make_server('0.0.0.0', port, app, threaded=True)
    
    loop = asyncio.get_running_loop()
    print(f"🌐 Anchoring production server context on assigned Render port: {port}")
    loop.run_in_executor(None, web_server.serve_forever)

    # 2. Fire up the Discord Bot loop
    print("🛰️ Opening explicit gateway pipeline to Discord Gateway...")
    try:
        async with bot:
            await bot.start(TOKEN.strip())
    except Exception as e:
        print(f"❌ Core Gateway Crash: {e}")

if __name__ == "__main__":
    asyncio.run(main())
