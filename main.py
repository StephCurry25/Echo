import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
from flask import Flask, jsonify
import werkzeug.serving

TOKEN = "YOUR_TOKEN_HERE"
PORT = 8080
app = Flask('')

@app.route('/')
def home():
    return jsonify({"status": "online"}), 200

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
        title, desc = pages.get(self.page)
        return discord.Embed(title=f"𝐄𝐜𝐡𝐨 | {title}", description=desc)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 1: self.page -= 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < 3: self.page += 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# --- BOT SETUP ---
class EchoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())

    async def setup_hook(self):
        await self.tree.sync()

bot = EchoBot()

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Open the 𝐄𝐜𝐡𝐨 setup wizard")
async def setup(interaction: discord.Interaction):
    view = SetupWizard()
    await interaction.response.send_message(embed=view.get_embed(), view=view)

@bot.tree.command(name="sban", description="Shadow ban a user by ID")
async def sban(interaction: discord.[span_2](start_span)Interaction, user_id: str):
    # Bans a user even if they are not in the server[span_2](end_span)
    await interaction.guild.ban(discord.Object(id=int(user_id)), reason="Shadow Ban protocol engaged.")
    await interaction.response.send_message(f"✅ **𝐄𝐜𝐡𝐨:** User {user_id} has been shadow-banned.")

# --- LISTENERS ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    [span_3](start_span)# Auto-remove AFK[span_3](end_span)
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    if cursor.rowcount > 0:
        await message.channel.send(f"🕶️ **𝐄𝐜𝐡𝐨:** Welcome back, {message.author.mention}! AFK status cleared.")
    db.commit()
    db.close()

    await bot.process_commands(message)

# --- EXECUTION ---
async def main():
    # Database Init
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.commit()
    db.close()

    # Flask for 8080
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
