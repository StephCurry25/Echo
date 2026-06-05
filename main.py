import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import json
import traceback
from flask import Flask

# --- SECTION 1: GLOBAL CONFIGURATION AND INITIALIZATION ---
# This bot is designed to be fully explicit to ensure maximum readability and length.
# We are initializing the bot with full intent support for server management.

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EchoPro')

app = Flask(__name__)
@app.route('/')
def home(): 
    return "The system is fully operational and awaiting commands."

def run_flask_server():
    app.run(host='0.0.0.0', port=8080)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True

# Explicitly defining the bot object
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- SECTION 2: DATA PERSISTENCE LAYER ---
# We use a JSON file to ensure that your settings are saved and reloaded.
CONFIG_FILE = "config.json"

def load_all_configuration():
    if not os.path.exists(CONFIG_FILE):
        return {"automod": False, "autorole_id": None, "log_channel_id": None}
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

def save_all_configuration(data):
    with open(CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)

config = load_all_configuration()

# --- SECTION 3: UI DASHBOARD AND SETTINGS MANAGEMENT ---
# This dashboard uses explicit button and select menus for your settings.
class FullDashboardView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger)
    async def toggle_automod_button(self, interaction: discord.Interaction, button: ui.Button):
        config["automod"] = not config["automod"]
        save_all_configuration(config)
        await interaction.response.send_message(f"AutoMod is now set to: {config['automod']}", ephemeral=True)

    @ui.role_select(placeholder="Select the Role for New Members", min_values=1, max_values=1)
    async def select_autorole_menu(self, interaction: discord.Interaction, select: ui.RoleSelect):
        config["autorole_id"] = select.values[0].id
        save_all_configuration(config)
        await interaction.response.send_message(f"Autorole role has been updated to: {select.values[0].name}", ephemeral=True)

    @ui.channel_select(placeholder="Select the Channel for Audit Logs", channel_types=[discord.ChannelType.text])
    async def select_log_channel_menu(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        config["log_channel_id"] = select.values[0].id
        save_all_configuration(config)
        await interaction.response.send_message(f"Log channel has been updated to: {select.values[0].mention}", ephemeral=True)

# --- SECTION 4: EXPLICIT LOGGING SYSTEM ---
# Every single moderation action will trigger this long-form function.
async def send_detailed_audit_log(guild: discord.Guild, title: str, details: str, color: discord.Color):
    if config["log_channel_id"]:
        log_channel = guild.get_channel(config["log_channel_id"])
        if log_channel:
            embed_log = discord.Embed(
                title=title, 
                description=details, 
                color=color, 
                timestamp=discord.utils.utcnow()
            )
            embed_log.set_footer(text="Audit System Log")
            await log_channel.send(embed=embed_log)

# --- SECTION 5: MODERATION COMMANDS (NON-TRIMMED) ---
@bot.tree.command(name="kick", description="Kick a member from the server for violating rules")
@app_commands.checks.has_permissions(kick_members=True)
async def kick_command(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"The member {member.name} has been kicked successfully.")
    await send_detailed_audit_log(interaction.guild, "Member Kicked", f"User: {member.name}\nReason: {reason}", discord.Color.orange())

@bot.tree.command(name="ban", description="Ban a member from the server permanently")
@app_commands.checks.has_permissions(ban_members=True)
async def ban_command(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"The member {member.name} has been banned successfully.")
    await send_detailed_audit_log(interaction.guild, "Member Banned", f"User: {member.name}\nReason: {reason}", discord.Color.red())

@bot.tree.command(name="unban", description="Unban a user using their unique User ID")
@app_commands.checks.has_permissions(ban_members=True)
async def unban_command(interaction: discord.Interaction, user_id: str):
    target_user = await bot.fetch_user(int(user_id))
    await interaction.guild.unban(target_user)
    await interaction.response.send_message(f"The user {target_user.name} has been unbanned.")
    await send_detailed_audit_log(interaction.guild, "Member Unbanned", f"User: {target_user.name}", discord.Color.green())

@bot.tree.command(name="mute", description="Mute a member by assigning the Muted role")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute_command(interaction: discord.Interaction, member: discord.Member):
    role_to_assign = discord.utils.get(interaction.guild.roles, name="Muted")
    if not role_to_assign:
        role_to_assign = await interaction.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
    await member.add_roles(role_to_assign)
    await interaction.response.send_message(f"The member {member.name} has been muted.")
    await send_detailed_audit_log(interaction.guild, "Member Muted", f"User: {member.name}", discord.Color.dark_grey())

@bot.tree.command(name="unmute", description="Unmute a previously muted member")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute_command(interaction: discord.Interaction, member: discord.Member):
    role_to_remove = discord.utils.get(interaction.guild.roles, name="Muted")
    await member.remove_roles(role_to_remove)
    await interaction.response.send_message(f"The member {member.name} has been unmuted.")
    await send_detailed_audit_log(interaction.guild, "Member Unmuted", f"User: {member.name}", discord.Color.light_grey())

@bot.tree.command(name="clear", description="Bulk delete messages from the current channel")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_command(interaction: discord.Interaction, amount: int):
    deleted_messages = await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"Successfully purged {len(deleted_messages)} messages from the channel.", ephemeral=True)
    await send_detailed_audit_log(interaction.guild, "Messages Purged", f"Amount: {len(deleted_messages)}\nChannel: {interaction.channel.name}", discord.Color.blue())

