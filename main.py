import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import json
import traceback
from flask import Flask

# ========================================================================
# SECTION 1: SYSTEM LOGGING AND WEB SERVER (PORT 8080 LOCKED)
# ========================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EchoBot-Core')

app = Flask(__name__)

@app.route('/')
def health_check(): 
    return "EchoBot System Status: Online & Running on Port 8080"

def start_web_server():
    # Explicitly locked to port 8080 as requested
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

# ========================================================================
# SECTION 2: CONFIGURATION AND DATA PERSISTENCE
# ========================================================================
CONFIG_FILE = "config.json"

def load_system_config():
    if not os.path.exists(CONFIG_FILE):
        default_settings = {
            "automod": False, 
            "autorole_id": None, 
            "log_channel_id": None,
            "blocked_words": ["scam", "freemoney", "phishing", "hack", "discord.gg/"]
        }
        with open(CONFIG_FILE, "w") as file:
            json.dump(default_settings, file, indent=4)
        return default_settings
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

def save_system_config(data):
    with open(CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)

config = load_system_config()

if "blocked_words" not in config:
    config["blocked_words"] = ["scam", "freemoney", "discord.gg/"]
    save_system_config(config)

# ========================================================================
# SECTION 3: ADVANCED AUDIT LOGGING
# ========================================================================
async def send_audit_log(guild: discord.Guild, title: str, description: str, color: discord.Color):
    if config["log_channel_id"]:
        log_channel = guild.get_channel(config["log_channel_id"])
        if log_channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
            embed.set_footer(text="EchoBot Security Logging")
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                logger.error(f"Failed to send log in channel {log_channel.name} due to missing permissions.")

# ========================================================================
# SECTION 4: INTERACTIVE UI DASHBOARD
# ========================================================================
class ServerManagementDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger, custom_id="toggle_automod_btn")
    async def toggle_automod_action(self, interaction: discord.Interaction, button: ui.Button):
        config["automod"] = not config["automod"]
        save_system_config(config)
        status = "ENABLED 🛡️" if config["automod"] else "DISABLED ❌"
        await interaction.response.send_message(f"AutoMod protection is now **{status}**.", ephemeral=True)

    @ui.select(cls=ui.RoleSelect, placeholder="Select Autorole for New Members", custom_id="autorole_select_menu")
    async def select_autorole_action(self, interaction: discord.Interaction, select: ui.RoleSelect):
        config["autorole_id"] = select.values[0].id
        save_system_config(config)
        await interaction.response.send_message(f"✅ Automatically assigning role: **{select.values[0].name}**.", ephemeral=True)

    @ui.select(cls=ui.ChannelSelect, placeholder="Select Channel for Audit Logs", channel_types=[discord.ChannelType.text], custom_id="audit_log_select_menu")
    async def select_log_channel_action(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        config["log_channel_id"] = select.values[0].id
        save_system_config(config)
        await interaction.response.send_message(f"✅ Audit logs routed to: **{select.values[0].mention}**.", ephemeral=True)

# ========================================================================
# SECTION 5: CORE BOT INITIALIZATION & GLOBAL ERROR HANDLING
# ========================================================================
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
        logger.info("Application commands successfully synchronized with Discord API.")

bot = EchoBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You do not have permission to execute this command.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message("❌ I do not have the required permissions. Adjust my role settings.", ephemeral=True)
    else:
        logger.error(f"Unhandled Command Exception: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"⚠️ An error occurred: {error}", ephemeral=True)

# ========================================================================
# SECTION 6: FAILSAFE MODERATION COMMANDS
# ========================================================================
@bot.tree.command(name="kick
