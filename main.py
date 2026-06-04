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
    async def accept(self, i: discord.Interaction, b: discord.ui.Button):
        # Add a role or simply log the acceptance
        await i.response.send_message(f"✅ {self.member.mention} has been accepted!")
        self.stop()

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, i: discord.Interaction, b: discord.ui.Button):
        await self.member.kick(reason="Denied at the Gate")
        await i.response.send_message(f"❌ {self.member.name} has been kicked.")
        self.stop()

# --- SETUP UI ---
class RoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Select newcomer role...")
    async def callback(self, i: discord.Interaction):
        # Save to DB (Simplified for brevity)
        await i.response.send_message(f"✅ Role set: {self.values[0].name}", ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())
    
    @discord.ui.button(label="Create/Reset Gate Channel", style=discord.ButtonStyle.danger)
    async def sec_btn(self, i: discord.Interaction, b: discord.ui.Button):
        channel = discord.utils.get(i.guild.text_channels, name="gate")
        if not channel: 
            channel = await i.guild.create_text_channel("gate")
        await i.response.send_message(f"✅ Gate channel is ready: {channel.mention}", ephemeral=True)

# --- LISTENERS ---
@bot.event
async def on_member_join(member):
    # Automatically send the Gate UI when a member joins
    channel = discord.utils.get(member.guild.text_channels, name="gate")
    if channel:
        await channel.send(f"👋 Newcomer {member.mention}, please wait for an admin to accept you.", view=GateView(member))

@bot.event
async def on_message(message):
    if message.author.bot: return
    # AFK Logic
    db = sqlite3.connect('edith_mainframe.db')
    cursor = db.cursor()
    # Check mentions for AFK
    for m in message.mentions:
        res = cursor.execute("SELECT reason FROM afk WHERE user_id=?", (m.id,)).fetchone()
        if res: await message.channel.send(f"💤 {m.name} is AFK: {res[0]}")
    # Clear AFK
    cursor.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    if cursor.rowcount > 0: await message.channel.send(f"👋 Welcome back, {message.author.mention}!")
    db.commit()
    db.close()
    await bot.process_commands(message)

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Open setup menu")
async def setup(i: discord.Interaction):
    await i.response.send_message("Setup Menu:", view=SetupView())

@bot.tree.command(name="afk", description="Set AFK")
async def afk(i: discord.Interaction, reason: str):
    db = sqlite3.connect('edith_mainframe.db')
    db.execute("INSERT OR REPLACE INTO afk (user_id, reason) VALUES (?, ?)", (i.user.id, reason))
    db.commit()
    db.close()
    await i.response.send_message(f"💤 AFK set: {reason}")

@bot.tree.command(name="kick", description="Kick user")
async def kick(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await i.response.send_message(f"👢 Kicked {member.name}")

@bot.tree.command(name="ban", description="Ban user")
async def ban(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member.name}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Echo is online.")

async def main():
    # DB Setup
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.commit()
    db.close()
    
    server = werkzeug.serving.make_server('0.0.0.0', PORT, app, threaded=True)
    asyncio.get_running_loop().run_in_executor(None, server.serve_forever)
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
