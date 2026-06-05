import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import json
import traceback

# --- 1. SETUP & CRASH PROTECTION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EchoBot-FIXED')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# We wrap the bot in a class to ensure it loads fully
class EchoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
    
    async def setup_hook(self):
        # Adding the view here makes the buttons persistent
        self.add_view(PersistentDashboard())
        await self.tree.sync()
        logger.info("Commands synced and views registered.")

bot = EchoBot()

# --- 2. STORAGE (Check for config.json) ---
def load_config():
    if not os.path.exists("config.json"):
        with open("config.json", "w") as f: json.dump({"automod": False, "autorole_id": None}, f)
    with open("config.json", "r") as f: return json.load(f)

config = load_config()

# --- 3. UI DASHBOARD ---
class PersistentDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger)
    async def toggle(self, i: discord.Interaction, b: ui.Button):
        config["automod"] = not config["automod"]
        await i.response.send_message(f"AutoMod: {config['automod']}", ephemeral=True)

    @ui.role_select(placeholder="Select Autorole")
    async def autorole(self, i: discord.Interaction, s: ui.RoleSelect):
        config["autorole_id"] = s.values[0].id
        await i.response.send_message(f"Autorole: {s.values[0].name}", ephemeral=True)

# --- 4. COMMANDS ---
@bot.tree.command(name="dashboard", description="Open settings")
async def dashboard(i: discord.Interaction):
    await i.response.send_message("⚙️", view=PersistentDashboard(), ephemeral=True)

@bot.tree.command(name="kick", description="Kick user")
async def kick(i: discord.Interaction, m: discord.Member, r: str = "None"):
    await m.kick(reason=r); await i.response.send_message(f"Kicked {m.name}")

@bot.tree.command(name="ban", description="Ban user")
async def ban(i: discord.Interaction, m: discord.Member, r: str = "None"):
    await m.ban(reason=r); await i.response.send_message(f"Banned {m.name}")

@bot.tree.command(name="mute", description="Mute user")
async def mute(i: discord.Interaction, m: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
    await m.add_roles(role); await i.response.send_message(f"Muted {m.name}")

@bot.tree.command(name="unmute", description="Unmute user")
async def unmute(i: discord.Interaction, m: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    await m.remove_roles(role); await i.response.send_message(f"Unmuted {m.name}")

@bot.tree.command(name="clear", description="Clear chat")
async def clear(i: discord.Interaction, n: int):
    d = await i.channel.purge(limit=n)
    await i.response.send_message(f"Cleared {len(d)}", ephemeral=True)

@bot.tree.command(name="userinfo", description="User info")
async def userinfo(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"{m.name} | ID: {m.id}")

@bot.tree.command(name="announce", description="Global broadcast")
async def announce(i: discord.Interaction, msg: str):
    if i.user.id != 1219266886143967245: return
    for g in bot.guilds:
        if g.system_channel: await g.system_channel.send(f"📢 {msg}")
    await i.response.send_message("Sent.")

# --- 5. FINAL LAUNCH ---
if __name__ == "__main__":
    token = os.environ.get("TOKEN")
    if not token:
        logger.error("!!! TOKEN IS MISSING. Check your environment variables.")
        exit(1) # This is why you get Status 1
    try:
        bot.run(token.strip())
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        traceback.print_exc()
