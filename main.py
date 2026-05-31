import os, discord, sqlite3, flask, asyncio
from discord.ext import commands, tasks
from threading import Thread
from datetime import datetime, timedelta, timezone

# --- DATABASE ---
db = sqlite3.connect('edith_mainframe.db')
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS storage (key TEXT PRIMARY KEY, content TEXT)')
# New table to persist active reminders across bot restarts
cursor.execute('CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, channel_id INTEGER, end_time TEXT, reason TEXT)')
db.commit()

# --- WEB SERVER (Required for Render Web Service) ---
app = flask.Flask('')

@app.route('/')
def home(): 
    return "E.D.I.T.H. Mainframe: Online and Secure"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = os.environ.get('TOKEN')
OWNER_ID = 1219266886143967245 
ROLE_NAME = "New Comer"

# Tokyo Time Zone Definition (GMT +9)
TOKYO_TZ = timezone(timedelta(hours=9))

class EdithBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)
        self.lockdown_active = False

    async self_setup_hook(self): # Keeping function layout structured for setup hook
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
    print(f"⏰ System Time Configured to Tokyo Zone (GMT+9)")

# --- 🔒 SOVEREIGNTY ---
@bot.check
async def globally_only_owner(ctx):
    return ctx.author.id == OWNER_ID

# --- 📥 STORAGE UI MODAL (4K LIMIT BYPASS) ---
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
        await interaction.response.send_message(f"📥 **Data Cached:** Sector `{self.key}` updated in mainframe.", ephemeral=True)

class StoreView(discord.ui.View):
    def __init__(self, key):
        super().__init__(timeout=60)
        self.key = key

    @discord.ui.button(label="Open UI Data Entry", style=discord.ButtonStyle.blurple, emoji="🔐")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StorageModal(self.key))

