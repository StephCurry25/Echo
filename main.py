import discord
from discord.ext import commands
from discord import app_commands
import os
import sqlite3
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- TICKET & MODERATION UI ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        category = discord.utils.get(i.guild.categories, name="Tickets")
        if not category: category = await i.guild.create_category("Tickets")
        channel = await i.guild.create_text_channel(f"ticket-{i.user.name}", category=category)
        await channel.set_permissions(i.guild.default_role, read_messages=False)
        await channel.set_permissions(i.user, read_messages=True, send_messages=True)
        await i.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Setup Ticket System")
async def setup(i: discord.Interaction):
    embed = discord.Embed(title="Support Center", description="Click below to open a ticket.", color=discord.Color.blue())
    await i.response.send_message(embed=embed, view=TicketView())

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await i.response.send_message(f"👢 Kicked {member.name}")

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member.name}")

@bot.tree.command(name="unban", description="Unban a user by ID")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(i: discord.Interaction, user_id: str):
    user = await bot.fetch_user(int(user_id))
    await i.guild.unban(user)
    await i.response.send_message(f"🔓 Unbanned {user.name}")

@bot.tree.command(name="mute", description="Mute a member")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted")
    await member.add_roles(role)
    await i.response.send_message(f"🤐 Muted {member.name}")

@bot.tree.command(name="unmute", description="Unmute a member")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    await member.remove_roles(role)
    await i.response.send_message(f"🔊 Unmuted {member.name}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is ready as {bot.user}")
    keep_alive()

if __name__ == "__main__":
    bot.run(os.environ.get("TOKEN").strip())
