import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import json
import traceback
from flask import Flask

# --- 1. INDUSTRIAL LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EchoBot-Production')

# --- 2. UPTIME SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "System Status: Online"
def start_web_server(): app.run(host='0.0.0.0', port=8080)

# --- 3. BOT CONFIGURATION ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Configuration management
CONFIG_FILE = "config.json"
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    return {"automod": False, "autorole_id": None, "log_channel_id": None}

def save_config(data):
    with open(CONFIG_FILE, "w") as f: json.dump(data, f, indent=4)

config = load_config()

# --- 4. PERSISTENT UI DASHBOARD ---
class PersistentDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger)
    async def toggle_automod(self, i: discord.Interaction, b: ui.Button):
        config["automod"] = not config["automod"]
        save_config(config)
        await i.response.send_message(f"AutoMod set to: {config['automod']}", ephemeral=True)

    @ui.select(cls=ui.RoleSelect, placeholder="Select Autorole")
    async def select_autorole(self, i: discord.Interaction, s: ui.RoleSelect):
        config["autorole_id"] = s.values[0].id
        save_config(config)
        await i.response.send_message(f"Autorole set to: {s.values[0].name}", ephemeral=True)

    @ui.select(cls=ui.ChannelSelect, placeholder="Select Log Channel", channel_types=[discord.ChannelType.text])
    async def select_log(self, i: discord.Interaction, s: ui.ChannelSelect):
        config["log_channel_id"] = s.values[0].id
        save_config(config)
        await i.response.send_message(f"Logs set to: {s.values[0].mention}", ephemeral=True)

# --- 5. LOGGING UTILITY ---
async def log_action(guild, title, description, color=discord.Color.blue()):
    if config["log_channel_id"]:
        channel = guild.get_channel(config["log_channel_id"])
        if channel:
            embed = discord.Embed(title=title, description=description, color=color)
            await channel.send(embed=embed)

# --- 6. COMMANDS ---
class EchoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        self.add_view(PersistentDashboard())
        await self.tree.sync()
        logger.info("Bot commands synced and views registered.")

bot = EchoBot()

@bot.tree.command(name="dashboard", description="Manage settings")
async def dashboard(i: discord.Interaction):
    await i.response.send_message("⚙️ **Dashboard**", view=PersistentDashboard(), ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, reason: str = "None"):
    await member.kick(reason=reason)
    await i.response.send_message(f"👢 Kicked {member.name}")
    await log_action(i.guild, "Kick", f"{member.name} was kicked.", discord.Color.orange())

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, reason: str = "None"):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member.name}")
    await log_action(i.guild, "Ban", f"{member.name} was banned.", discord.Color.red())

@bot.tree.command(name="unmute", description="Unmute a member")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    await member.remove_roles(role)
    await i.response.send_message(f"🔊 Unmuted {member.name}")

@bot.tree.command(name="mute", description="Mute a member")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
    await member.add_roles(role)
    await i.response.send_message(f"🤐 Muted {member.name}")

@bot.tree.command(name="clear", description="Bulk delete messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, amount: int):
    purged = await i.channel.purge(limit=amount)
    await i.response.send_message(f"🧹 Purged {len(purged)} messages.", ephemeral=True)

@bot.tree.command(name="cmds", description="List all commands")
async def cmds(i: discord.Interaction):
    embed = discord.Embed(title="📜 Commands", description="/kick, /ban, /mute, /unmute, /clear, /dashboard, /userinfo, /serverinfo, /announce")
    await i.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="User info")
async def userinfo(i: discord.Interaction, member: discord.Member):
    await i.response.send_message(f"👤 {member.name} (ID: {member.id})")

@bot.tree.command(name="serverinfo", description="Server info")
async def serverinfo(i: discord.Interaction):
    await i.response.send_message(f"🏰 {i.guild.name} | Members: {i.guild.member_count}")

# --- 7. EVENTS & LAUNCH ---
@bot.event
async def on_member_join(member):
    if config["autorole_id"]:
        role = member.guild.get_role(config["autorole_id"])
        if role: await member.add_roles(role)

@bot.event
async def on_message(message):
    if config["automod"] and not message.author.bot:
        if any(w in message.content.lower() for w in ["badword", "scam"]):
            await message.delete()
    await bot.process_commands(message)

if __name__ == "__main__":
    threading.Thread(target=start_web_server, daemon=True).start()
    token = os.environ.get("TOKEN")
    if not token:
        logger.error("!!! TOKEN MISSING !!!")
        exit(1)
    bot.run(token.strip())
