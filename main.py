import os
import discord
import sqlite3
import asyncio
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from threading import Thread
from keep_alive import run_server  # Imports the Render port runner

# ==============================================================================
# --- DATABASE INITIALIZATION ---
# ==============================================================================
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS storage (
        key TEXT PRIMARY KEY, 
        content TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        channel_id INTEGER, 
        end_time TEXT, 
        reason TEXT
    )
''')
db.commit()

# ==============================================================================
# --- CONFIGURATION & SETUP ---
# ==============================================================================
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
ROLE_NAME = "New Comer"
TOKYO_TZ = timezone(timedelta(hours=9))

class EdithBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)
        self.lockdown_active = False

    async def setup_hook(self):
        await self.tree.sync()
        if not self.lockdown_monitor.is_running():
            self.lockdown_monitor.start()
        if not self.reminder_scheduler.is_running():
            self.reminder_scheduler.start()

bot = EdithBot()

@bot.event
async def on_ready():
    print(f"🛰️ Mainframe Online: {bot.user.name}")
    print(f"🔒 Monitoring Owner ID: {OWNER_ID}")

# ==============================================================================
# --- SECURITY LAYERS ---
# ==============================================================================
@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# ==============================================================================
# --- STORAGE UI MODAL ---
# ==============================================================================
class StorageModal(discord.ui.Modal, title='Mainframe: Secure Data Input'):
    data_input = discord.ui.TextInput(
        label='Enter Value',
        style=discord.TextStyle.long,
        placeholder='Paste up to 4,000 characters here...',
        required=True,
        max_length=4000
    )

    def __init__(self, key):
        super().__init__()
        self.key = key

    async def on_submit(self, interaction: discord.Interaction):
        value = str(self.data_input.value)
        cursor.execute('INSERT OR REPLACE INTO storage (key, content) VALUES (?, ?)', (self.key.lower(), value))
        db.commit()
        await interaction.response.send_message(
            content=f"📥 **Data Cached:** Sector `{self.key}` updated in mainframe.", 
            ephemeral=True
        )

class StoreView(discord.ui.View):
    def __init__(self, key):
        super().__init__(timeout=60)
        self.key = key

    @discord.ui.button(label="Open UI Data Entry", style=discord.ButtonStyle.blurple, emoji="🔐")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StorageModal(self.key))

# ==============================================================================
# --- REMINDER INTERACTION INTERFACES ---
# ==============================================================================
class ReminderControl(discord.ui.View):
    def __init__(self, reason):
        super().__init__(timeout=None)
        self.reason = reason

    @discord.ui.button(label="Snooze (10 Mins)", style=discord.ButtonStyle.blurple, emoji="⏳")
    async def snooze(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID: 
            return
        
        now_tokyo = datetime.now(TOKYO_TZ)
        snooze_time = now_tokyo + timedelta(minutes=10)
        snooze_str = snooze_time.isoformat()

        cursor.execute(
            'INSERT INTO reminders (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)',
            (OWNER_ID, interaction.channel_id, snooze_str, f"[Snoozed] {self.reason}")
        )
        db.commit()

        await interaction.response.edit_message(
            content=f"⏰ **Reminder Snoozed.** Re-pinging in 10 minutes (Tokyo: {snooze_time.strftime('%H:%M:%S')}).", 
            view=None
        )

    @discord.ui.button(label="Done", style=discord.ButtonStyle.green, emoji="✅")
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID: 
            return
        await interaction.response.edit_message(content=f"✅ **Task Completed.**", view=None)

# ==============================================================================
# --- GATEWAY 2FA UI PROTOCOLS ---
# ==============================================================================
class EntryProtocol(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="GRANT ACCESS", style=discord.ButtonStyle.green, emoji="🛡️")
    async def grant(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID: 
            return
        role = discord.utils.get(self.member.guild.roles, name=ROLE_NAME)
        if not role:
            role = await self.member.guild.create_role(name=ROLE_NAME)
            
        if role:
            await self.member.add_roles(role)
            await interaction.response.edit_message(content=f"✅ **{self.member.name}** verified into mainframe.", view=None)
        else:
            await interaction.response.send_message(f"❌ Role '{ROLE_NAME}' could not be resolved.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID: 
            return
        await self.member.kick(reason="Entry Protocol Denied by Sovereign.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** safely ejected from systems.", view=None)

# ==============================================================================
# --- SYSTEM ENGINE COMMANDS ---
# ==============================================================================
@bot.command()
async def ping(ctx):
    await ctx.send(f"🛰️ Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🕶️ E.D.I.T.H. MANIFEST", color=0x2b2d31)
    embed.add_field(name="🛡️ CORE", value="`!setup`, `!ping`, `!cmds`", inline=True)
    embed.add_field(name="📦 STORAGE", value="`!store`, `!storage`, `!unstore`, `!delete`", inline=True)
    embed.add_field(name="⏰ ALERTS", value="`!remind [minutes] [reason]`", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def setup(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    category = await ctx.guild.create_category(name="Security", overwrites=overwrites)
    gate = await ctx.guild.create_text_channel('entry-gate', category=category)
    logs = await ctx.guild.create_text_channel('war-room', category=category)
    await ctx.send(f"✅ Security Sectors Configured.\nGate: {gate.mention}\nWar Room: {logs.mention}")

@bot.command()
async def remind(ctx, minutes: int, *, reason: str):
    now_tokyo = datetime.now(TOKYO_TZ)
    end_time = now_tokyo + timedelta(minutes=minutes)
    end_time_str = end_time.isoformat()

    cursor.execute(
        'INSERT INTO reminders (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)',
        (OWNER_ID, ctx.channel.id, end_time_str, reason)
    )
    db.commit()
    await ctx.send(f"⏰ **Reminder Set.**\n📅 **Tokyo Target:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

# ==============================================================================
# --- HARDWARE STORAGE SYSTEM ---
# ==============================================================================
@bot.command()
async def store(ctx, k: str = None):
    if not k:
        return await ctx.send("⚠️ Key required: `!store [key_name]`")
    await ctx.send(f"🔐 **Mainframe Secure Entry Mode:** Operational for block `{k}`.", view=StoreView(k))

@bot.command()
async def unstore(ctx, k):
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    if res:
        await ctx.send(f"📦 Data:\n{res[0]}")
    else:
        await ctx.send("❌ Data segment not found within current tables.")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    res = cursor.fetchall()
    keys = "\n".join([f"• {r[0]}" for r in res]) if res else "No keys currently registered."
    await ctx.send(embed=discord.Embed(title="🗄️ STORAGE INDEX", description=keys, color=0x3498db))

@bot.command()
async def delete(ctx, k):
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    await ctx.send(f"🗑️ Purged sector `{k}` completely from local hardware tables.")

# ==============================================================================
# --- APPLICATION INTELLIGENCE MODULES ---
# ==============================================================================
@bot.tree.command(name="server-info", description="Gathers server intel")
async def server_info(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return
    g = interaction.guild
    embed = discord.Embed(title=f"📊 INTEL: {g.name}", color=0x00ffff)
    embed.add_field(name="Total Members", value=g.member_count)
    await interaction.response.send_message(embed=embed)

# ==============================================================================
# --- CHRONO SCHEDULERS & AUTOMATION ---
# ==============================================================================
@tasks.loop(seconds=1)
async def reminder_scheduler():
    now_tokyo = datetime.now(TOKYO_TZ)
    cursor.execute('SELECT id, channel_id, end_time, reason FROM reminders')
    rows = cursor.fetchall()
    
    for row in rows:
        rem_id, channel_id, end_time_str, reason = row
        end_time = datetime.fromisoformat(end_time_str)
        
        if now_tokyo >= end_time:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(content=f"🚨 <@{OWNER_ID}> **ALERT:** {reason}", view=ReminderControl(reason))
                except:
                    pass
            cursor.execute('DELETE FROM reminders WHERE id = ?', (rem_id,))
            db.commit()

@tasks.loop(seconds=3)
async def lockdown_monitor():
    for guild in bot.guilds:
        owner = guild.get_member(OWNER_ID)
        if not owner:
            continue
        
        is_offline = (owner.status == discord.Status.offline)
        
        if is_offline and not bot.lockdown_active:
            bot.lockdown_active = True
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=False)
                except:
                    pass
            print("🔒 Lockdown Mode: Active. Server channels clamped down.")
        elif not is_offline and bot.lockdown_active:
            bot.lockdown_active = False
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=None)
                except:
                    pass
            print("🔓 Lockdown Mode: Terminated. Baseline permissions restored.")

# ==============================================================================
# --- SIGNAL CAPTURE AND BACKLOGS ---
# ==============================================================================
@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate:
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **2FA ENTRY PROTOCOL REQUIRED**", view=EntryProtocol(member))

@bot.event
async def on_bulk_message_delete(messages):
    logs = discord.utils.get(messages[0].guild.text_channels, name="war-room")
    if logs:
        await logs.send(f"🗑️ **Bulk Delete Event:** {len(messages)} messages dropped in {messages[0].channel.mention}")

# ==============================================================================
# --- ENGINE RUNTIME LIFECYCLE ---
# ==============================================================================
def run_bot_worker():
    """Executes the bot initialization loop cleanly inside an independent thread context."""
    try:
        print("🛰 ...Connecting to Discord Gateway via Background Pipeline...")
        bot.run(TOKEN.strip())
    except Exception as e:
        print(f"❌ Discord core gateway failure: {e}")

if __name__ == "__main__":
    if TOKEN:
        # 1. Launch the Discord listener loop safely inside a background worker thread
        bot_thread = Thread(target=run_bot_worker)
        bot_thread.daemon = True
        bot_thread.start()

        # 2. Bind the main thread completely to the Flask server. 
        # This satisfies Render's strict port checks and blocks early exits.
        print("🌐 Anchoring web production server on assigned Render port.")
        try:
            run_server()
        except Exception as e:
            print(f"❌ Web engine failed to bind to network port: {e}")
    else:
        print("❌ FATAL: TOKEN environment variable is missing in Render dashboard.")
