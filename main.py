import os
import discord
import sqlite3
import asyncio
import logging
from flask import Flask, jsonify
from discord.ext import commands
import werkzeug.serving

# Configuration
TOKEN = os.environ.get('TOKEN')
PORT = 8080

# Bot Initialization with all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

app = Flask('')

@app.route('/')
def home():
    return jsonify({"status": "online"}), 200

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f"🚀 𝐄𝐜𝐡𝐨 IS ONLINE")

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
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("SELECT newcomer_role_name, welcome_dm FROM server_settings WHERE guild_id=?", (member.guild.id,))
    res = cursor.fetchone()
    db.close()
    if res:
        role = discord.utils.get(member.guild.roles, name=res[0])
        if role: await member.add_roles(role)
        try:
            await member.send(f"🕶️ **𝐄𝐜𝐡𝐨 Briefing:** {res[1]}")
        except: pass

# --- COMMANDS ---
@bot.command()
async def setup(ctx, role_name: str, *, dm_message: str):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('REPLACE INTO server_settings (guild_id, newcomer_role_name, welcome_dm) VALUES (?, ?, ?)', 
                   (ctx.guild.id, role_name, dm_message))
    db.commit()
    db.close()
    await ctx.send(f"✅ **𝐄𝐜𝐡𝐨:** Protocol locked. Newcomers will be assigned **{role_name}** and sent a briefing DM.")

@bot.command()
async def afk(ctx, *, reason: str = "Away"):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('REPLACE INTO afk (user_id, reason) VALUES (?, ?)', (ctx.author.id, reason))
    db.commit()
    db.close()
    await ctx.send(f"🕶️ **𝐄𝐜𝐡𝐨:** Status engaged. You are now AFK: *{reason}*")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided."):
    await member.kick(reason=reason)
    await ctx.send(f"✅ **𝐄𝐜𝐡𝐨:** {member.name} has been removed.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided."):
    await member.ban(reason=reason)
    await ctx.send(f"✅ **𝐄𝐜𝐡𝐨:** {member.name} has been exiled.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def sban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.ban(user, reason="Shadow Ban protocol engaged.")
    await ctx.send(f"✅ **𝐄𝐜𝐡𝐨:** {user.name} has been shadow-banned.")

# --- MAIN ---
async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, newcomer_role_name TEXT, welcome_dm TEXT)')
    db.commit()
    db.close()
    
    # Run server and bot
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