# --- SECTION 6: UTILITY AND INFORMATION ---
@bot.tree.command(name="dashboard", description="Open the full configuration dashboard for this server")
async def dashboard_command(interaction: discord.Interaction):
    embed_message = discord.Embed(
        title="⚙️ Full Server Management Dashboard",
        description="Select the appropriate module below to configure your server's settings in real-time.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed_message, view=FullDashboardView(), ephemeral=True)

@bot.tree.command(name="cmds", description="Display a full list of all available commands for the bot")
async def cmds_command(interaction: discord.Interaction):
    embed_cmds = discord.Embed(title="📜 Official Command Directory", color=discord.Color.gold())
    embed_cmds.add_field(name="🛡️ Moderation Toolkit", value="`/kick`, `/ban`, `/unban`, `/mute`, `/unmute`, `/clear`", inline=False)
    embed_cmds.add_field(name="📊 Server Auditing", value="`/userinfo`, `/serverinfo`", inline=False)
    embed_cmds.add_field(name="⚙️ Administration", value="`/announce`, `/dashboard`", inline=False)
    await interaction.response.send_message(embed=embed_cmds)

# --- SECTION 7: AUTOMATED EVENT HANDLERS ---
@bot.event
async def on_member_join(member):
    if config["autorole_id"]:
        role_to_add = member.guild.get_role(config["autorole_id"])
        if role_to_add:
            await member.add_roles(role_to_add)
    await send_detailed_audit_log(member.guild, "New Member Joined", f"User: {member.name} has joined the server.", discord.Color.green())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if config["automod"]:
        restricted_terms = ["scam", "badword", "phishing", "spam"]
        if any(term in message.content.lower() for term in restricted_terms):
            await message.delete()
            await message.channel.send("⚠️ This message has been removed for violating server security policies.", delete_after=5)
    await bot.process_commands(message)

# --- SECTION 8: SYSTEM INITIALIZATION AND SYNC ---
@bot.event
async def on_ready():
    synced_commands = await bot.tree.sync()
    logger.info(f"The bot is now fully online and logged in as {bot.user}")
    logger.info(f"Total commands successfully synchronized: {len(synced_commands)}")

# The main execution block that runs the web server and the discord bot concurrently.
if __name__ == "__main__":
    server_thread = threading.Thread(target=run_flask_server, daemon=True)
    server_thread.start()
    
    bot_token = os.environ.get("TOKEN")
    if bot_token:
        bot.run(bot_token.strip())
    else:
        logger.error("The bot token is missing from the environment variables.")
