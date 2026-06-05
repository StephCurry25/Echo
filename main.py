import discord
from discord import app_commands
from discord.ext import commands
import os
import threading
from flask import Flask

# --- WEB SERVER & HEARTBEAT (Keeps bot awake) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is awake!"
def run_web_server(): app.run(host='0.0.0.0', port=8080)

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

config = {"welcome_ch": None, "assign_role": None, "theme": "Robot"}

# --- COMMANDS ---
@bot.tree.command(name="cmds", description="List all commands")
async def cmds(i: discord.Interaction):
    embed = discord.Embed(title="📜 Command List", color=discord.Color.gold())
    embed.add_field(name="Moderation", value="/kick, /ban, /unban, /mute, /unmute, /clear, /lock, /unlock", inline=False)
    embed.add_field(name="Management", value="/setup, /userinfo, /poll", inline=False)
    await i.response.send_message(embed=embed)

@bot.tree.command(name="unban", description="Unban a user by username or ID")
async def unban(i: discord.Interaction, user_input: str):
    bans = [entry async for entry in i.guild.bans()]
    for entry in bans:
        if str(entry.user) == user_input or str(entry.user.id) == user_input:
            await i.guild.unban(entry.user)
            return await i.response.send_message(f"🔓 Successfully unbanned: {entry.user}")
    await i.response.send_message("❌ User not found in the ban list. Please check the spelling or ID.")

@bot.tree.command(name="setup", description="Configure welcome settings")
async def setup(i: discord.Interaction, channel: discord.TextChannel, role: discord.Role, theme: str):
    config.update({"welcome_ch": channel, "assign_role": role, "theme": theme})
    await i.response.send_message(f"✅ Configured! Channel: {channel.mention}, Theme: {theme}", ephemeral=True)

@bot.tree.command(name="clear", description="Clear messages")
async def clear(i: discord.Interaction, amount: int):
    deleted = await i.channel.purge(limit=amount)
    await i.response.send_message(f"🧹 Cleared {len(deleted)} messages.", ephemeral=True)

@bot.tree.command(name="userinfo", description="Get user info")
async def userinfo(i: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title=f"User: {member.name}", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    await i.response.send_message(embed=embed)

@bot.tree.command(name="lock", description="Lock channel")
async def lock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("🔒 Channel locked.")

@bot.tree.command(name="unlock", description="Unlock channel")
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message("🔓 Channel unlocked.")

@bot.tree.command(name="poll", description="Create a poll")
async def poll(i: discord.Interaction, question: str):
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.purple())
    msg = await i.channel.send(embed=embed)
    await msg.add_reaction("👍"); await msg.add_reaction("👎")
    await i.response.send_message("✅ Poll created!", ephemeral=True)

# --- EVENTS ---
@bot.event
async def on_member_join(member):
    if config["assign_role"]: await member.add_roles(config["assign_role"])
    if config["welcome_ch"]:
        themes = {"StarWars": "The Force is with you!", "Lego": "Everything is awesome!", "Pirate": "Ahoy!", "Robot": "System online."}
        msg = themes.get(config["theme"], "Welcome!")
        await config["welcome_ch"].send(embed=discord.Embed(title="Welcome!", description=f"{msg} {member.mention}", color=discord.Color.green()))

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Bot is online and synced.")

if __name__ == "__main__":
    threading.Thread(target=run_web_server).start()
    token = os.environ.get("TOKEN")
    if token: bot.run(token.strip())
