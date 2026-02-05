import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from aiohttp import web
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = os.getenv('CLIENT_ID')
PORT = int(os.getenv('PORT', 5000))

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents, sync_commands_on_load=True)

# Sync app commands with Discord
async def sync_commands():
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s) with Discord")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

# Store tracking data
tracking_data = {
    'channel_id': None,
    'last_version': None
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
        except:
            tracking_data = {'channel_id': None, 'last_version': None}

# Save tracking data to file
def save_tracking_data():
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f)

# Fetch Roblox status and version
async def fetch_roblox_status():
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Try multiple API endpoints
            urls = [
                'https://clientsettingscdn.roblox.com/v2/client-version/WindowsPlayer',
                'https://setup.rbxcdn.com/DeployHistory.txt',
                'https://setup.roblox.com/DeployHistory.txt',
                'https://setup.roblox.com/version.txt'
            ]
            
            for url in urls:
                try:
                    headers = {
                        'User-Agent': 'Roblox/WinInet'
                    }
                    
                    async with session.get(url, headers=headers) as response:
                        logger.info(f"Trying {url} - Status: {response.status}")
                        
                        if response.status == 200:
                            content_type = response.headers.get('Content-Type', '')
                            
                            # Handle JSON response (clientsettingscdn)
                            if 'json' in content_type:
                                data = await response.json()
                                version = data.get('version') or data.get('clientVersionUpload')
                                
                                if version:
                                    logger.info(f"Found Roblox version: {version}")
                                    return {
                                        'version': version,
                                        'status': 'operational',
                                        'component_name': 'Windows Desktop Client'
                                    }
                            
                            # Handle text response (DeployHistory)
                            else:
                                text = await response.text()
                                lines = text.strip().split('\n')
                                
                                if lines:
                                    # First line is the latest version
                                    latest_line = lines[0].strip()
                                    logger.info(f"Response content: {latest_line}")
                                    
                                    # Check if it's just a version string
                                    if latest_line.startswith('version-'):
                                        version = latest_line
                                        logger.info(f"Found Roblox version: {version}")
                                        
                                        return {
                                            'version': version,
                                            'status': 'operational',
                                            'component_name': 'Windows Desktop Client'
                                        }
                                    
                                    # Extract version from deploy history format
                                    elif 'version-' in latest_line:
                                        # Split by space and find the version part
                                        parts = latest_line.split()
                                        for part in parts:
                                            if part.startswith('version-'):
                                                version = part
                                                
                                                logger.info(f"Found Roblox version: {version}")
                                                
                                                return {
                                                    'version': version,
                                                    'status': 'operational',
                                                    'component_name': 'Windows Desktop Client'
                                                }
                except Exception as e:
                    logger.warning(f"Failed to fetch from {url}: {e}")
                    continue
            
            logger.error("All API endpoints failed")
            return None
                
    except Exception as e:
        logger.error(f"Error fetching Roblox status: {e}")
        return None

# Create embed for update notification
def create_update_embed(version, component_name):
    embed = discord.Embed(
        title="🎮 Roblox Windows Update Detected!",
        description=f"A new update has been released for {component_name}",
        color=discord.Color.from_rgb(0, 162, 232),
        timestamp=datetime.now()
    )
    embed.add_field(name="Version", value=f"`{version}`", inline=False)
    embed.add_field(name="Status", value="✅ Live", inline=False)
    embed.add_field(name="Platform", value="Windows Desktop Client", inline=False)
    embed.set_footer(text="Roblox Update Tracker")
    return embed

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    print(f'{bot.user} has connected to Discord!')
    load_tracking_data()
    # Sync slash commands with Discord
    await sync_commands()
    # Start the background task
    check_roblox_updates.start()

@bot.tree.command(name='rbxupdate', description='Set the channel for Roblox update notifications and get test message')
async def rbxupdate(interaction: discord.Interaction):
    """Slash command to set the tracking channel and send a test message"""
    try:
        tracking_data['channel_id'] = interaction.channel.id
        save_tracking_data()
        
        # Fetch current Roblox status for test message
        roblox_info = await fetch_roblox_status()
        
        if roblox_info:
            embed = create_update_embed(roblox_info['version'], roblox_info['component_name'])
            embed.add_field(name="Test Message", value="✅ This is a test notification", inline=False)
            await interaction.response.send_message(embed=embed)
            # Send confirmation
            await interaction.followup.send(f"✅ Channel set to {interaction.channel.mention} for Roblox updates!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Could not fetch Roblox status. Please try again later.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in rbxupdate command: {e}")
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@tasks.loop(minutes=5)
async def check_roblox_updates():
    """Background task to check for Roblox updates every 5 minutes"""
    if tracking_data['channel_id'] is None:
        return
    
    try:
        channel = bot.get_channel(tracking_data['channel_id'])
        if channel is None:
            return
        
        roblox_info = await fetch_roblox_status()
        if roblox_info is None:
            return
        
        current_version = roblox_info['version']
        
        # Check if version has changed
        if tracking_data['last_version'] is None:
            tracking_data['last_version'] = current_version
            save_tracking_data()
        elif tracking_data['last_version'] != current_version:
            # New version detected!
            embed = create_update_embed(current_version, roblox_info['component_name'])
            await channel.send(embed=embed)
            
            # Update stored version
            tracking_data['last_version'] = current_version
            save_tracking_data()
            
            print(f"Update detected: {tracking_data['last_version']} -> {current_version}")
    
    except Exception as e:
        print(f"Error in background update check: {e}")

@check_roblox_updates.before_loop
async def before_check_updates():
    """Wait until bot is ready before starting background task"""
    await bot.wait_until_ready()

# HTTP Server for Render
async def health_check(request):
    return web.Response(text='Bot is running!')

async def start_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f'HTTP Server started on port {PORT}')

async def main():
    try:
        # Start the HTTP server
        await start_server()
        logger.info('Starting Discord bot...')
        # Start the Discord bot
        async with bot:
            await bot.start(TOKEN)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

# Run the bot
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
