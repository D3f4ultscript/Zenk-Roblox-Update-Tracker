import discord
from discord.ext import commands, tasks
import aiohttp
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = os.getenv('CLIENT_ID')

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

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
        async with aiohttp.ClientSession() as session:
            async with session.get('https://status.roblox.com/api/v2/components.json') as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Find Windows Desktop Client component
                    for component in data['components']:
                        if 'Windows' in component['name'] and 'Desktop' in component['name']:
                            version = component.get('description', 'Unknown')
                            status = component.get('status', 'unknown')
                            return {
                                'version': version,
                                'status': status,
                                'component_name': component['name']
                            }
                    
                    return None
    except Exception as e:
        print(f"Error fetching Roblox status: {e}")
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
    print(f'{bot.user} has connected to Discord!')
    load_tracking_data()
    # Start the background task
    check_roblox_updates.start()

@bot.command(name='rbxupdate', description='Set the channel for Roblox update notifications')
async def rbxupdate(ctx):
    """Command to set the tracking channel and send a test message"""
    tracking_data['channel_id'] = ctx.channel.id
    save_tracking_data()
    
    # Fetch current Roblox status for test message
    roblox_info = await fetch_roblox_status()
    
    if roblox_info:
        embed = create_update_embed(roblox_info['version'], roblox_info['component_name'])
        embed.add_field(name="Test Message", value="✅ This is a test notification", inline=False)
        await ctx.send(embed=embed)
        await ctx.send(f"✅ Channel set to {ctx.channel.mention} for Roblox updates!")
    else:
        await ctx.send("❌ Could not fetch Roblox status. Please try again later.")

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

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)
