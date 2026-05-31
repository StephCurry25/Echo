import os
import discord
import sqlite3
import asyncio
import logging
from flask import Flask, request, jsonify
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from threading import Thread

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
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return jsonify({"status": "online", "system": "E.D.I.T.H. Mainframe", "origin_verified": client_ip}), 200

@app.route('/pulse')
def pulse():
    return "PULSE_OK", 200

def run_production_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# ==============================================================================
# --- BOT INITIALIZATION ---
# ==============================================================================
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
ROLE_NAME = "New Comer"
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
    print(f"🛰️ Mainframe Online: {bot.user.name}")

@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# ==============================================================================
# --- CORE COMMAND STRUCTURES ---
# ==============================================================================
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cmds`", inline=True)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`", inline=True)
    embed.add_field(name="⏰ ALERTS", value="`!remind [minutes] [reason]`", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    category = await ctx.guild.create_category(name="Security", overwrites=overwrites)
    gate = await ctx.guild.create_text_channel('entry-gate', category=category)
    logs = await ctx.guild.create_text_channel('war-room', category=category)
    await ctx.send(f"✅ Security Sectors Configured.")

@bot.command()
async def remind(ctx, minutes: int, *, reason: str):
    now_tokyo = datetime.now(TOKYO_TZ)
    end_time_str = (now_tokyo + timedelta(minutes=minutes)).isoformat()
    cursor.execute('INSERT INTO reminders (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)', (OWNER_ID, ctx.channel.id, end_time_str, reason))
    db.commit()
    await ctx.send(f"⏰ **Reminder Set.**")

@bot.command()
async def store(ctx, k: str = None):
    if not k: return await ctx.send("⚠️ Key required.")
    await ctx.send(f"🔐 **Storage block loaded:** Operational for block `{k}`.")

@bot.command()
async def unstore(ctx, k):
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    if res: await ctx.send(f"📦 Data:\n{res[0]}")
    else: await ctx.send("❌ Not found.")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    res = cursor.fetchall()
    keys = "\n".join([f"• {r[0]}" for r in res]) if res else "Empty."
    await ctx.send(embed=discord.Embed(title="🗄️ STORAGE INDEX", description=keys, color=0x3498db))

@bot.command()
async def delete(ctx, k):
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    await ctx.send(f"🗑️ Purged `{k}`")

# ==============================================================================
# --- RUNTIME AUTOMATION LOOPS ---
# ==============================================================================
@tasks.loop(seconds=1)
async def reminder_scheduler():
    now_tokyo = datetime.now(TOKYO_TZ)
    cursor.execute('SELECT id, channel_id, end_time, reason FROM reminders')
    for row in cursor.fetchall():
        rem_id, channel_id, end_time_str, reason = row
        if now_tokyo >= datetime.fromisoformat(end_time_str):
            channel = bot.get_channel(channel_id)
            if channel:
                try: await channel.send(content=f"🚨 **ALERT:** {reason}")
                except: pass
            cursor.execute('DELETE FROM reminders WHERE id = ?', (rem_id,))
            db.commit()

@tasks.loop(seconds=3)
async def lockdown_monitor():
    for guild in bot.guilds:
        owner = guild.get_member(OWNER_ID)
        if not owner: continue
        is_offline = (owner.status == discord.Status.offline)
        if is_offline and not bot.lockdown_active:
            bot.lockdown_active = True
            for channel in guild.text_channels:
                try: await channel.set_permissions(guild.default_role, send_messages=False)
                except: pass
        elif not is_offline and bot.lockdown_active:
            bot.lockdown_active = False
            for channel in guild.text_channels:
                try: await channel.set_permissions(guild.default_role, send_messages=None)
                except: pass

# ==============================================================================
# --- SYSTEM CONTROL TRACKS ---
# ==============================================================================
def run_bot_worker():
    try:
        print("🛰️ Opening background connection pipeline to Discord Gateway...")
        bot.run(TOKEN.strip())
    except Exception as e:
        print(f"❌ Core Gateway Crash: {e}")

if __name__ == "__main__":
    if TOKEN:
        # 1. Fire up Discord loop in background worker
        bot_thread = Thread(target=run_bot_worker)
        bot_thread.daemon = True
        bot_thread.start()

        # 2. Bind Flask server to main thread to block exit routine
        print("🌐 Anchoring production server context on assigned Render port.")
        run_production_server()
    else:
        print("❌ FATAL: TOKEN configuration environment missing.")
