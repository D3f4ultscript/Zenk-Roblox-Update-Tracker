import discord
from discord import app_commands
import aiohttp
import asyncio
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import logging
from keep_alive import keep_alive

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def vprint(message: str) -> None:
    print(f"{BOT_VERSION} {message}")

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHECK_INTERVAL = 300  # 5 minutes
BOT_VERSION = "#4"  # Version counter
GUILD_ID = os.getenv('GUILD_ID')
GUILD_ID = int(GUILD_ID) if GUILD_ID and GUILD_ID.isdigit() else None

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Store tracking data
tracking_data = {
    'channel_id': None,
    'last_entry_id': None
}

# File to persist tracking data
TRACKING_FILE = 'tracking_data.json'

# Load tracking data from file
def load_tracking_data():
    global tracking_data
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                tracking_data = json.load(f)
                logger.info(f"Loaded tracking data: {tracking_data}")
        except Exception as e:
            logger.error(f"Error loading tracking data: {e}")
            tracking_data = {'channel_id': None, 'last_entry_id': None}

    # Migrate old keys if needed
    if 'last_entry_id' not in tracking_data:
        tracking_data['last_entry_id'] = None
    if 'channel_id' not in tracking_data:
        tracking_data['channel_id'] = None
    tracking_data.pop('last_status', None)

# Save tracking data to file
def save_tracking_data():
    try:
        with open(TRACKING_FILE, 'w') as f:
            json.dump(tracking_data, f)
            logger.info(f"Saved tracking data: {tracking_data}")
    except Exception as e:
        logger.error(f"Error saving tracking data: {e}")

# Fetch latest Roblox update from RSS
async def fetch_latest_update():
    urls = [
        'https://devforum.roblox.com/c/updates.rss',
        'https://blog.roblox.com/feed/'
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (RobloxUpdateTracker)'
    }

    timeout = aiohttp.ClientTimeout(total=10)

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for url in urls:
                try:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            logger.warning(f"RSS HTTP {resp.status} for {url}")
                            continue

                        text = await resp.text()
                        latest = parse_rss_latest(text)
                        if latest:
                            logger.info(f"✅ Latest RSS update: {latest['title']}")
                            return latest
                except Exception as e:
                    logger.warning(f"RSS fetch failed for {url}: {e}")
                    continue

        vprint("❌ RSS Error: Could not fetch Roblox updates")
        return None
    except Exception as e:
        logger.error(f"Error fetching RSS: {e}")
        vprint(f"❌ Fetch error: {e}")
        return None


def parse_rss_latest(xml_text: str) -> dict | None:
    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)
        channel = root.find('channel')
        if channel is None:
            return None

        item = channel.find('item')
        if item is None:
            return None

        title = item.findtext('title', default='(No title)').strip()
        link = item.findtext('link', default='').strip()
        pub_date = item.findtext('pubDate', default='').strip()
        guid = item.findtext('guid', default=link).strip()

        if not guid:
            guid = link or title

        return {
            'id': guid,
            'title': title,
            'link': link,
            'published': pub_date
        }
    except Exception as e:
        logger.warning(f"RSS parse error: {e}")
        return None

# Create embed for status update
def create_update_embed(update: dict, is_test: bool = False) -> discord.Embed:
    title = "📰 Roblox Update"
    if is_test:
        title += " (Test)"

    embed = discord.Embed(
        title=title,
        description=update.get('title', '(No title)'),
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )

    link = update.get('link') or ""
    published = update.get('published') or ""

    if link:
        embed.add_field(name="Link", value=link, inline=False)
    if published:
        embed.add_field(name="Published", value=published, inline=True)

    if is_test:
        embed.add_field(name="Test Message", value="✅ This is a test notification", inline=False)

    embed.set_footer(text="Roblox Update Tracker")
    return embed

@client.event
async def on_ready():
    logger.info(f'Bot Version {BOT_VERSION} - {client.user} has connected to Discord!')
    vprint('═══════════════════════════════════════')
    vprint(f'Bot Version: {BOT_VERSION}')
    vprint(f'Connected as: {client.user}')
    vprint(f'Bot ID: {client.user.id}')
    vprint('═══════════════════════════════════════')
    
    # Load saved tracking data
    load_tracking_data()
    
    # Sync slash commands
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} command(s) to guild {GUILD_ID}")
            vprint(f'✅ Synced {len(synced)} slash command(s) to guild {GUILD_ID}')
        else:
            synced = await tree.sync()
            logger.info(f"Synced {len(synced)} command(s) globally")
            vprint(f'✅ Synced {len(synced)} slash command(s) globally')

        command_names = [cmd.name for cmd in tree.get_commands()]
        vprint(f"Commands registered: {', '.join(command_names)}")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
        vprint(f'❌ Failed to sync commands: {e}')
    
    # Start background task
    client.loop.create_task(check_roblox_status())
    vprint('🔄 Background status checker started')
    vprint('═══════════════════════════════════════')


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Admin-Rechte erforderlich, um diesen Command zu nutzen.",
            ephemeral=True
        )
        return

    logger.error(f"App command error: {error}")
    try:
        await interaction.response.send_message(
            "❌ Es gab einen Fehler beim Ausfuehren des Commands.",
            ephemeral=True
        )
    except Exception:
        pass

