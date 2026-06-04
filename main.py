import os
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
from keep_alive import keep_alive

TOKEN = os.environ.get('TOKEN')
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
    async def interaction_check(self, i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("❌ Only admins can use this.", ephemeral=True)
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

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Create/Reset Gate", style=discord.ButtonStyle.danger)
    async def sec_btn(self, i: discord.Interaction, b: discord.ui.Button):
        channel = discord.utils.get(i.guild.text_channels, name="gate")
        if not channel: channel = await i.guild.create_text_channel("gate")
        await i.response.send_message(f"✅ Gate ready: {channel.mention}", ephemeral=True)

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Open Setup UI")
async def setup(i: discord.Interaction):
    await i.response.send_message("Server Setup:", view=SetupView())

@bot.tree.command(name="afk", description="Set AFK status")
async def afk(i: discord.Interaction, reason: str):
    db = sqlite3.connect('edith_mainframe.db')
    db.execute("INSERT OR REPLACE INTO afk (user_id, reason) VALUES (?, ?)", (i.user.id, reason))
    db.commit()
    db.close()
    await i.response.send_message(f"💤 AFK set: {reason}")

@bot.tree.command(name="kick", description="Kick user")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await i.response.send_message(f"👢 Kicked {member.name}")

@bot.tree.command(name="ban", description="Ban user")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member.name}")

@bot.tree.command(name="unban", description="Unban user by ID")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(i: discord.Interaction, user_id: str):
    await i.guild.unban(discord.Object(id=int(user_id)))
    await i.response.send_message(f"🔓 Unbanned {user_id}")

@bot.tree.command(name="mute", description="Mute user")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted")
    await member.add_roles(role)
    await i.response.send_message(f"🤐 Muted {member.name}")

@bot.tree.command(name="unmute", description="Unmute user")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    await member.remove_roles(role)
    await i.response.send_message(f"🔊 Unmuted {member.name}")

# --- LISTENERS & RUN ---
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="gate")
    if channel:
        await channel.send(f"👋 Newcomer {member.mention}, wait for an admin.", view=GateView(member))

@bot.event
async def on_message(message):
    if message.author.bot: return
    db = sqlite3.connect('edith_mainframe.db')
    for m in message.mentions:
        res = db.execute("SELECT reason FROM afk WHERE user_id=?", (m.id,)).fetchone()
        if res: await message.channel.send(f"💤 {m.name} is AFK: {res[0]}")
    if db.execute("DELETE FROM afk WHERE user_id=?", (message.author.id,)).rowcount > 0:
        await message.channel.send(f"👋 Welcome back, {message.author.mention}!")
    db.commit()
    db.close()
    await bot.process_commands(message)

@bot.event
async def on_ready():
    keep_alive()
    await bot.tree.sync()
    print("✅ Echo is fully online.")

async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.commit()
    db.close()
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
