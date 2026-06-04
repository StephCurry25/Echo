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
class GateView(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message(f"✅ {self.member.name} accepted.")
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message(f"❌ {self.member.name} denied.")

class RoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Select newcomer role...")
    async def callback(self, i: discord.Interaction):
        update_db(i.guild.id, "role_name", self.values[0].name)
        await i.response.send_message(f"✅ Role set: {self.values[0].name}", ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())
    @discord.ui.button(label="Security Gate", style=discord.ButtonStyle.danger)
    async def sec_btn(self, i: discord.Interaction, b: discord.ui.Button):
        channel = discord.utils.get(i.guild.text_channels, name="gate")
        if not channel: channel = await i.guild.create_text_channel("gate")
        await i.response.send_message(f"✅ Gate ready: {channel.mention}", ephemeral=True)

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Open Echo setup")
async def setup(i: discord.Interaction):
    await i.response.send_message("Setup Menu:", view=SetupView())

@bot.tree.command(name="afk", description="Set AFK status")
async def afk(i: discord.Interaction, reason: str):
    db = sqlite3.connect('edith_mainframe.db')
    db.execute("INSERT OR REPLACE INTO afk (user_id, reason) VALUES (?, ?)", (i.user.id, reason))
    db.commit()
    db.close()
    await i.response.send_message(f"💤 AFK: {reason}")

@bot.tree.command(name="kick", description="Kick user")
async def kick(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await i.response.send_message(f"👢 Kicked {member.name}")

@bot.tree.command(name="ban", description="Ban user")
async def ban(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member.name}")

# --- LISTENERS ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    # AFK Mention Listener
    for member in message.mentions:
        db = sqlite3.connect('edith_mainframe.db')
        res = db.execute("SELECT reason FROM afk WHERE user_id=?", (member.id,)).fetchone()
        db.close()
        if res: await message.channel.send(f"💤 {member.name} is AFK: {res[0]}")
    # Auto-Clear AFK
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    if cursor.rowcount > 0: await message.channel.send(f"👋 Welcome back, {message.author.mention}!")
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
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, role_name TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.commit()
    db.close()
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
