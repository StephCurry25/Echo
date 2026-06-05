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
# SECTION 1: SYSTEM LOGGING AND WEB SERVER (STATUS 1 FIX)
# ========================================================================
# Setting up detailed logging so if something goes wrong, you see exactly what it is.
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EchoBot-Production')

# Flask server to keep the bot alive on Render/hosting platforms.
# THE FIX: Render requires the app to bind to the port it specifies in the environment.
app = Flask(__name__)
@app.route('/')
def health_check(): 
    return "EchoBot System Status: 100% Operational"

def start_web_server():
    # We grab the port from Render, fallback to 8080 if not found
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ========================================================================
# SECTION 2: CONFIGURATION AND DATA PERSISTENCE
# ========================================================================
# We use a JSON file so that when Render restarts your bot, it doesn't wipe your settings.
CONFIG_FILE = "config.json"

def load_system_config():
    if not os.path.exists(CONFIG_FILE):
        default_settings = {"automod": False, "autorole_id": None, "log_channel_id": None}
        with open(CONFIG_FILE, "w") as file:
            json.dump(default_settings, file, indent=4)
        return default_settings
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

def save_system_config(data):
    with open(CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)

config = load_system_config()

# ========================================================================
# SECTION 3: ADVANCED AUDIT LOGGING
# ========================================================================
# Every moderation command will call this function to log actions to your chosen channel.
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
# This is the persistent view for your /dashboard command.
class ServerManagementDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger, custom_id="toggle_automod_btn")
    async def toggle_automod_action(self, interaction: discord.Interaction, button: ui.Button):
        config["automod"] = not config["automod"]
        save_system_config(config)
        status = "ENABLED" if config["automod"] else "DISABLED"
        await interaction.response.send_message(f"✅ AutoMod protection is now **{status}**.", ephemeral=True)

    @ui.select(cls=ui.RoleSelect, placeholder="Select Autorole for New Members", custom_id="autorole_select_menu")
    async def select_autorole_action(self, interaction: discord.Interaction, select: ui.RoleSelect):
        config["autorole_id"] = select.values[0].id
        save_system_config(config)
        await interaction.response.send_message(f"✅ Automatically assigning role: **{select.values[0].name}** to new members.", ephemeral=True)

    @ui.select(cls=ui.ChannelSelect, placeholder="Select Channel for Audit Logs", channel_types=[discord.ChannelType.text], custom_id="audit_log_select_menu")
    async def select_log_channel_action(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        config["log_channel_id"] = select.values[0].id
        save_system_config(config)
        await interaction.response.send_message(f"✅ Audit logs will now be sent to: **{select.values[0].mention}**.", ephemeral=True)

# ========================================================================
# SECTION 5: CORE BOT INITIALIZATION
# ========================================================================
class EchoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        # Register the dashboard view so buttons don't break on restart
        self.add_view(ServerManagementDashboard())
        await self.tree.sync()
        logger.info("Bot commands successfully synced to Discord API.")

bot = EchoBot()

# ========================================================================
# SECTION 6: MODERATION COMMANDS (DYNO-LIKE FEATURES)
# ========================================================================
@bot.tree.command(name="kick", description="Remove a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def command_kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided by moderator"):
    if member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ You cannot kick a member with an equal or higher role.", ephemeral=True)
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 **{member.name}** has been kicked from the server.")
    await send_audit_log(interaction.guild, "Member Kicked", f"**Target:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.orange())

@bot.tree.command(name="ban", description="Permanently ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def command_ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided by moderator"):
    if member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ You cannot ban a member with an equal or higher role.", ephemeral=True)
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 **{member.name}** has been banned from the server.")
    await send_audit_log(interaction.guild, "Member Banned", f"**Target:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.red())

@bot.tree.command(name="unban", description="Revoke a ban for a user using their ID")
@app_commands.checks.has_permissions(ban_members=True)
async def command_unban(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"🔓 **{user.name}** has been successfully unbanned.")
        await send_audit_log(interaction.guild, "Member Unbanned", f"**Target:** {user.mention}\n**Moderator:** {interaction.user.mention}", discord.Color.green())
    except discord.NotFound:
        await interaction.response.send_message("❌ User not found or not currently banned.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ Please provide a valid numerical User ID.", ephemeral=True)

@bot.tree.command(name="mute", description="Mute a member by applying the Muted role")
@app_commands.checks.has_permissions(manage_roles=True)
async def command_mute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not role:
        # Create role if it doesn't exist
        role = await interaction.guild.create_role(name="Muted", reason="Mute command executed")
        for channel in interaction.guild.channels:
            await channel.set_permissions(role, send_messages=False, speak=False)
    
    await member.add_roles(role, reason=reason)
    await interaction.response.send_message(f"🤐 **{member.name}** has been muted.")
    await send_audit_log(interaction.guild, "Member Muted", f"**Target:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.dark_grey())

@bot.tree.command(name="unmute", description="Remove the Muted role from a member")
@app_commands.checks.has_permissions(manage_roles=True)
async def command_unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if role in member.roles:
        await member.remove_roles(role)
        await interaction.response.send_message(f"🔊 **{member.name}** has been unmuted.")
        await send_audit_log(interaction.guild, "Member Unmuted", f"**Target:** {member.mention}\n**Moderator:** {interaction.user.mention}", discord.Color.light_grey())
    else:
        await interaction.response.send_message("❌ This member is not currently muted.", ephemeral=True)

@bot.tree.command(name="clear", description="Bulk delete a specific number of messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def command_clear(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        return await interaction.response.send_message("❌ Please specify an amount between 1 and 100.", ephemeral=True)
    
    deleted_messages = await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Successfully cleared **{len(deleted_messages)}** messages.", ephemeral=True)
    await send_audit_log(interaction.guild, "Messages Cleared", f"**Amount:** {len(deleted_messages)}\n**Channel:** {interaction.channel.mention}\n**Moderator:** {interaction.user.mention}", discord.Color.blue())

# ========================================================================
# SECTION 7: UTILITY AND ADMINISTRATION
# ========================================================================
@bot.tree.command(name="dashboard", description="Open the server configuration interface")
@app_commands.checks.has_permissions(administrator=True)
async def command_dashboard(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ EchoBot Configuration Dashboard",
        description="Welcome to the control panel. Select the options below to configure AutoMod, AutoRoles, and Logging.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=ServerManagementDashboard(), ephemeral=True)

@bot.tree.command(name="announce", description="Broadcast an update globally (Owner Only)")
async def command_announce(interaction: discord.Interaction, message: str):
    # HARDCODED CHECK FOR YOUR SPECIFIC USER ID
    if interaction.user.id != 1219266886143967245:
        return await interaction.response.send_message("❌ UNAUTHORIZED: This command is restricted to the bot developer.", ephemeral=True)
    
    success_count = 0
    await interaction.response.defer(ephemeral=True)
    
    for guild in bot.guilds:
        target_channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if target_channel:
            embed = discord.Embed(title="📢 Official System Announcement", description=message, color=discord.Color.gold())
            try:
                await target_channel.send(embed=embed)
                success_count += 1
            except discord.Forbidden:
                pass
                
    await interaction.followup.send(f"✅ Broadcast successfully delivered to **{success_count}** servers.")

@bot.tree.command(name="userinfo", description="View detailed information about a member")
async def command_userinfo(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title=f"User Profile: {member.name}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Account ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%B %d, %Y"), inline=False)
    
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles) if roles else "No specific roles", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="View detailed information about this server")
async def command_serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Server Profile: {guild.name}", color=discord.Color.teal())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Total Members", value=guild.member_count, inline=True)
    embed.add_field(name="Creation Date", value=guild.created_at.strftime("%B %d, %Y"), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cmds", description="List all available EchoBot commands")
async def command_cmds(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 EchoBot Command Directory", color=discord.Color.dark_purple())
    embed.add_field(name="🛡️ Moderation", value="`/kick`, `/ban`, `/unban`, `/mute`, `/unmute`, `/clear`", inline=False)
    embed.add_field(name="📊 Information", value="`/userinfo`, `/serverinfo`", inline=False)
    embed.add_field(name="⚙️ Administration", value="`/dashboard` (Admin), `/announce` (Dev Only)", inline=False)
    embed.set_footer(text="EchoBot Pro System")
    await interaction.response.send_message(embed=embed)

# ========================================================================
# SECTION 8: AUTOMATED EVENTS (AUTOROLE & AUTOMOD)
# ========================================================================
@bot.event
async def on_member_join(member):
    if config["autorole_id"]:
        role = member.guild.get_role(config["autorole_id"])
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                logger.error(f"Failed to assign autorole in {member.guild.name} due to hierarchy/permissions.")
    await send_audit_log(member.guild, "📥 Member Joined", f"{member.mention} has joined the server.", discord.Color.green())

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # AutoMod Logic
    if config["automod"]:
        restricted_words = ["scam", "freemoney", "phishing", "badword1"]
        if any(word in message.content.lower() for word in restricted_words):
            try:
                await message.delete()
                warning = await message.channel.send(f"⚠️ {message.author.mention}, your message was removed for violating server policies.")
                await warning.delete(delay=5)
                await send_audit_log(message.guild, "🛡️ AutoMod Triggered", f"**User:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Action:** Message Deleted", discord.Color.yellow())
            except discord.Forbidden:
                pass

    # Required to process prefix commands if you add any later
    await bot.process_commands(message)

# ========================================================================
# SECTION 9: APPLICATION LAUNCH
# ========================================================================
if __name__ == "__main__":
    # Start the web server on a background thread so Render passes health checks
    threading.Thread(target=start_web_server, daemon=True).start()
    
    bot_token = os.environ.get("TOKEN")
    
    if not bot_token:
        logger.critical("CRITICAL FAILURE: No 'TOKEN' environment variable found. The bot cannot start.")
        exit(1)
        
    try:
        logger.info("Initializing connection to Discord API...")
        bot.run(bot_token.strip())
    except discord.LoginFailure:
        logger.critical("CRITICAL FAILURE: The provided TOKEN is invalid. Please check your Discord Developer Portal.")
        exit(1)
    except Exception as e:
        logger.critical(f"FATAL SYSTEM ERROR: {e}")
        traceback.print_exc()
        exit(1)