@tree.command(name='version', description='Show bot version (Admin only)')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def version(interaction: discord.Interaction):
    """Show current bot version - Admin only"""
    try:
        embed = discord.Embed(
            title="🤖 Bot Version",
            description=f"Current Version: **{BOT_VERSION}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Bot Name", value=client.user.name, inline=True)
        embed.add_field(name="Bot ID", value=client.user.id, inline=True)
        embed.add_field(name="Check Interval", value=f"{CHECK_INTERVAL // 60} minutes", inline=True)
        embed.set_footer(text="Roblox Status Tracker")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Version command used by {interaction.user}")
    except Exception as e:
        logger.error(f"Error in version command: {e}")
        try:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        except:
            pass

@tree.command(name='rbxupdate', description='Set this channel for Roblox update notifications (Admin only)')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def rbxupdate(interaction: discord.Interaction):
    """Slash command to set the tracking channel and send a test message - Admin only"""
    try:
        # Set channel
        tracking_data['channel_id'] = interaction.channel.id
        save_tracking_data()
        
        # Fetch latest update
        latest_update = await fetch_latest_update()

        if latest_update:
            # Update last entry
            tracking_data['last_entry_id'] = latest_update['id']
            save_tracking_data()

            # Send test message
            embed = create_update_embed(latest_update, is_test=True)
            await interaction.response.send_message(embed=embed)

            # Confirmation
            await interaction.followup.send(
                f"✅ Channel set to {interaction.channel.mention} for Roblox updates!\n"
                f"🔄 Checking every 5 minutes for new posts.",
                ephemeral=True
            )

            logger.info(f"Channel set to {interaction.channel.id} by {interaction.user}")
        else:
            await interaction.response.send_message(
                "❌ Could not fetch Roblox updates. Please try again later.",
                ephemeral=True
            )
    except Exception as e:
        logger.error(f"Error in rbxupdate command: {e}")
        try:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        except:
            pass

async def check_roblox_status():
    """Background task to check Roblox updates every 5 minutes"""
    await client.wait_until_ready()
    logger.info(f"Background status checker started (Version {BOT_VERSION})")
    vprint(f"🔄 Status checker active - checking every {CHECK_INTERVAL // 60} minutes")
    
    while not client.is_closed():
        try:
            # Only check if we have a channel set
            if tracking_data['channel_id']:
                channel = client.get_channel(tracking_data['channel_id'])
                
                if channel:
                    # Fetch latest update
                    latest_update = await fetch_latest_update()

                    if latest_update:
                        latest_id = latest_update['id']

                        # Check if update changed
                        if tracking_data['last_entry_id'] != latest_id:
                            logger.info(
                                f"🔔 New update: '{tracking_data['last_entry_id']}' -> '{latest_id}'"
                            )
                            vprint("🔔 NEW UPDATE DETECTED!")
                            vprint(f"Title: {latest_update.get('title', '')}")

                            # Send update
                            embed = create_update_embed(latest_update, is_test=False)
                            await channel.send(embed=embed)

                            # Update stored entry
                            tracking_data['last_entry_id'] = latest_id
                            save_tracking_data()
                        else:
                            logger.debug("No new updates")
                else:
                    logger.warning(f"Channel {tracking_data['channel_id']} not found")
            else:
                logger.debug("No channel set for tracking")
        
        except Exception as e:
            logger.error(f"Error in status check loop: {e}")
            vprint(f"❌ Status check error: {e}")
        
        # Wait 5 minutes before next check
        await asyncio.sleep(CHECK_INTERVAL)

# Run the bot
if __name__ == "__main__":
    try:
        vprint('═══════════════════════════════════════')
        vprint('Starting Roblox Status Tracker')
        vprint(f'Version: {BOT_VERSION}')
        vprint('═══════════════════════════════════════')
        
        # Check if token exists
        if not TOKEN:
            vprint("❌ ERROR: DISCORD_TOKEN not found in environment!")
            vprint("Please set DISCORD_TOKEN in Replit Secrets")
            exit(1)
        
        # Start Flask webserver for Replit
        keep_alive()
        vprint("✅ Webserver started on port 8080")
        
        logger.info(f"Starting bot version {BOT_VERSION}...")
        client.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
        vprint("⚠️ Bot shutdown by user")
    except discord.LoginFailure:
        logger.error("Invalid Discord token!")
        vprint("❌ ERROR: Invalid Discord token!")
        vprint("Please check your DISCORD_TOKEN in Replit Secrets")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        vprint(f"❌ ERROR: Bot crashed - {e}")
        import traceback
        traceback.print_exc()
