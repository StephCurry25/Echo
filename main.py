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
# SECTION 1: SYSTEM LOGGING AND WEB SERVER
# ========================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EchoBot-Pro')

app = Flask(__name__)
@app.route('/')
def health_check(): 
    return "EchoBot System Status: 100% Operational"

def start_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ========================================================================
# SECTION 2: CONFIGURATION AND DYNAMIC DATABASE
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

# Ensure older config files get the new blocked_words list
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
            embed.set_footer(text="EchoBot Security System")
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                logger.error(f"Lacking permissions to send audit log in channel {log_channel.name}")

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
        await interaction.response.send_message(f"✅ Audit logs will now be sent to: **{select.values[0].mention}**.", ephemeral=True)

# ========================================================================
# SECTION 5: CORE BOT INITIALIZATION & ERROR HANDLING
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
        logger.info("Bot commands successfully synced to Discord API.")

bot = EchoBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You lack the required permissions to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message("❌ I lack the Discord permissions to do this. Check my roles in Server Settings.", ephemeral=True)
    else:
        logger.error(f"Command Error: {error}")
        await interaction.response.send_message(f"⚠️ An error occurred: {error}", ephemeral=True)

# ========================================================================
# SECTION 6: FAILSAFE MODERATION COMMANDS
# ========================================================================
@bot.tree.command(name="kick", description="Remove a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def command_kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message("❌ You cannot kick a member with an equal or higher role.", ephemeral=True)
    if member.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ My bot role is lower than the target's role! Drag my role higher in settings.", ephemeral=True)
    
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 **{member.name}** has been kicked.")
        await send_audit_log(interaction.guild, "Member Kicked", f"**Target:** {member.mention}\n**Mod:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.orange())
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to kick this user.", ephemeral=True)

@bot.tree.command(name="ban", description="Permanently ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def command_ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message("❌ You cannot ban a member with an equal or higher role.", ephemeral=True)
    if member.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ My bot role is lower than the target's role! Drag my role higher in settings.", ephemeral=True)

    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 **{member.name}** has been banned.")
        await send_audit_log(interaction.guild, "Member Banned", f"**Target:** {member.mention}\n**Mod:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.red())
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to ban this user.", ephemeral=True)

@bot.tree.command(name="mute", description="Mute a member by applying the Muted role")
@app_commands.checks.has_permissions(manage_roles=True)
async def command_mute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ My bot role is too low to mute this user.", ephemeral=True)

    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not role:
        try:
            role = await interaction.guild.create_role(name="Muted", reason="Mute command executed")
            for channel in interaction.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ I don't have permission to create a Muted role.", ephemeral=True)
    
    try:
        await member.add_roles(role, reason=reason)
        await interaction.response.send_message(f"
