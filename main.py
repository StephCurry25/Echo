import os
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
from keep_alive import keep_alive # Use your separate keep_alive.py file

TOKEN = os.environ.get('TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# --- SECURED GATE UI ---
class GateView(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow admins to use these buttons
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only admins can use this.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message(f"✅ {self.member.name} accepted.")
        self.stop()

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, i: discord.Interaction, b: discord.ui.Button):
        await self.member.kick(reason="Denied at Gate")
        await i.response.send_message(f"❌ {self.member.name} kicked.")
        self.stop()

# --- SETUP UI ---
class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Create/Reset Gate Channel", style=discord.ButtonStyle.danger)
    async def sec_btn(self, i: discord.Interaction, b: discord.ui.Button):
        channel = discord.utils.get(i.guild.text_channels, name="gate")
        if not channel: 
            channel = await i.guild.create_text_channel("gate")
        await i.response.send_message(f"✅ Gate channel: {channel.mention}", ephemeral=True)

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

# --- LISTENERS ---
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="gate")
    if channel:
        await channel.send(f"👋 Newcomer {member.mention}, please wait for an admin to accept you.", view=GateView(member))

@bot.event
async def on_message(message):
    if message.author.bot: return
    db = sqlite3.connect('edith_mainframe.db')
    # Check AFK
    for m in message.mentions:
        res = db.execute("SELECT reason FROM afk WHERE user_id=?", (m.id,)).fetchone()
        if res: await message.channel.send(f"💤 {m.name} is AFK: {res[0]}")
    # Clear AFK
    cursor = db.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,))
    if cursor.rowcount > 0: await message.channel.send(f"👋 Welcome back, {message.author.mention}!")
    db.commit()
    db.close()
    await bot.process_commands(message)

@bot.event
async def on_ready():
    keep_alive() # Start uptime server
    await bot.tree.sync()
    print("✅ Echo is online.")

async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.commit()
    db.close()
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
