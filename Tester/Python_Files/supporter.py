# Python_Files/supporter.py

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
import asyncpg
from datetime import datetime, timezone

# --- Basic Setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data_Files")
load_dotenv(os.path.join(DATA_DIR, ".env"))

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s]  %(message)s"
)
log = logging.getLogger(__name__)

# --- Import All Feature Managers ---
from date_and_time import DateTimeManager
from no_text import NoTextManager
from help import HelpManager
from owner_actions import OwnerActionsManager
from level import LevelManager
from youtube_notification import YouTubeManager

# --- Bot Configuration ---
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True


class SupporterBot(commands.Bot):
    """A custom bot class to hold our database connection and managers."""

    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.pool = None

    async def setup_hook(self):
        """This function is called once the bot is ready, before it connects to Discord."""
        log.info("Bot is setting up...")

        # 1. Connect to the PostgreSQL database
        try:
            self.pool = await asyncpg.create_pool(DATABASE_URL, max_size=20)
            log.info("✅ Successfully connected to the PostgreSQL database.")
        except Exception as e:
            log.critical(f"❌ CRITICAL: Could not connect to the database: {e}")
            await self.close()
            return

        # 2. Initialize and start all managers
        log.info("Initializing feature managers...")
        self.datetime_manager = DateTimeManager(self, self.pool)
        self.notext_manager = NoTextManager(self, self.pool)
        self.help_manager = HelpManager(self)
        self.owner_manager = OwnerActionsManager(self, self.pool)
        self.level_manager = LevelManager(self, self.pool)
        self.youtube_manager = YouTubeManager(self, self.pool)

        await self.datetime_manager.start()
        await self.notext_manager.start()
        await self.level_manager.start()
        await self.youtube_manager.start()

        # 3. Register slash commands from all managers
        self.datetime_manager.register_commands()
        self.notext_manager.register_commands()
        self.help_manager.register_commands()
        self.owner_manager.register_commands()
        self.level_manager.register_commands()
        self.youtube_manager.register_commands()

        log.info("All managers have been initialized.")


bot = SupporterBot()


@bot.event
async def on_ready():
    """Event that runs when the bot is fully connected and ready."""
    log.info("=" * 50)
    log.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

    try:
        synced = await bot.tree.sync()
        log.info(f"✅ Synced {len(synced)} slash commands globally.")
    except Exception as e:
        log.error(f"❌ Failed to sync slash commands: {e}")

    log.info(f"🚀 Bot is connected to {len(bot.guilds)} server(s):")
    for guild in bot.guilds:
        log.info(f"   - {guild.name} (ID: {guild.id})")
    log.info("=" * 50)
    log.info("✅ Bot is fully ready and operational!")


@bot.event
async def on_guild_join(guild: discord.Guild):
    log.info(f"🔥 Joined a new server: {guild.name} (ID: {guild.id})")
    if await bot.owner_manager.is_guild_banned(guild.id):
        log.warning(f"🚫 Bot joined banned server {guild.name}. Leaving immediately.")
        try:
            if guild.owner:
                await guild.owner.send(
                    "This bot is not permitted in this server and has been removed."
                )
        except discord.Forbidden:
            log.warning("Could not notify server owner about the ban.")
        finally:
            await guild.leave()


