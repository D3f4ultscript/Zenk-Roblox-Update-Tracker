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

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHECK_INTERVAL = 300  # 5 minutes

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Store tracking data
tracking_data = {
    'channel_id': None,
    'last_status': None
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
            tracking_data = {'channel_id': None, 'last_status': None}

# Save tracking data to file
def save_tracking_data():
    try:
        with open(TRACKING_FILE, 'w') as f:
            json.dump(tracking_data, f)
            logger.info(f"Saved tracking data: {tracking_data}")
    except Exception as e:
        logger.error(f"Error saving tracking data: {e}")

# Fetch Roblox status
async def fetch_roblox_status():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://status.roblox.com/data/status.json') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status_info = data.get('status', {})
                    description = status_info.get('description', 'Unknown')
                    indicator = status_info.get('indicator', 'unknown')
                    
                    logger.info(f"Fetched Roblox status: {description}")
                    
                    return {
                        'description': description,
                        'indicator': indicator
                    }
                else:
                    logger.error(f"Failed to fetch status: HTTP {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching Roblox status: {e}")
        return None

# Create embed for status update
def create_status_embed(status_description, indicator, is_test=False):
    # Choose color based on indicator
    color_map = {
        'none': discord.Color.green(),
        'minor': discord.Color.gold(),
        'major': discord.Color.orange(),
        'critical': discord.Color.red()
    }
    color = color_map.get(indicator, discord.Color.blue())
    
    # Choose emoji based on indicator
    emoji_map = {
        'none': '✅',
        'minor': '⚠️',
        'major': '🔴',
        'critical': '🚨'
    }
    emoji = emoji_map.get(indicator, '🎮')
    
    title = f"{emoji} Roblox Status Update"
    if is_test:
        title += " (Test)"
    
    embed = discord.Embed(
        title=title,
        description=status_description,
        color=color,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Status Indicator", value=f"`{indicator}`", inline=True)
    embed.add_field(name="Source", value="[Roblox Status](https://status.roblox.com)", inline=True)
    
    if is_test:
        embed.add_field(name="Test Message", value="✅ This is a test notification", inline=False)
    
    embed.set_footer(text="Roblox Update Tracker")
    
    return embed

@client.event
async def on_ready():
    logger.info(f'{client.user} has connected to Discord!')
    print(f'{client.user} has connected to Discord!')
    
    # Load saved tracking data
    load_tracking_data()
    
    # Sync slash commands
    try:
        synced = await tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    # Start background task
    client.loop.create_task(check_roblox_status())

@tree.command(name='rbxupdate', description='Set this channel for Roblox status notifications')
async def rbxupdate(interaction: discord.Interaction):
    """Slash command to set the tracking channel and send a test message"""
    try:
        # Set channel
        tracking_data['channel_id'] = interaction.channel.id
        save_tracking_data()
        
        # Fetch current status
        status_info = await fetch_roblox_status()
        
        if status_info:
            # Update last status
            tracking_data['last_status'] = status_info['description']
            save_tracking_data()
            
            # Send test message
            embed = create_status_embed(
                status_info['description'],
                status_info['indicator'],
                is_test=True
            )
            await interaction.response.send_message(embed=embed)
            
            # Confirmation
            await interaction.followup.send(
                f"✅ Channel set to {interaction.channel.mention} for Roblox status updates!\n"
                f"🔄 Checking every 5 minutes for status changes.",
                ephemeral=True
            )
            
            logger.info(f"Channel set to {interaction.channel.id} by {interaction.user}")
        else:
            await interaction.response.send_message(
                "❌ Could not fetch Roblox status. Please try again later.",
                ephemeral=True
            )
    except Exception as e:
        logger.error(f"Error in rbxupdate command: {e}")
        try:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        except:
            pass

async def check_roblox_status():
    """Background task to check Roblox status every 5 minutes"""
    await client.wait_until_ready()
    logger.info("Started background status checker")
    
    while not client.is_closed():
        try:
            # Only check if we have a channel set
            if tracking_data['channel_id']:
                channel = client.get_channel(tracking_data['channel_id'])
                
                if channel:
                    # Fetch current status
                    status_info = await fetch_roblox_status()
                    
                    if status_info:
                        current_status = status_info['description']
                        
                        # Check if status changed
                        if tracking_data['last_status'] != current_status:
                            logger.info(f"Status changed: '{tracking_data['last_status']}' -> '{current_status}'")
                            
                            # Send update
                            embed = create_status_embed(
                                current_status,
                                status_info['indicator'],
                                is_test=False
                            )
                            await channel.send(embed=embed)
                            
                            # Update stored status
                            tracking_data['last_status'] = current_status
                            save_tracking_data()
                        else:
                            logger.info(f"Status unchanged: {current_status}")
                else:
                    logger.warning(f"Channel {tracking_data['channel_id']} not found")
            else:
                logger.info("No channel set for tracking")
        
        except Exception as e:
            logger.error(f"Error in status check loop: {e}")
        
        # Wait 5 minutes before next check
        await asyncio.sleep(CHECK_INTERVAL)

# Run the bot
if __name__ == "__main__":
    try:
        # Start Flask webserver for Replit
        keep_alive()
        
        logger.info("Starting bot...")
        client.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
