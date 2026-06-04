import os
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
from flask import Flask
import werkzeug.serving

TOKEN = os.environ.get('TOKEN')
PORT = 8080
app = Flask('')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# --- GATE UI ---
class GateView(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"✅ {self.member.name} accepted.")
        self.stop()

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"❌ {self.member.name} denied.")
        self.stop()

# --- AFK & MESSAGE LISTENER ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    # 1. Handle Mentions of AFK Users
    if message.mentions:
        for member in message.mentions:
            db = sqlite3.connect('edith_mainframe.db')
            cursor = db.cursor()
            cursor.execute("SELECT reason FROM afk WHERE user_id=?", (member.id,))
            res = cursor.fetchone()
            db.close()
            if res:
                await message.channel.send(f"💤 {member.name} is AFK: {res[0]}")

    # 2. Auto-remove AFK
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    if cursor.rowcount > 0:
        await message.channel.send(f"👋 Welcome back, {message.author.mention}!")
    db.commit()
    db.close()

    await bot.process_commands(message)

# --- COMMANDS ---
@bot.tree.command(name="gate_test", description="Test the gate UI")
async def gate_test(interaction: discord.Interaction):
    # This simulates a user triggering the gate
    await interaction.response.send_message(f"New user {interaction.user.name} at the gate:", view=GateView(interaction.user))

@bot.tree.command(name="afk", description="Set AFK status")
async def afk(interaction: discord.Interaction, reason: str):
    db = sqlite3.connect('edith_mainframe.db')
    db.execute("INSERT OR REPLACE INTO afk (user_id, reason) VALUES (?, ?)", (interaction.user.id, reason))
    db.commit()
    db.close()
    await interaction.response.send_message(f"💤 You are now AFK: {reason}")

# --- EXECUTION ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Echo is online.")

async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.commit()
    db.close()
    
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
