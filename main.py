import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
from flask import Flask

# --- LOGGING & SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is live!"
def run_web_server(): app.run(host='0.0.0.0', port=8080)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

bot_config = {"automod_enabled": False, "autorole_id": None}

# --- UI COMPONENTS ---
class SettingsView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @ui.select(
        placeholder="Select a module...",
        options=[
            discord.SelectOption(label="Toggle AutoMod", description="Filter offensive language"),
            discord.SelectOption(label="Set Autorole", description="Assign roles on join")
        ]
    )
    async def select_callback(self, i: discord.Interaction, select: ui.Select):
        if select.values[0] == "Toggle AutoMod":
            bot_config["automod_enabled"] = not bot_config["automod_enabled"]
            await i.response.send_message(f"✅ AutoMod is now {bot_config['automod_enabled']}", ephemeral=True)

# --- SLASH COMMANDS ---

# ADMIN
@bot.tree.command(name="announce", description="Global broadcast")
async def announce(i: discord.Interaction, message: str):
    if i.user.id != 1219266886143967245: return await i.response.send_message("❌ Unauthorized.", ephemeral=True)
    count = 0
    for guild in bot.guilds:
        channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if channel: await channel.send(embed=discord.Embed(title="📢 Announcement", description=message, color=0xff0000)); count += 1
    await i.response.send_message(f"✅ Sent to {count} servers.", ephemeral=True)

# MODERATION
@bot.tree.command(name="mute", description="Mute a member")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
    await member.add_roles(role)
    await i.response.send_message(f"🤐 Muted {member.name}")

@bot.tree.command(name="unmute", description="Unmute a member")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if role in member.roles:
        await member.remove_roles(role)
        await i.response.send_message(f"🔊 Unmuted {member.name}")
    else:
        await i.response.send_message("❌ Member is not muted.")

# "OPPOSITE" OF MODERATION (Information/Audit)
@bot.tree.command(name="userinfo", description="Get full details on a member")
async def userinfo(i: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title=f"User Audit: {member.name}", color=0x00ff00)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Roles", value=", ".join([r.name for r in member.roles if r.name != "@everyone"]))
    await i.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Get server audit data")
async def serverinfo(i: discord.Interaction):
    embed = discord.Embed(title=f"Server Audit: {i.guild.name}", color=0x00ff00)
    embed.add_field(name="Members", value=i.guild.member_count)
    embed.add_field(name="Owner", value=i.guild.owner)
    await i.response.send_message(embed=embed)

# STANDARD MOD
@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, reason: str = "None"):
    await member.kick(reason=reason); await i.response.send_message(f"🦿 Kicked {member.name}")

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, reason: str = "None"):
    await member.ban(reason=reason); await i.response.send_message(f"🔨 Banned {member.name}")

@bot.tree.command(name="clear", description="Clear messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, amount: int):
    deleted = await i.channel.purge(limit=amount)
    await i.response.send_message(f"🧹 Purged {len(deleted)}.", ephemeral=True)

# --- INITIALIZATION ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} is online.")

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    token = os.environ.get("TOKEN")
    if token: bot.run(token.strip())
