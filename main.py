import os
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
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
class EchoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())

    async def setup_hook(self):
        await self.tree.sync() # Syncs slash commands

bot = EchoBot()

# --- MODERATION & SETUP ---
@bot.tree.command(name="setup", description="Configure newcomer role and welcome DM")
@app_commands.describe(role_name="Name of existing role", dm_msg="Welcome DM content")
async def setup(interaction: discord.Interaction, role_name: str, dm_msg: str):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('REPLACE INTO server_settings (guild_id, role_name, welcome_dm) VALUES (?, ?, ?)', 
                   (interaction.guild_id, role_name, dm_msg))
    db.commit()
    db.close()
    await interaction.response.send_message(f"✅ **𝐄𝐜𝐡𝐨:** Protocol locked. Newcomers will receive **{role_name}**.")

@bot.tree.command(name="afk", description="Set your AFK status")
async def afk(interaction: discord.Interaction, reason: str):
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute('REPLACE INTO afk (user_id, reason) VALUES (?, ?)', (interaction.user.id, reason))
    db.commit()
    db.close()
    await interaction.response.send_message(f"🕶️ **𝐄𝐜𝐡𝐨:** AFK status engaged: *{reason}*")

@bot.tree.command(name="sban", description="Shadow ban a user by ID")
async def sban(interaction: discord.Interaction, user_id: str):
    user = await bot.fetch_user(int(user_id))
    await interaction.guild.ban(user, reason="Shadow Ban protocol engaged.")
    await interaction.response.send_message(f"✅ **𝐄𝐜𝐡𝐨:** {user.name} has been shadow-banned.")

# --- LISTENERS ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    # AFK Ping Listener
    if message.mentions:
        for member in message.mentions:
            db = sqlite3.connect('edith_mainframe.db')
            cursor = db.cursor()
            cursor.execute("SELECT reason FROM afk WHERE user_id=?", (member.id,))
            res = cursor.fetchone()
            if res:
                await message.channel.send(f"🕶️ **𝐄𝐜𝐡𝐨:** Target **{member.display_name}** is currently inactive. Status: *{res[0]}*")
    await bot.process_commands(message)

# --- MAIN ---
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
