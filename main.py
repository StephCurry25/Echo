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
def get_role_id(guild_id):
    db = sqlite3.connect('edith_mainframe.db')
    row = db.execute("SELECT role_id FROM server_settings WHERE guild_id=?", (guild_id,)).fetchone()
    db.close()
    return row[0] if row else None

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
        role_id = get_role_id(i.guild.id)
        if role_id:
            role = i.guild.get_role(int(role_id))
            if role: await self.member.add_roles(role)
        await i.response.send_message(f"✅ {self.member.name} accepted and role assigned.")
        self.stop()
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, i: discord.Interaction, b: discord.ui.Button):
        await self.member.kick(reason="Denied at Gate")
        await i.response.send_message(f"❌ {self.member.name} kicked.")
        self.stop()

class RoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Select newcomer role...")
    async def callback(self, i: discord.Interaction):
        role = self.values[0]
        db = sqlite3.connect('edith_mainframe.db')
        db.execute("INSERT OR REPLACE INTO server_settings (guild_id, role_id) VALUES (?, ?)", (i.guild.id, role.id))
        db.commit()
        db.close()
        await i.response.send_message(f"✅ Saved role: {role.name}", ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())
    @discord.ui.button(label="Create/Reset Gate", style=discord.ButtonStyle.danger, row=2)
    async def sec_btn(self, i: discord.Interaction, b: discord.ui.Button):
        channel = discord.utils.get(i.guild.text_channels, name="gate")
        if not channel: channel = await i.guild.create_text_channel("gate")
        await i.response.send_message(f"✅ Gate ready: {channel.mention}", ephemeral=True)

# --- COMMANDS ---
@bot.tree.command(name="setup", description="Open Setup UI")
async def setup(i: discord.Interaction):
    await i.response.send_message("Server Setup:", view=SetupView())

# ... [Keep your other moderation/AFK commands exactly as they were] ...

@bot.event
async def on_ready():
    keep_alive()
    await bot.tree.sync()
    print("✅ Echo is online.")

async def main():
    db = sqlite3.connect('edith_mainframe.db')
    db.execute('CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, role_id INTEGER)')
    db.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)')
    db.commit()
    db.close()
    await bot.start(TOKEN.strip())

if __name__ == "__main__":
    asyncio.run(main())
