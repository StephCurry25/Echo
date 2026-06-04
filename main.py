import discord
from discord import app_commands
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration Storage
config = {"welcome_ch": None, "audit_ch": None, "admin_role": None, "theme": "Robot", "assign_role": None}

class TicketOpenView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="📩 Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open(self, i: discord.Interaction, b: discord.ui.Button):
        channel = await i.guild.create_text_channel(f"ticket-{i.user.name}")
        await channel.set_permissions(i.guild.default_role, read_messages=False)
        await channel.set_permissions(i.user, read_messages=True, send_messages=True)
        await i.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
        if config["audit_ch"]:
            await config["audit_ch"].send(f"📂 Ticket opened by {i.user.name}")

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Setup welcome channel, role, and theme")
async def setup(i: discord.Interaction, channel: discord.TextChannel, role: discord.Role, theme: str):
    config.update({"welcome_ch": channel, "assign_role": role, "theme": theme})
    await i.response.send_message(f"✅ Setup complete!\nTheme: {theme}\nChannel: {channel.mention}\nRole to Auto-assign: {role.name}", ephemeral=True)

@bot.tree.command(name="tsetup", description="Setup Ticket System: audit channel and admin role")
async def tsetup(i: discord.Interaction, audit_channel: discord.TextChannel, admin_role: discord.Role):
    config.update({"audit_ch": audit_channel, "admin_role": admin_role})
    await audit_channel.set_permissions(i.guild.default_role, read_messages=False)
    await audit_channel.set_permissions(admin_role, read_messages=True)
    embed = discord.Embed(title="🎟️ Support Center", description="Click below to open a ticket.", color=discord.Color.blue())
    await i.channel.send(embed=embed, view=TicketOpenView())
    await i.response.send_message("✅ Ticket system configured.", ephemeral=True)

# --- MODERATION ---
@bot.tree.command(name="unban", description="Unban a user by username")
async def unban(i: discord.Interaction, username: str):
    async for ban_entry in i.guild.bans():
        if str(ban_entry.user) == username:
            await i.guild.unban(ban_entry.user)
            return await i.response.send_message(f"🔓 Unbanned {username}")
    await i.response.send_message("❌ User not found in ban list.")

# [Keep your kick, ban, mute, unmute commands here as before]

# --- WELCOME LOGIC ---
@bot.event
async def on_member_join(member):
    if config["assign_role"]:
        await member.add_roles(config["assign_role"])
    
    if config["welcome_ch"]:
        themes = {
            "StarWars": f"The Force is strong with {member.mention}! Welcome to the Alliance.",
            "Lego": f"Welcome {member.mention}! Everything is awesome!",
            "Pirate": f"Ahoy {member.mention}! Welcome aboard the ship!",
            "Robot": f"Beep boop! Hello {member.mention}, system online."
        }
        msg = themes.get(config["theme"], f"Welcome {member.mention}!")
        embed = discord.Embed(title="Welcome!", description=msg, color=discord.Color.green())
        await config["welcome_ch"].send(embed=embed)

@bot.event
async def on_ready(): await bot.tree.sync(); print("✅ Online.")

bot.run(os.environ.get("TOKEN"))
