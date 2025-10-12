# supporter.py

from dotenv import load_dotenv
import discord
from discord.ext import commands
import os
from datetime import datetime, timezone
import logging

# Configure logging to reduce console spam
logging.basicConfig(level=logging.WARNING)

# Corrected import paths for all feature managers
from Python_Files.level import LevelManager
from Python_Files.date_and_time import DateTimeManager
from Python_Files.no_text import NoTextManager
from Python_Files.help import HelpManager
from Python_Files.youtube_notification import YouTubeManager
from Python_Files.owner_actions import (
    OwnerActionsManager,
)  # <--- IMPORT THE NEW MANAGER

# Get the base directory for data files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data_Files")
load_dotenv(os.path.join(DATA_DIR, ".env"))

# Bot configuration
TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Initialize all feature managers
datetime_manager = DateTimeManager(bot, DATA_DIR)
notext_manager = NoTextManager(bot, DATA_DIR)
level_manager = LevelManager(bot, DATA_DIR)
youtube_manager = YouTubeManager(bot)
help_manager = HelpManager(bot)
owner_manager = OwnerActionsManager(bot)  # <--- INITIALIZE THE NEW MANAGER


@bot.event
async def on_ready():
    # Start all feature managers
    await datetime_manager.start()
    await notext_manager.start()
    await level_manager.start()
    await youtube_manager.start()

    # Register all commands from manager files
    level_manager.register_commands()
    notext_manager.register_commands()
    youtube_manager.register_commands()
    help_manager.register_commands()
    owner_manager.register_commands()  # <--- REGISTER THE NEW COMMANDS

    # Sync slash commands globally
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands globally")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    # ========================= NEW CODE START =========================
    # Print the list of servers to the console
    print("-" * 30)
    print(f"Bot is connected to {len(bot.guilds)} server(s):")
    for guild in bot.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
    print("-" * 30)
    # ========================== NEW CODE END ==========================

    print("🚀 Bot is fully ready!")


# ========================= NEW CODE START =========================
@bot.event
async def on_guild_join(guild: discord.Guild):
    """Event that triggers when the bot joins a new server."""
    print(f"📥 Joined a new server: {guild.name} (ID: {guild.id})")

    # Check if the guild is on the ban list
    if await owner_manager.is_guild_banned(guild.id):
        print(
            f"🚫 Attempted to join a banned server: {guild.name}. Leaving immediately."
        )
        try:
            # Try to send a message to the owner if possible
            if guild.owner:
                await guild.owner.send(
                    "This bot is not permitted to be in this server and has been removed."
                )
        except discord.Forbidden:
            print("Could not notify the server owner about the ban.")
        finally:
            await guild.leave()


# ========================== NEW CODE END ==========================


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    await notext_manager.handle_message(message)
    await level_manager.handle_message(message)
    await bot.process_commands(message)


# ... (rest of your supporter.py file remains the same) ...
# The /setup-time-channels, /setup-no-text, /remove-no-text,
# /show-config, /serverlist, error handling, and run_bot functions
# are all still here.


# ===== SLASH COMMANDS DEFINED IN MAIN FILE =====
@bot.tree.command(
    name="setup-time-channels",
    description="Set up date, India time, and Japan time channels",
)
async def setup_time_channels(
    interaction: discord.Interaction,
    date_channel: discord.abc.GuildChannel,
    india_channel: discord.abc.GuildChannel,
    japan_channel: discord.abc.GuildChannel,
):
    await interaction.response.defer(ephemeral=True)
    await datetime_manager.setup_channels(
        interaction, date_channel, india_channel, japan_channel
    )


@bot.tree.command(
    name="setup-no-text",
    description="Set up a channel where only media/links are allowed",
)
async def setup_no_text(
    interaction: discord.Interaction,
    no_text_channel: discord.TextChannel,
    redirect_channel: discord.TextChannel,
):
    await interaction.response.defer(ephemeral=True)
    await notext_manager.setup_channel(interaction, no_text_channel, redirect_channel)


@bot.tree.command(
    name="remove-no-text", description="Remove no-text restriction from a channel"
)
async def remove_no_text(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    await interaction.response.defer(ephemeral=True)
    await notext_manager.remove_channel(interaction, channel)


@bot.tree.command(name="show-config", description="Show current bot configuration")
async def show_config(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    embed = discord.Embed(
        title="🤖 Bot Configuration",
        color=0x00FF00,
        timestamp=datetime.now(timezone.utc),
    )

    time_config = datetime_manager.get_config(guild_id)
    if time_config:
        embed.add_field(
            name="⏰ Time Channels",
            value=f"📅 Date: <#{time_config['date']}>\n🇮🇳 India: <#{time_config['india']}>\n🇯🇵 Japan: <#{time_config['japan']}>",
            inline=False,
        )
    else:
        embed.add_field(
            name="⏰ Time Channels", value="❌ Not configured", inline=False
        )

    notext_config = notext_manager.get_config(guild_id)
    if notext_config and notext_config["channels"]:
        notext_info = ""
        for ch_id in notext_config["channels"]:
            redirect_id = notext_config["redirects"].get(str(ch_id))
            notext_info += f"🚫📝 <#{ch_id}> → 💬 <#{redirect_id}>\n"
        embed.add_field(name="🚫📝 No-Text Channels", value=notext_info, inline=False)
    else:
        embed.add_field(
            name="🚫📝 No-Text Channels", value="❌ None configured", inline=False
        )

    embed.set_footer(text=f"Server ID: {interaction.guild_id}")
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(
    name="serverlist", description="Lists all servers the bot is in (Bot Owner only)."
)
async def serverlist(interaction: discord.Interaction):
    # This is a security check. It ensures only the person who created the bot
    # in the Discord Developer Portal can use this command.
    if not await bot.is_owner(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.", ephemeral=True
        )
        return

    # Defer the response to give the bot time to build the list, and make it private
    await interaction.response.defer(ephemeral=True)

    # Build a formatted string containing the server list
    server_list_details = []
    for guild in bot.guilds:
        server_list_details.append(f"- **{guild.name}** (ID: `{guild.id}`)")

    message_content = "\n".join(server_list_details)

    # Send the final list back to the owner
    await interaction.followup.send(
        f"🔎 I am currently in the following **{len(bot.guilds)}** server(s):\n{message_content}"
    )


# ===== ERROR HANDLING =====
@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: discord.app_commands.AppCommandError
):
    print(f"❌ Slash command error: {error}")
    message = "❌ An error occurred while processing your command."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


# ===== START BOT =====
def run_bot():
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in environment variables!")
        exit(1)
    print("🚀 Starting Supporter Bot...")
    bot.run(TOKEN)


if __name__ == "__main__":
    run_bot()
