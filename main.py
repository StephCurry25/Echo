import discord
from discord import app_commands
from discord.ext import commands
import os
import threading
from flask import Flask

# --- WEB SERVER (Port 8080) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running on port 8080"
def run_web_server(): app.run(host='0.0.0.0', port=8080)

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

config = {"welcome_ch": None, "audit_ch": None, "admin_role": None, "theme": "Robot", "assign_role": None}

# --- TICKET UI ---
class TicketOpenView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="📩 Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open(self, i: discord.Interaction, b: discord.ui.Button):
        channel = await i.guild.create_text_channel(f"ticket-{i.user.name}")
        await channel.set_permissions(i.guild.default_role, read_messages=False)
        await channel.set_permissions(i.user, read_messages=True, send_messages=True)
        await i.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
        if config["audit_ch"]: await config["audit_ch"].send(f"📂 Ticket opened by {i.user.name}")

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Configure welcome channel, role, and theme")
async def setup(i: discord.Interaction, channel: discord.TextChannel, role: discord.Role, theme: str):
    config.update({"welcome_ch": channel, "assign_role": role, "theme": theme})
    await i.response.send_message(f"✅ Configured! Channel: {channel.mention}, Theme: {theme}", ephemeral=True)

@bot.tree.command(name="tsetup", description="Setup Ticket System: Audit channel and Admin role")
async def tsetup(i: discord.Interaction, audit_channel: discord.TextChannel, admin_role: discord.Role):
    config.update({"audit_ch": audit_channel, "admin_role": admin_role})
    await audit_channel.set_permissions(i.guild.default_role, read_messages=False)
    await audit_channel.set_permissions(admin_role, read_messages=True)
    embed = discord.Embed(title="🎟️ Support Center", description="Click below to open a ticket.", color=discord.Color.blue())
    await i.channel.send(embed=embed, view=TicketOpenView())
    await i.response.send_message("✅ Ticket system configured.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
async def kick(i: discord.Interaction, member: discord.Member):
    await member.kick(); await i.response.send_message(f"👢 Kicked {member.name}")

@bot.tree.command(name="ban", description="Ban a member")
async def ban(i: discord.Interaction, member: discord.Member):
    await member.ban(); await i.response.send_message(f"🔨 Banned {member.name}")

@bot.tree.command(name="unban", description="Unban user by username")
async def unban(i: discord.Interaction, username: str):
    async for entry in i.guild.bans():
        if str(entry.user) == username:
            await i.guild.unban(entry.user)
            return await i.response.send_message(f"🔓 Unbanned {username}")
    await i.response.send_message("❌ User not found.")

@bot.tree.command(name="mute", description="Mute a member")
async def mute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted")
    await member.add_roles(role); await i.response.send_message(f"🤐 Muted {member.name}")

@bot.tree.command(name="unmute", description="Unmute a member")
async def unmute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    await member.remove_roles(role); await i.response.send_message(f"🔊 Unmuted {member.name}")

# --- EVENTS ---
@bot.event
async def on_member_join(member):
    if config["assign_role"]: await member.add_roles(config["assign_role"])
    if config["welcome_ch"]:
        themes = {"StarWars": "The Force is with you!", "Lego": "Everything is awesome!", "Pirate": "Ahoy!", "Robot": "Beep boop!"}
        msg = themes.get(config["theme"], "Welcome!")
        await config["welcome_ch"].send(embed=discord.Embed(title="Welcome!", description=f"{msg} {member.mention}", color=discord.Color.green()))

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Bot is online and ready.")

if __name__ == "__main__":
    threading.Thread(target=run_web_server).start()
    token = os.environ.get("TOKEN")
    if token: bot.run(token.strip())
