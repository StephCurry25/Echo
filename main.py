import os
import discord
import sqlite3
import asyncio
from discord.ext import commands
from flask import Flask, jsonify
import werkzeug.serving

TOKEN = os.environ.get('TOKEN')
PORT = 8080
app = Flask('')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# --- AUTOMATIC AFK REMOVAL ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Auto-remove AFK status
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("SELECT reason FROM afk WHERE user_id=?", (message.author.id,))
    res = cursor.fetchone()
    if res:
        cursor.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
        db.commit()
        await message.channel.send(f"🕶️ **𝐄𝐜𝐡𝐨:** Welcome back, {message.author.mention}! Your AFK status has been cleared.")
    db.close()

    # AFK Ping Listener (Check if someone is AFK when mentioned)
    if message.mentions:
        for member in message.mentions:
            db = sqlite3.connect('edith_mainframe.db')
            cursor = db.cursor()
            cursor.execute("SELECT reason FROM afk WHERE user_id=?", (member.id,))
            res = cursor.fetchone()
            db.close()
            if res:
                await message.channel.send(f"🕶️ **𝐄𝐜𝐡𝐨:** This person is AFK and the reason is: *{res[0]}*")

    await bot.process_commands(message)

# --- SETUP WIZARD (Keep your existing SetupWizard class and commands) ---
# ... (Ensure your SetupWizard and commands !role, !msg remain here)

async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, role_name TEXT, welcome_dm TEXT)')
    db.commit()
    db.close()
    
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