# --- ⏰ REMINDER SNOOZE / DONE UI ---
class ReminderControl(discord.ui.View):
    def __init__(self, reason):
        super().__init__(timeout=None)
        self.reason = reason

    @discord.ui.button(label="Snooze (10 Mins)", style=discord.ButtonStyle.blurple, emoji="⏳")
    async def snooze(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID: return
        
        # Calculate 10 minutes from now in Tokyo Time
        now_tokyo = datetime.now(TOKYO_TZ)
        snooze_time = now_tokyo + timedelta(minutes=10)
        snooze_str = snooze_time.isoformat()

        cursor.execute(
            'INSERT INTO reminders (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)',
            (OWNER_ID, interaction.channel_id, snooze_str, f"[Snoozed] {self.reason}")
        )
        db.commit()

        await interaction.response.edit_message(
            content=f"⏰ **Reminder Snoozed.** E.D.I.T.H. will re-ping you in 10 minutes (Tokyo Time: {snooze_time.strftime('%H:%M:%S')}).", 
            view=None
        )

    @discord.ui.button(label="Done", style=discord.ButtonStyle.green, emoji="✅")
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID: return
        await interaction.response.edit_message(content=f"✅ **Task Completed:** Task dropped from active alerts.", view=None)

# --- 🛡️ 2FA UI ---
class EntryProtocol(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="GRANT ACCESS", style=discord.ButtonStyle.green, emoji="🛡️")
    async def grant(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID: return
        role = discord.utils.get(self.member.guild.roles, name=ROLE_NAME)
        if not role:
            role = await self.member.guild.create_role(name=ROLE_NAME)
            
        if role:
            await self.member.add_roles(role)
            await interaction.response.edit_message(content=f"✅ **{self.member.name}** verified.", view=None)
        else:
            await interaction.response.send_message(f"❌ Role '{ROLE_NAME}' missing.", ephemeral=True)

    @discord.ui.button(label="EJECT TARGET", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID: return
        await self.member.kick(reason="Entry Denied.")
        await interaction.response.edit_message(content=f"🚫 **{self.member.name}** ejected.", view=None)

# --- 🛠️ CORE COMMANDS ---
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
    """Creates a 'Security' Category and places core channels inside it hidden from @everyone"""
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    
    # Create the requested 'Security' Category
    category = await ctx.guild.create_category(name="Security", overwrites=overwrites)
    
    # Create structural channels directly tied inside the Category
    gate = await ctx.guild.create_text_channel('entry-gate', category=category)
    logs = await ctx.guild.create_text_channel('war-room', category=category)
    
    await ctx.send(f"✅ Security Category and Sectors Configured.\nGate: {gate.mention}\nWar Room: {logs.mention}")

# --- ⏰ REMINDER LOGIC ---
@bot.command()
async def remind(ctx, minutes: int, *, reason: str):
    """Sets a reminder using Tokyo Standard Time (GMT+9)"""
    now_tokyo = datetime.now(TOKYO_TZ)
    end_time = now_tokyo + timedelta(minutes=minutes)
    end_time_str = end_time.isoformat()

    cursor.execute(
        'INSERT INTO reminders (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)',
        (OWNER_ID, ctx.channel.id, end_time_str, reason)
    )
    db.commit()

    await ctx.send(f"⏰ **Reminder Set.** E.D.I.T.H. will alert you in {minutes} minutes.\n📅 **Tokyo Target Time:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

# --- 📦 STORAGE LAYER ---
@bot.command()
async def store(ctx, k: str = None):
    """Bypasses standard chat limits using Modal inputs up to 4k chars"""
    if not k:
        return await ctx.send("⚠️ Key required: `!store [key_name]`")
    await ctx.send(f"🔐 **Mainframe Secure Entry Mode:** Operational for block `{k}`.", view=StoreView(k))

@bot.command()
async def unstore(ctx, k):
    cursor.execute("SELECT content FROM storage WHERE key=?", (k.lower(),))
    res = cursor.fetchone()
    if res: 
        await ctx.send(f"📦 Data: `{res[0]}`")
    else: 
        await ctx.send("❌ Not found.")

@bot.command()
async def storage(ctx):
    cursor.execute("SELECT key FROM storage")
    res = cursor.fetchall()
    keys = "\n".join([f"• {r[0]}" for r in res]) if res else "Empty."
    await ctx.send(embed=discord.Embed(title="🗄️ STORAGE", description=keys, color=0x3498db))

@bot.command()
async def delete(ctx, k):
    cursor.execute("DELETE FROM storage WHERE key=?", (k.lower(),))
    db.commit()
    await ctx.send(f"🗑️ Purged `{k}`")

# --- 📊 SLASH ---
@bot.tree.command(name="server-info", description="Gathers server intel")
async def server_info(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return
    g = interaction.guild
    embed = discord.Embed(title=f"📊 INTEL: {g.name}", color=0x00ffff)
    embed.add_field(name="Members", value=g.member_count)
    await interaction.response.send_message(embed=embed)

# --- ⏰ REAL-TIME CLOCK TASK (1-SECOND ENGINE CHECK) ---
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
                    await channel.send(
                        content=f"🚨 <@{OWNER_ID}> **ALERT:** {reason}", 
                        view=ReminderControl(reason)
                    )
                except Exception as e:
                    print(f"Error distributing alert: {e}")
            
            # Clean processed reminder from DB
            cursor.execute('DELETE FROM reminders WHERE id = ?', (rem_id,))
            db.commit()

# --- 🔐 3-SECOND LOCKDOWN ---
@tasks.loop(seconds=3)
async def lockdown_monitor():
    for guild in bot.guilds:
        owner = guild.get_member(OWNER_ID)
        if not owner: continue
        
        is_offline = (owner.status == discord.Status.offline)
        
        if is_offline and not bot.lockdown_active:
            bot.lockdown_active = True
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=False)
                except: pass
            print("🔒 Lockdown: Active.")
        elif not is_offline and bot.lockdown_active:
            bot.lockdown_active = False
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=None)
                except: pass
            print("🔓 Lockdown: Lifted.")

# --- 🚨 LOGS & EVENTS ---
@bot.event
async def on_member_join(member):
    gate = discord.utils.get(member.guild.text_channels, name="entry-gate")
    if gate: 
        await gate.send(content=f"🚨 <@{OWNER_ID}> — **2FA REQUIRED**", view=EntryProtocol(member))

@bot.event
async def on_bulk_message_delete(messages):
    logs = discord.utils.get(messages[0].guild.text_channels, name="war-room")
    if logs: 
        await logs.send(f"🗑️ **Bulk Delete:** {len(messages)} messages in {messages[0].channel.mention}")

# --- START ---
if __name__ == "__main__":
    if TOKEN:
        keep_alive()
        try:
            # Fixing setup hooks initialization alignment inside bot startup cycle
            bot.setup_hook = bot.self_setup_hook
            bot.run(TOKEN.strip())
        except Exception as e:
            print(f"❌ Error starting bot: {e}")
    else:
        print("❌ FATAL: TOKEN environment variable is missing.")
