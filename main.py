import discord
from discord.ext import commands
from discord import app_commands
import os
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- TICKET CONTROL PANEL ---
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message("❌ Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        await i.channel.delete()

# --- OPEN TICKET BUTTON ---
class TicketOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Open Support Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        category = discord.utils.get(i.guild.categories, name="Tickets")
        if not category: category = await i.guild.create_category("Tickets")
        
        channel = await i.guild.create_text_channel(f"ticket-{i.user.name}", category=category)
        await channel.set_permissions(i.guild.default_role, read_messages=False)
        await channel.set_permissions(i.user, read_messages=True, send_messages=True)
        
        embed = discord.Embed(
            title="🎟️ Support Ticket",
            description=f"**User:** {i.user.mention}\n**ID:** `{i.user.id}`\n\nPlease describe your issue. Support staff will be with you shortly.",
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=TicketControlView())
        await i.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Setup Ticket System")
async def setup(i: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ Echo Support Center",
        description="Need help? Click the button below to open a private ticket. Please be patient while waiting for an admin.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Echo Tickets v2")
    await i.response.send_message(embed=embed, view=TicketOpenView())

# ... [Keep your other moderation commands (/kick, /ban, /mute, etc.) here] ...

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is ready as {bot.user}")
    keep_alive()

if __name__ == "__main__":
    bot.run(os.environ.get("TOKEN").strip())
