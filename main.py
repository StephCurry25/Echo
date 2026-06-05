import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import threading
import logging
import json
from flask import Flask

# --- SECTION 1: HARDCODED PORT 8080 WEB SERVER ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EchoBot')

app = Flask(__name__)

@app.route('/')
def health_check(): 
    return "EchoBot Matrix: Active on Port 8080"

def start_web_server():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

# --- SECTION 2: STORAGE AND DATA PERSISTENCE ---
CONFIG_FILE = "config.json"

def load_system_config():
    if not os.path.exists(CONFIG_FILE):
        default = {
            "automod": False, 
            "autorole_id": None, 
            "log_channel_id": None,
            "blocked_words": ["scam", "freemoney", "phishing"]
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=4)
        return default
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_system_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_system_config()

# --- SECTION 3: AUDIT LOG DISTRIBUTION ---
async def send_audit_log(guild: discord.Guild, title: str, description: str, color: discord.Color):
    if config["log_channel_id"]:
        log_channel = guild.get_channel(config["log_channel_id"])
        if log_channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
            try:
                await log_channel.send(embed=embed)
            except:
                pass

# --- SECTION 4: INTERACTIVE UI DASHBOARD ---
class ServerManagementDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Toggle AutoMod", style=discord.ButtonStyle.danger, custom_id="tg_am")
    async def toggle_automod_action(self, interaction: discord.Interaction, button: ui.Button):
        config["automod"] = not config["automod"]
        save_system_config(config)
        status = "ENABLED" if config["automod"] else "DISABLED"
        await interaction.response.send_message(f"AutoMod protection is now **{status}**.", ephemeral=True)

    @ui.select(cls=ui.RoleSelect, placeholder="Select Autorole", custom_id="sel_ar")
    async def select_autorole_action(self, interaction: discord.Interaction, select: ui.RoleSelect):
        config["autorole_id"] = select.values[0].id
        save_system_config(config)
        await interaction.response.send_message(f"Autorole saved: **{select.values[0].name}**.", ephemeral=True)

    @ui.select(cls=ui.ChannelSelect, placeholder="Select Audit Log Channel", channel_types=[discord.ChannelType.text], custom_id="sel_log")
    async def select_log_channel_action(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        config["log_channel_id"] = select.values[0].id
        save_system_config(config)
        await interaction.response.send_message(f"Audit logs routed to: **{select.values[0].mention}**.", ephemeral=True)

# --- SECTION 5: INITIALIZATION SETUP ---
class EchoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        self.add_view(ServerManagementDashboard())
        try:
            await self.tree.sync()
            logger.info("Application gateway synchronized cleanly.")
        except Exception as e:
            logger.error(f"Command sync warning: {e}")

bot = EchoBot()

# --- AUTOMATED GLOBAL ERROR CATCHER ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            f"❌ **Permission Denied:** You need `Administrator` permissions to run this command.", 
            ephemeral=True
        )
    else:
        logger.error(f"Execution failure: {error}")
        try:
            await interaction.response.send_message(f"❌ **Internal System Error:** `{error}`", ephemeral=True)
        except:
            pass

