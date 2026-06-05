import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import json
import logging
from flask import Flask

# --- 1. LOGGING & WEB ---
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is live"
def start_web(): app.run(host='0.0.0.0', port=8080)

# --- 2. CONFIG ---
CONFIG_FILE = "config.json"
def get_config():
    if not os.path.exists(CONFIG_FILE): return {"automod": False, "autorole_id": None}
    with open(CONFIG_FILE, "r") as f: return json.load(f)

config = get_config()

# --- 3. UI DASHBOARD ---
class Dashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger)
    async def toggle(self, i: discord.Interaction, b: ui.Button):
        config["automod"] = not config["automod"]
        await i.response.send_message(f"AutoMod: {config['automod']}", ephemeral=True)
    
    @ui.select(cls=ui.RoleSelect, placeholder="Select Autorole")
    async def role_sel(self, i: discord.Interaction, s: ui.RoleSelect):
        config["autorole_id"] = s.values[0].id
        await i.response.send_message(f"Set: {s.values[0].name}", ephemeral=True)

# --- 4. BOT CORE ---
class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self):
        self.add_view(Dashboard())
        await self.tree.sync()

bot = Bot()

# --- 5. COMMANDS ---
@bot.tree.command(name="dashboard", description="Open UI")
async def dashboard(i: discord.Interaction):
    await i.response.send_message("⚙️", view=Dashboard(), ephemeral=True)

@bot.tree.command(name="announce", description="Global broadcast")
async def announce(i: discord.Interaction, msg: str):
    if i.user.id != 1219266886143967245: return await i.response.send_message("❌", ephemeral=True)
    for g in bot.guilds:
        if g.system_channel: await g.system_channel.send(f"📢 {msg}")
    await i.response.send_message("Sent.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, m: discord.Member):
    await m.kick(); await i.response.send_message(f"Kicked {m.name}")

@bot.tree.command(name="ban", description="Ban member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, m: discord.Member):
    await m.ban(); await i.response.send_message(f"Banned {m.name}")

@bot.tree.command(name="mute", description="Mute member")
async def mute(i: discord.Interaction, m: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
    await m.add_roles(role); await i.response.send_message("Muted.")

@bot.tree.command(name="clear", description="Clear chat")
async def clear(i: discord.Interaction, n: int):
    await i.channel.purge(limit=n); await i.response.send_message("Done.", ephemeral=True)

# --- 6. LAUNCH ---
if __name__ == "__main__":
    threading.Thread(target=start_web, daemon=True).start()
    token = os.environ.get("TOKEN")
    if not token:
        print("CRITICAL: Environment variable 'TOKEN' is missing.")
        exit(1)
    bot.run(token)
