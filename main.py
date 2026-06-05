import discord
from discord import app_commands
from discord.ext import commands
import os
import threading
from flask import Flask

# --- WEB SERVER (Port 8080) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is awake!"
def run_web_server(): app.run(host='0.0.0.0', port=8080)

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- GLOBAL ANNOUNCE (Dyno-style) ---
@bot.tree.command(name="announce", description="Send an update to all servers")
async def announce(i: discord.Interaction, message: str):
    # Authorized User ID
    if i.user.id != 1219266886143967245: 
        return await i.response.send_message("❌ You are not authorized to use this.", ephemeral=True)
    
    count = 0
    embed = discord.Embed(title="📢 Bot Update", description=message, color=discord.Color.red())
    for guild in bot.guilds:
        channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if channel:
            await channel.send(embed=embed)
            count += 1
            
    await i.response.send_message(f"✅ Announcement sent to {count} servers.", ephemeral=True)

# --- MODERATION & UTILS ---
@bot.tree.command(name="ban", description="Ban a user")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member.name}")

@bot.tree.command(name="clear", description="Clear messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, amount: int):
    deleted = await i.channel.purge(limit=amount)
    await i.response.send_message(f"🧹 Cleared {len(deleted)} messages.", ephemeral=True)

# --- BOT STARTUP ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is live as {bot.user}")

if __name__ == "__main__":
    threading.Thread(target=run_web_server).start()
    token = os.environ.get("TOKEN")
    if token: bot.run(token.strip())
