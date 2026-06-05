import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import json
from flask import Flask

# --- 1. SETUP & LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EchoBot-Production')

# --- 2. UPTIME SERVER ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "System Online"
def start_web_server(): app.run(host='0.0.0.0', port=8080)

# --- 3. CONFIGURATION MANAGEMENT ---
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {"automod": False, "autorole_id": None, "log_channel_id": None}
        with open(CONFIG_FILE, "w") as f: json.dump(default, f, indent=4)
        return default
    with open(CONFIG_FILE, "r") as f: return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f: json.dump(data, f, indent=4)

config = load_config()

# --- 4. PERSISTENT UI ---
class PersistentDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger)
    async def toggle(self, i: discord.Interaction, b: ui.Button):
        config["automod"] = not config["automod"]
        save_config(config)
        await i.response.send_message(f"AutoMod: {config['automod']}", ephemeral=True)

    @ui.select(cls=ui.RoleSelect, placeholder="Select Autorole")
    async def autorole(self, i: discord.Interaction, s: ui.RoleSelect):
        config["autorole_id"] = s.values[0].id
        save_config(config)
        await i.response.send_message(f"Autorole: {s.values[0].name}", ephemeral=True)

    @ui.select(cls=ui.ChannelSelect, placeholder="Select Log Channel", channel_types=[discord.ChannelType.text])
    async def log_channel(self, i: discord.Interaction, s: ui.ChannelSelect):
        config["log_channel_id"] = s.values[0].id
        save_config(config)
        await i.response.send_message(f"Logs: {s.values[0].name}", ephemeral=True)

# --- 5. BOT CORE ---
class EchoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        self.add_view(PersistentDashboard())
        await self.tree.sync()
        logger.info("Commands synced.")

bot = EchoBot()

# --- 6. COMMANDS ---
@bot.tree.command(name="dashboard", description="Open settings")
async def dashboard(i: discord.Interaction):
    await i.response.send_message("⚙️ Dashboard", view=PersistentDashboard(), ephemeral=True)

@bot.tree.command(name="announce", description="Global broadcast")
async def announce(i: discord.Interaction, message: str):
    if i.user.id != 1219266886143967245:
        return await i.response.send_message("❌ Unauthorized.", ephemeral=True)
    for g in bot.guilds:
        if g.system_channel: await g.system_channel.send(f"📢 {message}")
    await i.response.send_message("✅ Broadcasted.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick user")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, m: discord.Member, reason: str = "No reason"):
    await m.kick(reason=reason); await i.response.send_message(f"Kicked {m.name}")

@bot.tree.command(name="ban", description="Ban user")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, m: discord.Member, reason: str = "No reason"):
    await m.ban(reason=reason); await i.response.send_message(f"Banned {m.name}")

@bot.tree.command(name="mute", description="Mute user")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(i: discord.Interaction, m: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
    await m.add_roles(role); await i.response.send_message(f"Muted {m.name}")

@bot.tree.command(name="unmute", description="Unmute user")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(i: discord.Interaction, m: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    await m.remove_roles(role); await i.response.send_message(f"Unmuted {m.name}")

@bot.tree.command(name="clear", description="Clear chat")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, n: int):
    d = await i.channel.purge(limit=n)
    await i.response.send_message(f"Purged {len(d)}", ephemeral=True)

# --- 7. EVENTS ---
@bot.event
async def on_member
