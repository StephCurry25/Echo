import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import json
from flask import Flask

# --- SECTION 1: HARDCODED PORT 8080 WEB SERVER ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EchoBot')

app = Flask(__name__)

@app.route('/')
def health_check(): 
    return "EchoBot Matrix: Active on Port 8080"

def start_web_server():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

# --- SECTION 2: STORAGE AND DATA PERSISTENCE ---
CONFIG_FILE = "config.json"

def load_system_config():
    if not os.path.exists(CONFIG_FILE):
        default = {
            "automod": False, 
            "autorole_id": None, 
            "log_channel_id": None,
            "blocked_words": ["scam", "freemoney", "phishing"]
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=4)
        return default
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_system_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_system_config()

# --- SECTION 3: AUDIT LOG DISTRIBUTION ---
async def send_audit_log(guild: discord.Guild, title: str, description: str, color: discord.Color):
    if config["log_channel_id"]:
        log_channel = guild.get_channel(config["log_channel_id"])
        if log_channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
            try:
                await log_channel.send(embed=embed)
            except:
                pass

# --- SECTION 4: INTERACTIVE UI DASHBOARD ---
class ServerManagementDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger, custom_id="tg_am")
    async def toggle_automod_action(self, interaction: discord.Interaction, button: ui.Button):
        config["automod"] = not config["automod"]
        save_system_config(config)
        status = "ENABLED" if config["automod"] else "DISABLED"
        await interaction.response.send_message(f"AutoMod protection is now **{status}**.", ephemeral=True)

    @ui.select(cls=ui.RoleSelect, placeholder="Select Autorole", custom_id="sel_ar")
    async def select_autorole_action(self, interaction: discord.Interaction, select: ui.RoleSelect):
        config["autorole_id"] = select.values[0].id
        save_system_config(config)
        await interaction.response.send_message(f"Autorole saved: **{select.values[0].name}**.", ephemeral=True)

    @ui.select(cls=ui.ChannelSelect, placeholder="Select Audit Log Channel", channel_types=[discord.ChannelType.text], custom_id="sel_log")
    async def select_log_channel_action(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        config["log_channel_id"] = select.values[0].id
        save_system_config(config)
        await interaction.response.send_message(f"Audit logs routed to: **{select.values[0].mention}**.", ephemeral=True)

# --- SECTION 5: INITIALIZATION SETUP ---
class EchoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        self.add_view(ServerManagementDashboard())
        await self.tree.sync()
        logger.info("Application gateway synchronized cleanly.")

bot = EchoBot()

# --- SECTION 6: FAILSAFE MODERATION SYSTEMS ---
@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def command_kick(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message("❌ Target has an equal or higher role than you.", ephemeral=True)
    if member.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ Move my bot role above the target's role in server settings.", ephemeral=True)
    
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 **{member.name}** has been kicked.")
        await send_audit_log(interaction.guild, "Kick Executed", f"Target: {member.mention}\nMod: {interaction.user.mention}", discord.Color.orange())
    except:
        await interaction.response.send_message("❌ Permission Execution Error.", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def command_ban(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message("❌ Target has an equal or higher role than you.", ephemeral=True)
    if member.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ Move my bot role above the target's role in server settings.",
