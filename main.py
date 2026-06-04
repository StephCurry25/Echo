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

# --- DATABASE HELPERS ---
def update_db(guild_id, column, value):
    db = sqlite3.connect('edith_mainframe.db')
    db.execute(f'UPDATE server_settings SET {column}=? WHERE guild_id=?', (value, guild_id))
    db.commit()
    db.close()

# --- UI COMPONENTS ---
class RoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Select a newcomer role...")

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        update_db(interaction.guild.id, "role_name", role.name)
        await interaction.response.send_message(f"✅ Role set to {role.mention}", ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())

    @discord.ui.button(label="Security Gate", style=discord.ButtonStyle.danger)
    async def sec_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create "gate" channel
        guild = interaction.guild
        channel = discord.utils.get(guild.text_channels, name="gate")
        if not channel:
            channel = await guild.create_text_channel("gate")
        await interaction.response.send_message(f"✅ Security channel {channel.mention} ready.", ephemeral=True)

    @discord.ui.button(label="Set Welcome DM", style=discord.ButtonStyle.secondary)
    async def dm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        class DMModal(discord.ui.Modal, title="Set Welcome DM"):
            msg = discord.ui.TextInput(label="Message")
            async def on_submit(self, i):
                update_db(i.guild.id, "welcome_dm", self.msg.value)
                await i.response.send_message("DM saved!", ephemeral=True)
        await interaction.response.send_modal(DMModal())

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Open the Echo setup UI")
async def setup(interaction: discord.Interaction):
    await interaction.response.send_message("Configure your server:", view=SetupView())

@bot.tree.command(name="afk", description="Set AFK status")
async def afk(interaction: discord.Interaction, reason: str):
    db = sqlite3.connect('edith_mainframe.db')
    db.execute("INSERT OR REPLACE INTO afk (user_id, reason) VALUES (?, ?)", (interaction.user.id, reason))
    db.commit()
    db.close()
    await interaction.response.send_message(f"💤 You are now AFK: {reason}")

# --- LISTENERS ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    # Remove AFK
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    if cursor.rowcount > 0:
        await message.channel.send(f"Welcome back, {message.author.mention}!")
    db.commit()
    db.close()
    await bot.process_commands(message)

# --- EXECUTION ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Echo is online.")

async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, role_name TEXT, welcome_dm TEXT)')
    db.execute('INSERT OR IGNORE INTO server_settings (guild_id) VALUES (0)')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.commit()
    db.close()
    
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