# --- SECTION 6: FAILSAFE MODERATION SYSTEMS ---
@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def command_kick(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message("❌ Target has an equal or higher role than you.", ephemeral=True)
    if member.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ Move my bot role above the target's role in server settings.", ephemeral=True)
    
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 **{member.name}** has been kicked.")
        await send_audit_log(interaction.guild, "Kick Executed", f"Target: {member.mention}\nMod: {interaction.user.mention}", discord.Color.orange())
    except:
        await interaction.response.send_message("❌ Permission Execution Error.", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def command_ban(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message("❌ Target has an equal or higher role than you.", ephemeral=True)
    if member.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ Move my bot role above the target's role in server settings.", ephemeral=True)

    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 **{member.name}** has been banned.")
        await send_audit_log(interaction.guild, "Ban Executed", f"Target: {member.mention}\nMod: {interaction.user.mention}", discord.Color.red())
    except:
        await interaction.response.send_message("❌ Permission Execution Error.", ephemeral=True)

@bot.tree.command(name="unban", description="Unban a member by ID string")
@app_commands.checks.has_permissions(ban_members=True)
async def command_unban(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"🔓 **{user.name}** has been unbanned.")
        await send_audit_log(interaction.guild, "Unban Executed", f"Target: {user.name}\nMod: {interaction.user.mention}", discord.Color.green())
    except:
        await interaction.response.send_message("❌ User not found or not banned.", ephemeral=True)

@bot.tree.command(name="mute", description="Apply the Muted server role")
@app_commands.checks.has_permissions(manage_roles=True)
async def command_mute(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    if member.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ My role level is below the target.", ephemeral=True)

    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not role:
        try:
            role = await interaction.guild.create_role(name="Muted")
            for channel in interaction.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False)
        except:
            return await interaction.response.send_message("❌ Cannot generate a Muted role.", ephemeral=True)
    
    try:
        await member.add_roles(role, reason=reason)
        await interaction.response.send_message(f"🤐 **{member.name}** has been muted.")
        await send_audit_log(interaction.guild, "Mute Executed", f"Target: {member.mention}\nMod: {interaction.user.mention}", discord.Color.dark_grey())
    except:
        await interaction.response.send_message("❌ Role adjustment blocked.", ephemeral=True)

@bot.tree.command(name="unmute", description="Remove the Muted server role")
@app_commands.checks.has_permissions(manage_roles=True)
async def command_unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if role and role in member.roles:
        try:
            await member.remove_roles(role)
            await interaction.response.send_message(f"🔊 **{member.name}** has been unmuted.")
            await send_audit_log(interaction.guild, "Unmute Executed", f"Target: {member.mention}\nMod: {interaction.user.mention}", discord.Color.light_grey())
        except:
            await interaction.response.send_message("❌ Role adjustment blocked.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Target is not currently muted.", ephemeral=True)

@bot.tree.command(name="clear", description="Bulk delete text messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def command_clear(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        return await interaction.response.send_message("❌ Quantify between 1 and 100.", ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"🧹 Cleared **{len(deleted)}** messages.", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Channel permissions missing.", ephemeral=True)

# --- SECTION 7: UI EMBEDDED MODAL & AUTOMOD ENGINE ---
class BlacklistAddModal(ui.Modal, title="Add Blacklist Words (Max 4k Chars)"):
    words_input = ui.TextInput(
        label="Enter terms (Separated by commas OR new lines)",
        style=discord.TextStyle.paragraph,
        placeholder="scam\nfree nitro\nfakebot, malware",
        required=True,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Instantly defer to completely eliminate 3-second timeout limits
        await interaction.response.defer(ephemeral=True)
        
        raw_text = self.words_input.value
        normalized_text = raw_text.replace("\n", ",")
        input_list = [w.strip().lower() for w in normalized_text.split(",") if w.strip()]
        
        added_words = []
        skipped_words = []
        
        for word in input_list:
            if word in config["blocked_words"]:
                skipped_words.append(word)
            else:
                config["blocked_words"].append(word)
                added_words.append(word)
                
        if added_words:
            save_system_config(config)
            
        msg = ""
        if added_words:
            msg += f"✅ **Added to filters:** {', '.join(f'`{w}`' for w in added_words[:30])}"
            if len(added_words) > 30:
                msg += f" ...and {len(added_words) - 30} more words."
            msg += "\n"
        if skipped_words:
            msg += f"⚠️ **Skipped (Already existed):** {', '.join(f'`{w}`' for w in skipped_words[:15])}"
            if len(skipped_words) > 15:
                msg += f" ...and {len(skipped_words) - 15} more duplicates."
        if not msg:
            msg = "❌ No valid terms processed."
            
        await interaction.followup.send(content=msg)

blacklist_group = app_commands.Group(name="blacklist", description="Filter word matrix management")

@blacklist_group.command(name="add", description="Open the secure UI input box to paste blocklists")
@app_commands.checks.has_permissions(administrator=True)
async def blacklist_add(interaction: discord.Interaction):
    # Triggers the embedded pop-up window interface directly
    await interaction.response.send_modal(BlacklistAddModal())

@blacklist_group.command(name="remove", description="Remove word from filters")
@app_commands.checks.has_permissions(administrator=True)
async def blacklist_remove(interaction: discord.Interaction, word: str):
    word = word.lower()
    if word not in config["blocked_words"]:
        return await interaction.response.send_message("❌ Token not found.", ephemeral=True)
    config["blocked_words"].remove(word)
    save_system_config(config)
    await interaction.response.send_message(f"✅ Removed **{word}** from filters.", ephemeral=True)

@blacklist_group.command(name="show", description="Display word filters")
@app_commands.checks.has_permissions(administrator=True)
async def blacklist_show(interaction: discord.Interaction):
    words = ", ".join(config["blocked_words"]) if config["blocked_words"] else "Empty Matrix."
    await interaction.response.send_message(f"🛡️ **Current Filter Blacklist:**\n`{words}`", ephemeral=True)

bot.tree.add_command(blacklist_group)

# --- SECTION 8: ADMINISTRATION ROUTINES ---
@bot.tree.command(name="dashboard", description="Open settings menu")
@app_commands.checks.has_permissions(administrator=True)
async def command_dashboard(interaction: discord.Interaction):
    await interaction.response.send_message("⚙️ **System Configuration Hub**", view=ServerManagementDashboard(), ephemeral=True)

@bot.tree.command(name="announce", description="Global deployment broadcast")
async def command_announce(interaction: discord.Interaction, message: str):
    if interaction.user.id != 1219266886143967245:
        return await interaction.response.send_message("❌ Unauthorized signature.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    count = 0
    for guild in bot.guilds:
        target = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if target:
            try:
                embed = discord.Embed(title="📢 Network Notification", description=message, color=discord.Color.gold())
                await target.send(embed=embed)
                count += 1
            except:
                pass
    await interaction.followup.send(f"✅ Delivery complete to **{count}** node servers.")

@bot.tree.command(name="cmds", description="Command guide reference")
async def command_cmds(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 System Directory", color=discord.Color.purple())
    embed.add_field(name="🛡️ Moderation Engine", value="`/kick`, `/ban`, `/unban`, `/mute`, `/unmute`, `/clear`")
    embed.add_field(name="🤖 Filtering", value="`/blacklist add`, `/blacklist remove`, `/blacklist show`")
    embed.add_field(name="⚙️ Admin Architecture", value="`/dashboard`, `/announce`")
    await interaction.response.send_message(embed=embed)

# --- SECTION 9: ENGINE AUTOMATION LOOP ---
@bot.event
async def on_member_join(member):
    if config["autorole_id"]:
        role = member.guild.get_role(config["autorole_id"])
        if role:
            try:
                await member.add_roles(role)
            except:
                pass
    await send_audit_log(member.guild, "📥 Member Joined", f"{member.mention} entered.", discord.Color.green())

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if config["automod"]:
        content_lower = message.content.lower()
        if any(bad_word in content_lower for bad_word in config["blocked_words"]):
            try:
                await message.delete()
                return
            except:
                pass

    await bot.process_commands(message)

# --- SECTION 10: ENTRY SYSTEM RUNNER ---
if __name__ == "__main__":
    threading.Thread(target=start_web_server, daemon=True).start()
    bot_token = os.environ.get("TOKEN")
    if not bot_token:
        exit(1)
    try:
        bot.run(bot_token.strip())
    except:
        exit(1)
