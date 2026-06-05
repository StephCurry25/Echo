import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import asyncio
from flask import Flask

# --- ADVANCED LOGGING CONFIGURATION ---
# We use a dedicated logger to track bot health and command execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('ProBot')

# --- WEB SERVER (Health Check Endpoint) ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Bot status: OPERATIONAL", 200

def start_web_server():
    app.run(host='0.0.0.0', port=8080)

# --- BOT INITIALIZATION ---
# Intents explicitly defined for granular control
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- GLOBAL CONFIGURATION STORE ---
# In a professional setting, this would be an external PostgreSQL or MongoDB database
bot_config = {
    "automod": False,
    "autorole_id": None,
    "log_channel_id": None,
    "muted_role_name": "Muted"
}

# --- UI DASHBOARD (Interactive Class-based View) ---
class ManagementDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.select(
        placeholder="Select a Server Module...",
        options=[
            discord.SelectOption(label="AutoMod", description="Toggle message filtering"),
            discord.SelectOption(label="Autorole", description="Configure join roles"),
            discord.SelectOption(label="Audit Logs", description="Configure activity logging")
        ]
    )
    async def select_module(self, interaction: discord.Interaction, select: ui.Select):
        module = select.values[0]
        if module == "AutoMod":
            bot_config["automod"] = not bot_config["automod"]
            status = "enabled" if bot_config["automod"] else "disabled"
            await interaction.response.send_message(f"✅ AutoMod has been {status}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Module '{module}' configuration requires specific command usage.", ephemeral=True)

# --- SLASH COMMANDS (Modularized Logic) ---

@bot.tree.command(name="dashboard", description="Open the full server management UI")
async def dashboard(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ Server Management Dashboard",
        description="Select a module below to configure your server's automated features.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=ManagementDashboard(), ephemeral=True)

@bot.tree.command(name="announce", description="Broadcast a message to all connected servers")
async def announce(interaction: discord.Interaction, message: str):
    # Security check for ownership
    if interaction.user.id != 1219266886143967245:
        await interaction.response.send_message("❌ Access Denied.", ephemeral=True)
        return
    
    success_count = 0
    for guild in bot.guilds:
        # Attempt to find the system channel or the first available text channel
        target_channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if target_channel:
            embed = discord.Embed(title="📢 Global Announcement", description=message, color=discord.Color.red())
            await target_channel.send(embed=embed)
            success_count += 1
            
    await interaction.response.send_message(f"✅ Broadcast complete. Message sent to {success_count} guilds.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    embed = discord.Embed(title="👢 Member Kicked", description=f"{member.mention} has been kicked.", color=discord.Color.orange())
    embed.add_field(name="Reason", value=reason)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    embed = discord.Embed(title="🔨 Member Banned", description=f"{member.mention} has been banned.", color=discord.Color.red())
    embed.add_field(name="Reason", value=reason)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unban", description="Unban a user by ID")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"🔓 Successfully unbanned {user.name}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="mute", description="Mute a member by assigning the Muted role")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name=bot_config["muted_role_name"])
    if not role:
        role = await interaction.guild.create_role(name=bot_config["muted_role_name"], permissions=discord.Permissions(send_messages=False))
    await member.add_roles(role)
    await interaction.response.send_message(f"🤐 {member.name} has been muted.")

@bot.tree.command(name="unmute", description="Unmute a member")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name=bot_config["muted_role_name"])
    if role and role in member.roles:
        await member.remove_roles(role)
        await interaction.response.send_message(f"🔊 {member.name} has been unmuted.")
    else:
        await interaction.response.send_message("❌ User is not currently muted.")

@bot.tree.command(name="clear", description="Bulk delete messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    if amount > 100: amount = 100
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Successfully cleared {len(deleted)} messages.", ephemeral=True)

@bot.tree.command(name="userinfo", description="Display auditing information for a member")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title=f"User Audit: {member.name}", color=discord.Color.green())
    embed.add_field(name="User ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Roles", value=", ".join([role.name for role in member.roles if role.name != "@everyone"]), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Display server statistics")
async def serverinfo(interaction: discord.Interaction):
    embed = discord.Embed(title=f"Server Audit: {interaction.guild.name}", color=discord.Color.green())
    embed.add_field(name="Member Count", value=interaction.guild.member_count, inline=True)
    embed.add_field(name="Owner", value=interaction.guild.owner, inline=True)
    await interaction.response.send_message(embed=embed)

# --- EVENT HANDLERS ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # AutoMod execution logic
    if bot_config["automod"]:
        forbidden_terms = ["badword1", "scamlink"]
        if any(term in message.content.lower() for term in forbidden_terms):
            await message.delete()
            await message.channel.send(f"⚠️ {message.author.mention}, that message was removed for violating rules.", delete_after=3)
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    # Autorole execution logic
    if bot_config["autorole_id"]:
        role = member.guild.get_role(bot_config["autorole_id"])
        if role:
            await member.add_roles(role)
            logger.info(f"Autorole applied to {member.name}")

@bot.event
async def on_ready():
    # Force sync command tree for immediate visibility
    synced = await bot.tree.sync()
    logger.info(f"Bot connected as {bot.user}")
    logger.info(f"Synchronized {len(synced)} slash commands.")
    print("--- SYSTEM READY ---")

# --- INITIALIZATION ---
if __name__ == "__main__":
    # Initiate Flask server in a background thread
    server_thread = threading.Thread(target=start_web_server, daemon=True)
    server_thread.start()
    
    # Secure token retrieval
    bot_token = os.environ.get("TOKEN")
    if not bot_token:
        print("CRITICAL ERROR: No bot token found.")
    else:
        bot.run(bot_token.strip())
