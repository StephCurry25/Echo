import os
import discord
import sqlite3
import asyncio
import logging
from flask import Flask, jsonify
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import werkzeug.serving

# Configuration
TOKEN = os.environ.get('TOKEN')
PORT = 8080
OWNER_ID = 1219266886143967245
TOKYO_TZ = timezone(timedelta(hours=9))

# Setup Flask
app = Flask('')
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return jsonify({"status": "online", "port": PORT}), 200

# Setup Bot
class EdithBot(commands.Bot):
    def __init__(self):
        # We use all intents; ensure they are enabled in Discord Developer Portal
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        if not self.reminder_scheduler.is_running():
            self.reminder_scheduler.start()

bot = EdithBot()

@bot.event
async def on_ready():
    print(f"🚀 E.D.I.T.H. IS ONLINE | {bot.user.name}")
    # Force the UI to show 'Online'
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="!cmds"))
    print(f"📡 Status set to Online. Connected to {len(bot.guilds)} servers.")

@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# Commands
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cmds`", inline=False)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`", inline=False)
    embed.add_field(name="⏰ ALERTS", value="`!remind [mins] [reason]`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    cat = await ctx.guild.create_category(name="Security")
    await ctx.guild.create_text_channel('entry-gate', category=cat)
    await ctx.guild.create_text_channel('war-room', category=cat)
    await ctx.send("✅ Security Sectors Configured.")

@bot.command()
async def remind(ctx, minutes: int, *, reason: str):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    end = (datetime.now(TOKYO_TZ) + timedelta(minutes=minutes)).isoformat()
    cursor.execute('INSERT INTO reminders (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)', (OWNER_ID, ctx.channel.id, end, reason))
    db.commit()
    db.close()
    await ctx.send("⏰ Reminder Set.")

@bot.command()
async def store(ctx, k: str, *, val: str):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('REPLACE INTO storage (key, content) VALUES (?, ?)', (k.lower(), val))
    db.commit()
    db.close()
    await ctx.send(f"🔐 Stored `{k}`.")

@bot.command()
async def unstore(ctx, k):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    db.close()
    await ctx.send(f"📦 Data: {res[0]}" if res else "❌ Not found.")

@bot.command()
async def delete(ctx, k):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    db.close()
    await ctx.send(f"🗑️ Purged `{k}`")

# Loops
@tasks.loop(seconds=5)
async def reminder_scheduler():
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('SELECT id, channel_id, end_time, reason FROM reminders')
    for row in cursor.fetchall():
        if datetime.now(TOKYO_TZ) >= datetime.fromisoformat(row[2]):
            channel = bot.get_channel(row[1])
            if channel: await channel.send(f"🚨 **ALERT:** {row[3]}")
            cursor.execute('DELETE FROM reminders WHERE id = ?', (row[0],))
            db.commit()
    db.close()

# Main entry
async def main():
    # Database Init
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, channel_id INTEGER, end_time TEXT, reason TEXT)')
    db.commit()
    db.close()

    # Start Flask on 8080
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    
    # Start Bot
    async with bot:
        await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
