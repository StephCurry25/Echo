import os
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
from flask import Flask, jsonify
import werkzeug.serving

TOKEN = os.environ.get('TOKEN')
PORT = 8080
app = Flask('')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# --- CORRECTED MODERATION COMMAND ---
@bot.tree.command(name="sban", description="Shadow ban a user by ID")
async def sban(interaction: discord.Interaction, user_id: str):
    """Shadow bans a user using their ID."""
    try:
        await interaction.guild.ban(discord.Object(id=int(user_id)), reason="Shadow Ban protocol engaged.")
        await interaction.response.send_message(f"✅ **𝐄𝐜𝐡𝐨:** User {user_id} has been shadow-banned.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}")

# --- SETUP WIZARD ---
class SetupWizard(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.page = 1

    def get_embed(self):
        pages = {
            1: ("🛡️ Security Gate", "Configure your security settings."),
            2: ("🎭 Role Setup", "Assign the newcomer role."),
            3: ("✉️ Welcome DM", "Set the DM briefing message.")
        }
        title, desc = pages.get(self.page, ("Error", "Unknown page"))
        return discord.Embed(title=f"𝐄𝐜𝐡𝐨 | {title}", description=desc)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 1: self.page -= 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < 3: self.page += 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

@bot.tree.command(name="setup", description="Open the 𝐄𝐜𝐡𝐨 setup wizard")
async def setup(interaction: discord.Interaction):
    view = SetupWizard()
    await interaction.response.send_message(embed=view.get_embed(), view=view)

# --- LISTENERS ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    # Auto-remove AFK
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    if cursor.rowcount > 0:
        await message.channel.send(f"🕶️ **𝐄𝐜𝐡𝐨:** Welcome back, {message.author.mention}! AFK status cleared.")
    db.commit()
    db.close()

    await bot.process_commands(message)

# --- EXECUTION ---
@bot.event
async def setup_hook():
    await bot.tree.[span_2](start_span)sync() # Syncs your slash commands with Discord[span_2](end_span)

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