# --- GENERAL COMMANDS ---
@bot.tree.command(
    name="g2-show-config",
    description="Show the current bot configuration for this server.",
)
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def show_config(interaction: discord.Interaction):
    """Displays a comprehensive summary of all bot configurations for the server."""
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild.id)

    embed = discord.Embed(
        title=f"🤖 Bot Configuration for {interaction.guild.name}",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc),
    )

    async with bot.pool.acquire() as conn:
        # 1. Leveling System Config
        level_notify_ch_id = await conn.fetchval(
            "SELECT channel_id FROM public.level_notify_channel WHERE guild_id = $1",
            guild_id,
        )
        level_reset_days = await conn.fetchval(
            "SELECT days FROM public.auto_reset WHERE guild_id = $1", guild_id
        )
        level_rewards_count = await conn.fetchval(
            "SELECT COUNT(*) FROM public.level_roles WHERE guild_id = $1", guild_id
        )
        level_value = (
            f"**Notifications:** {f'<#{level_notify_ch_id}>' if level_notify_ch_id else 'Not Set'}\n"
            f"**Auto-Reset:** {f'Every {level_reset_days} days' if level_reset_days else 'Disabled'}\n"
            f"**Role Rewards:** {level_rewards_count} configured"
        )
        embed.add_field(name="📊 Leveling & XP", value=level_value, inline=False)

        # 2. YouTube Notifications Config
        yt_configs = await conn.fetch(
            "SELECT yt_channel_name, target_channel_id FROM public.youtube_notification_config WHERE guild_id = $1",
            guild_id,
        )
        if yt_configs:
            yt_value = "\n".join(
                [
                    f"• **{cfg['yt_channel_name']}** → <#{cfg['target_channel_id']}>"
                    for cfg in yt_configs
                ]
            )
        else:
            yt_value = "No YouTube channels are being monitored."
        embed.add_field(name="📢 YouTube Notifications", value=yt_value, inline=False)

        # 3. Channel Restrictions Config
        no_text_ch = await conn.fetch(
            "SELECT channel_id FROM public.no_text_channels WHERE guild_id = $1",
            guild_id,
        )
        no_discord_ch = await conn.fetch(
            "SELECT channel_id FROM public.no_discord_links_channels WHERE guild_id = $1",
            guild_id,
        )
        no_links_ch = await conn.fetch(
            "SELECT channel_id FROM public.no_links_channels WHERE guild_id = $1",
            guild_id,
        )
        bypass_roles_count = await conn.fetchval(
            "SELECT COUNT(*) FROM public.bypass_roles WHERE guild_id = $1", guild_id
        )

        restriction_value = ""
        if no_text_ch:
            restriction_value += f"**Media-Only:** {len(no_text_ch)} channel(s)\n"
        if no_discord_ch:
            restriction_value += (
                f"**No Discord Invites:** {len(no_discord_ch)} channel(s)\n"
            )
        if no_links_ch:
            restriction_value += f"**No Links (All):** {len(no_links_ch)} channel(s)\n"
        restriction_value += f"**Bypass Roles:** {bypass_roles_count} configured"
        embed.add_field(
            name="🚫 Channel Restrictions", value=restriction_value, inline=False
        )

        # 4. Time Channels Config
        time_cfg = await conn.fetchrow(
            "SELECT date_channel_id, india_channel_id, japan_channel_id FROM public.time_channel_config WHERE guild_id = $1",
            guild_id,
        )
        if time_cfg:
            time_value = (
                f"📅 <#{time_cfg['date_channel_id']}> | "
                f"🇮🇳 <#{time_cfg['india_channel_id']}> | "
                f"🇯🇵 <#{time_cfg['japan_channel_id']}>"
            )
            embed.add_field(name="⏰ Time Channels", value=time_value, inline=False)

    await interaction.followup.send(embed=embed)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: discord.app_commands.AppCommandError
):
    log.error(f"Slash command error for '/{interaction.command.name}': {error}")
    message = "❌ An unexpected error occurred. Please try again later."
    if isinstance(error, discord.app_commands.MissingPermissions):
        message = "🚫 You do not have the required permissions to run this command."
    elif isinstance(error, discord.app_commands.CheckFailure):
        message = "🚫 You are not allowed to use this command."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def run_bot():
    """Checks for necessary tokens and runs the bot."""
    if not TOKEN:
        log.critical("❌ Error: DISCORD_TOKEN not found in .env file!")
        return
    if not DATABASE_URL:
        log.critical("❌ Error: DATABASE_URL not found in .env file!")
        return
    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    run_bot()
