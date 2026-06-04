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

# --- MODAL FOR INPUTS ---
class SetupModal(discord.ui.Modal):
    def __init__(self, title, field_label, db_column):
        super().__init__(title=title)
        self.db_column = db_column
        self.input_field = discord.ui.TextInput(label=field_label, style=discord.TextStyle.paragraph)
        self.add_item(self.input_field)

    async def on_submit(self, interaction: discord.Interaction):
        db = sqlite3.connect('edith_mainframe.db')
        db.execute(f'UPDATE server_settings SET {self.db_column}=? WHERE guild_id=?', (self.input_field.value, interaction.guild.id))
        db.commit()
        db.close()
        await interaction.response.send_message(f"✅ Saved {self.db_column}: {self.input_field.value}", ephemeral=True)

# --- UI WITH MODAL TRIGGERS ---
class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Security Gate", style=discord.ButtonStyle.danger)
    async def sec_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetupModal("Security Gate", "Enter Security Rule:", "security_gate"))

    @discord.ui.button(label="Newcomer Role", style=discord.ButtonStyle.primary)
    async def role_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetupModal("Role Setup", "Enter Role Name:", "role_name"))

    @discord.ui.button(label="Welcome DM", style=discord.ButtonStyle.secondary)
    async def dm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetupModal("DM Setup", "Enter Welcome Message:", "welcome_dm"))

# --- SLASH COMMANDS ---
@bot.tree.command(name="setup", description="Open the Echo setup UI")
async def setup(interaction: discord.Interaction):
    await interaction.response.send_message("Configure your server:", view=SetupView())

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.name}.")

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 Banned {member.name}.")

# --- SYNC & RUN ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Echo is online and synced.")

async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, role_name TEXT, welcome_dm TEXT, security_gate TEXT)')
    db.execute('INSERT OR IGNORE INTO server_settings (guild_id) VALUES (0)')
    db.commit()
    db.close()
    
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
