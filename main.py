import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- TICKET & AUDIT UTILS ---
async def setup_audit_channel(guild):
    # Delete existing audit channel if it exists
    existing_channel = discord.utils.get(guild.text_channels, name="ticket-audit")
    if existing_channel:
        await existing_channel.delete()
    
    # Create new fresh audit channel
    new_audit = await guild.create_text_channel("ticket-audit")
    return new_audit

# --- UI & COMMANDS ---
@bot.tree.command(name="setup", description="Initialize bot configuration")
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Bot Setup Configuration",
        description="Select an option below to initialize features.",
        color=discord.Color.blue()
    )
    # View with buttons for Audit/Tickets
    view = discord.ui.View()
    
    async def audit_callback(i: discord.Interaction):
        await setup_audit_channel(i.guild)
        await i.response.send_message("✅ Audit channel reset successfully.", ephemeral=True)
        
    btn = discord.ui.Button(label="Reset Audit Channel", style=discord.ButtonStyle.danger)
    btn.callback = audit_callback
    view.add_item(btn)
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="unban", description="Unban a user and DM them")
async def unban(interaction: discord.Interaction, user_id: str):
    user = await bot.fetch_user(int(user_id))
    try:
        await interaction.guild.unban(user)
        try:
            await user.send(f"🔓 You have been unbanned from {interaction.guild.name}!")
            await interaction.response.send_message(f"🔓 Unbanned {user.name} and notified via DM.")
        except discord.Forbidden:
            await interaction.response.send_message(f"🔓 Unbanned {user.name}, but could not send DM (DMs disabled).")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to unban: {e}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

bot.run("YOUR_TOKEN_HERE")
