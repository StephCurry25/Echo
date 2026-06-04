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
class EchoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        if not self.reminder_scheduler.is_running():
            self.reminder_scheduler.start()

bot = EchoBot()

@bot.event
async def on_ready():
    print(f"🚀 𝐄𝐜𝐡𝐨 IS ONLINE | {bot.user.name}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="!cmds"))

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # AFK Listener
    if message.mentions:
        for member in message.mentions:
            db = sqlite3.connect('edith_mainframe.db')
            cursor = db.cursor()
            cursor.execute("SELECT reason FROM afk WHERE user_id=?", (member.id,))
            res = cursor.fetchone()
            db.close()
            if res:
                await message.channel.send(f"🕶️ **𝐄𝐜𝐡𝐨:** Target **{member.display_name}** is currently inactive. Status: *{res[0]}*")
    
    # Auto-clear AFK on speak
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    db.commit()
    db.close()
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("SELECT newcomer_role_name, welcome_dm FROM server_settings WHERE guild_id=?", (member.guild.id,))
    res = cursor.fetchone()
    db.close()
    
    if res:
        # Assign Role
        role = discord.utils.get(member.guild.roles, name=res[0])
        if role: await member.add_roles(role)
        # Send DM Info
        try:
            await member.send(f"🕶️ **𝐄𝐜𝐡𝐨 Briefing:** {res[1]}")
        except: pass

@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# Commands
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ **𝐄𝐜𝐡𝐨:** Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ 𝐄𝐜𝐡𝐨 MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup [role] [message]`, `!ping`, `!cmds`, `!afk [reason]`", inline=False)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!unstore`, `!delete`", inline=False)
    embed.add_field(name="⏰ ALERTS", value="`!remind [mins] [reason]`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx, role_name: str, *, dm_message: str):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('REPLACE INTO server_settings (guild_id, newcomer_role_name, welcome_dm) VALUES (?, ?, ?)', (ctx.guild.id, role_name, dm_message))
    db.commit()
    db.close()
    await ctx.send(f"✅ **𝐄𝐜𝐡𝐨:** Protocols updated. Newcomers will receive role **{role_name}** and a custom DM briefing.")

@bot.command()
async def afk(ctx, *, reason: str = "Away"):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('REPLACE INTO afk (user_id, reason) VALUES (?, ?)', (ctx.author.id, reason))
    db.commit()
    db.close()
    await ctx.send(f"🕶️ **𝐄𝐜𝐡𝐨:** Status engaged. You are now AFK: *{reason}*")

@bot.command()
async def remind(ctx, minutes: int, *, reason: str):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    end = (datetime.now(TOKYO_TZ) + timedelta(minutes=minutes)).isoformat()
    cursor.execute('INSERT INTO reminders (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)', (OWNER_ID, ctx.channel.id, end, reason))
    db.commit()
    db.close()
    await ctx.send("⏰ **𝐄𝐜𝐡𝐨:** Reminder set.")

@bot.command()
async def store(ctx, k: str, *, val: str):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('REPLACE INTO storage (key, content) VALUES (?, ?)', (k.lower(), val))
    db.commit()
    db.close()
    await ctx.send(f"🔐 **𝐄𝐜𝐡𝐨:** Stored `{k}`.")

@bot.command()
async def unstore(ctx, k):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    db.close()
    await ctx.send(f"📦 **𝐄𝐜𝐡𝐨:** Data: {res[0]}" if res else "❌ **𝐄𝐜𝐡𝐨:** Not found.")

@bot.command()
async def delete(ctx, k):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    db.close()
    await ctx.send(f"🗑️ **𝐄𝐜𝐡𝐨:** Purged `{k}`")

@tasks.loop(seconds=5)
async def reminder_scheduler():
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('SELECT id, channel_id, end_time, reason FROM reminders')
    for row in cursor.fetchall():
        if datetime.now(TOKYO_TZ) >= datetime.fromisoformat(row[2]):
            channel = bot.get_channel(row[1])
            if channel: await channel.send(f"🚨 **𝐄𝐜𝐡𝐨 ALERT:** {row[3]}")
            cursor.execute('DELETE FROM reminders WHERE id = ?', (row[0],))
            db.commit()
    db.close()

async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, channel_id INTEGER, end_time TEXT, reason TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, newcomer_role_name TEXT, welcome_dm TEXT)')
    db.commit()
    db.close()

    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    
    async with bot:
        await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
