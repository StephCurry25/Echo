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

app = Flask('')
# Set up intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@app.route('/')
def home():
    return jsonify({"status": "online", "port": PORT}), 200

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
    
    # Clear AFK
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    db.commit()
    db.close()
    await bot.process_commands(message)

# --- Moderation Commands ---
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided."):
    await member.kick(reason=reason)
    await ctx.send(f"✅ **𝐄𝐜𝐡𝐨:** {member.name} has been removed from the sector.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided."):
    await member.ban(reason=reason)
    await ctx.send(f"✅ **𝐄𝐜𝐡𝐨:** {member.name} has been permanently exiled.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def sban(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason="Shadow Ban protocol engaged.")
        await ctx.send(f"✅ **𝐄𝐜𝐡𝐨:** User {user.name} has been shadow-banned.")
    except Exception as e:
        await ctx.send(f"❌ **𝐄𝐜𝐡𝐨:** Unable to execute shadow ban. {e}")

# --- Setup & Other Commands remain as previously defined ---

async def main():
    # Database initialization
    db = sqlite3.connect('echo_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, newcomer_role_name TEXT, welcome_dm TEXT)')
    db.commit()
    db.close()

    # Start Flask on 8080
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    
    async with bot:
        await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
