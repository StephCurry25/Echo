import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import json
import traceback
from flask import Flask

# --- SECTION 1: LOGGING & WEB SERVER ---
# Dedicated logging for professional debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EchoBot-Production')

app = Flask(__name__)
@app.route('/')
def health_check(): return "System Status: Online"
def start_web_server(): app.run(host='0.0.0.0', port=8080)

# --- SECTION 2: BOT CONFIGURATION ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Persistent storage logic
CONFIG_FILE = "config.json"
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    return {"automod": False, "autorole_id": None, "log_channel_id": None}

def save_config(data):
    with open(CONFIG_FILE, "w") as f: json.dump(data, f, indent=4)

config = load_config()

# --- SECTION 3: INTERACTIVE DASHBOARD ---
class PersistentDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger)
    async def toggle_automod(self, i: discord.Interaction, b: ui.Button):
        config["automod"] = not config["automod"]
        save_config(config)
        await i.response.send_message(f"AutoMod is now: {config['automod']}", ephemeral=True)

    @ui.role_select(placeholder="Select Autorole")
    async def select_autorole(self, i: discord.Interaction, select: ui.RoleSelect):
        config["autorole_id"] = select.values[0].id
        save_config(config)
        await i.response.send_message(f"Autorole set to: {select.values[0].name}", ephemeral=True)

    @ui.channel_select(placeholder="Select Log Channel", channel_types=[discord.ChannelType.text])
    async def select_log(self, i: discord.Interaction, select: ui.ChannelSelect):
        config["log_channel_id"] = select.values[0].id
        save_config(config)
        await i.response.send_message(f"Logs set to: {select.values[0].mention}", ephemeral=True)

# --- SECTION 4: MODERATION & UTILITY COMMANDS ---
@bot.tree.command(name="dashboard", description="Manage server settings")
async def dashboard(i: discord.Interaction):
    await i.response.send_message("⚙️ **Server Settings**", view=PersistentDashboard(), ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, reason: str = "None"):
    await member.kick(reason=reason)
    await i.response.send_message(f"👢 Kicked {member.name}")

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, reason: str = "None"):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member.name}")

@bot.tree.command(name="mute", description="Mute a user")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
    await member.add_roles(role)
    await i.response.send_message(f"🤐 Muted {member.name}")

@bot.tree.command(name="unmute", description="Unmute a user")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    await member.remove_roles(role)
    await i.response.send_message(f"🔊 Unmuted {member.name}")

@bot.tree.command(name="clear", description="Bulk delete messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, amount: int):
    purged = await i.channel.purge(limit=amount)
    await i.response.send_message(f"🧹 Purged {len(purged)} messages.", ephemeral=True)

# --- SECTION 5: EVENTS & SYNC ---
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

@bot.event
async def on_ready():
    # Persistence for UI components requires adding the view to the bot
    bot.add_view(PersistentDashboard())
    await bot.tree.sync()
    logger.info("Bot is ready and synced.")

if __name__ == "__main__":
    threading.Thread(target=start_web_server, daemon=True).start()
    token = os.environ.get("TOKEN")
    if token: bot.run(token.strip())
