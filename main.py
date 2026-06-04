import os
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
from keep_alive import keep_alive

TOKEN = os.environ.get('TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# --- DATABASE HELPERS ---
def get_db():
    return sqlite3.connect('edith_mainframe.db')

# --- UI COMPONENTS ---
class GateView(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member
    async def interaction_check(self, i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return False
        return True
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, i: discord.Interaction, b: discord.ui.Button):
        db = get_db()
        row = db.execute("SELECT role_id FROM server_settings WHERE guild_id=?", (i.guild.id,)).fetchone()
        db.close()
        if row and row[0]:
            role = i.guild.get_role(int(row[0]))
            if role: await self.member.add_roles(role)
        await i.response.send_message(f"✅ {self.member.name} accepted.")
        self.stop()
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, i: discord.Interaction, b: discord.ui.Button):
        await self.member.kick(reason="Denied at Gate")
        await i.response.send_message(f"❌ {self.member.name} kicked.")
        self.stop()

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.RoleSelect(placeholder="Select newcomer role...", custom_id="role_select"))
    @discord.ui.button(label="Initialize Gate Channel", style=discord.ButtonStyle.danger, row=1)
    async def sec_btn(self, i: discord.Interaction, b: discord.ui.Button):
        channel = discord.utils.get(i.guild.text_channels, name="gate")
        if not channel: channel = await i.guild.create_text_channel("gate")
        await i.response.send_message(f"✅ Gate ready: {channel.mention}", ephemeral=True)

# --- MODERATION COMMANDS ---
@bot.tree.command(name="setup", description="View server setup")
async def setup(i: discord.Interaction):
    embed = discord.Embed(title="⚙️ Echo Setup Panel", description="Configure your server settings below.", color=discord.Color.blue())
    await i.response.send_message(embed=embed, view=SetupView())

@bot.tree.command(name="kick", description="Kick user")
async def kick(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await i.response.send_message(f"👢 Kicked {member.name}")

@bot.tree.command(name="ban", description="Ban user")
async def ban(i: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member.name}")

@bot.tree.command(name="unban", description="Unban user and DM them")
async def unban(i: discord.Interaction, user_id: str):
    user = await bot.fetch_user(int(user_id))
    await i.guild.unban(user)
    try:
        await user.send(f"🔓 You have been unbanned from {i.guild.name}!")
        await i.response.send_message(f"🔓 Unbanned {user.name} and sent DM.")
    except:
        await i.response.send_message(f"🔓 Unbanned {user.name} (DM failed).")

@bot.tree.command(name="mute", description="Mute user")
async def mute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    if not role: role = await i.guild.create_role(name="Muted")
    await member.add_roles(role)
    await i.response.send_message(f"🤐 Muted {member.name}")

@bot.tree.command(name="unmute", description="Unmute user")
async def unmute(i: discord.Interaction, member: discord.Member):
    role = discord.utils.get(i.guild.roles, name="Muted")
    await member.remove_roles(role)
    await i.response.send_message(f"🔊 Unmuted {member.name}")

# --- LISTENER & SYNC ---
@bot.event
async def on_interaction(i):
    if i.type == discord.InteractionType.component and i.data.get("custom_id") == "role_select":
        db = get_db()
        db.execute("INSERT OR REPLACE INTO server_settings (guild_id, role_id) VALUES (?, ?)", (i.guild.id, i.data["values"][0]))
        db.commit()
        db.close()
        await i.response.send_message("✅ Role saved!", ephemeral=True)

@bot.event
async def on_ready():
    keep_alive()
    await bot.tree.sync()
    print("✅ Echo is fully online.")

async def main():
    db = get_db()
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, role_id INTEGER)')
    db.commit()
    db.close()
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
