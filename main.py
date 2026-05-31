import os
import discord
import sqlite3
import asyncio
import logging
from flask import Flask, request, jsonify
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import werkzeug.serving

# Force the port to 8080 explicitly
os.environ["PORT"] = "8080"

# ==============================================================================
# --- DATABASE & CONFIG ---
# ==============================================================================
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, channel_id INTEGER, end_time TEXT, reason TEXT)')
db.commit()

TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245
TOKYO_TZ = timezone(timedelta(hours=9))

app = Flask('')
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return jsonify({"status": "active", "port": 8080}), 200

# ==============================================================================
# --- BOT CORE ---
# ==============================================================================
class EdithBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)
        self.lockdown_active = False

    async def setup_hook(self):
        await self.tree.sync()
        if not self.reminder_scheduler.is_running():
            self.reminder_scheduler.start()

bot = EdithBot()

@bot.event
async def on_ready():
    print(f"🚀 E.D.I.T.H. ONLINE on Port 8080 | {bot.user.name}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="!cmds for help"))

@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# ==============================================================================
# --- COMMAND LIST ---
# ==============================================================================
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cmds`", inline=False)
    embed.add_field(name="📦 STORAGE", value="`!store <key> <val>`, `!storage`, `!unstore <key>`, `!delete <key>`", inline=False)
    embed.add_field(name="⏰ ALERTS", value="`!remind <minutes> <reason>`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False), ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
    cat = await ctx.guild.create_category(name="Security", overwrites=overwrites)
    await ctx.guild.create_text_channel('entry-gate', category=cat)
    await ctx.guild.create_text_channel('war-room', category=cat)
    await ctx.send("✅ Security Sectors Configured.")

@bot.command()
async def remind(ctx, minutes: int, *, reason: str):
    end_time = (datetime.now(TOKYO_TZ) + timedelta(minutes=minutes)).isoformat()
    cursor.execute('INSERT INTO reminders (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)', (OWNER_ID, ctx.channel.id, end_time, reason))
    db.commit()
    await ctx.send(f"⏰ Reminder set for {minutes} minutes.")

@bot.command()
async def store(ctx, k: str, *, val: str):
    cursor.execute('REPLACE INTO storage (key, content) VALUES (?, ?)', (k.lower(), val))
    db.commit()
    await ctx.send(f"🔐 Stored `{k}`.")

@bot.command()
async def unstore(ctx, k):
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    await ctx.send(f"📦 Data:\n{res[0]}" if res else "❌ Not found.")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    res = [r[0] for r in cursor.fetchall()]
    await ctx.send(f"🗄️ Index: {', '.join(res)}" if res else "Empty.")

@bot.command()
async def delete(ctx, k):
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    await ctx.send(f"🗑️ Purged `{k}`")

# ==============================================================================
# --- LOOPS & RUNTIME ---
# ==============================================================================
@tasks.loop(seconds=1)
async def reminder_scheduler():
    cursor.execute('SELECT id, channel_id, end_time, reason FROM reminders')
    for row in cursor.fetchall():
        if datetime.now(TOKYO_TZ) >= datetime.fromisoformat(row[2]):
            channel = bot.get_channel(row[1])
            if channel: await channel.send(f"🚨 **ALERT:** {row[3]}")
            cursor.execute('DELETE FROM reminders WHERE id = ?', (row[0],))
            db.commit()

async def main():
    port = 8080 # Hardcoded to your request
    server = werkzeug.serving.make_server('0.0.0.0', port, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    async with bot:
        await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
