import discord
from discord import app_commands
from discord.ext import commands

# 1. HARDCODED TOKEN - ONLY FOR TESTING
# Paste your token here between the quotes
TOKEN = "PASTE_YOUR_TOKEN_HERE_EXACTLY" 

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is online and ready as {bot.user}")

# --- YOUR COMMANDS HERE ---
# (I have removed the complex config to ensure this runs)

@bot.tree.command(name="ping", description="Test if bot is working")
async def ping(i: discord.Interaction):
    await i.response.send_message("Pong!")

if __name__ == "__main__":
    if TOKEN == "PASTE_YOUR_TOKEN_HERE_EXACTLY":
        print("❌ ERROR: You didn't paste your token!")
    else:
        bot.run(TOKEN)
