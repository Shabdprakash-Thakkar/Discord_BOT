# Python_Files/date_and_time.py
# This version aligns the time updates to clean 10-minute intervals.

import discord
from discord.ext import tasks, commands
import pytz
from datetime import datetime, timedelta
import asyncpg
import logging
import asyncio

log = logging.getLogger(__name__)


class DateTimeManager:
    def __init__(self, bot: commands.Bot, pool: asyncpg.Pool):
        self.bot = bot
        self.pool = pool  # The database connection pool from supporter.py
        self.server_configs = {}  # In-memory cache for channel IDs
        log.info("Date and Time system has been initialized.")

    async def _load_configs_from_db(self):
        """Load all server time configurations from the database into the cache."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM public.time_channel_config;")
            for row in rows:
                self.server_configs[int(row["guild_id"])] = {
                    "date": int(row["date_channel_id"]),
                    "india": int(row["india_channel_id"]),
                    "japan": int(row["japan_channel_id"]),
                }
        log.info(
            f"Loaded {len(self.server_configs)} time configurations from the database."
        )

    async def start(self):
        """Loads initial data and starts the background tasks for this manager."""
        await self._load_configs_from_db()
        self.update_time_channels.start()
        self.update_date_daily.start()

    # -------------------- Date Management --------------------

    async def update_date_channel(self):
        """Update date channels for all configured servers."""
        tz_india = pytz.timezone("Asia/Kolkata")
        date_str = datetime.now(tz_india).strftime("%d %B, %Y")
        new_name = f"📅 {date_str}"

        for guild_id, config in self.server_configs.items():
            try:
                channel = self.bot.get_channel(config["date"])
                if channel and channel.name != new_name:
                    await channel.edit(name=new_name)
            except discord.Forbidden:
                log.warning(
                    f"Missing permissions to edit date channel in guild {guild_id}."
                )
            except Exception as e:
                log.error(f"Error updating date channel for guild {guild_id}: {e}")

    @tasks.loop(hours=24)
    async def update_date_daily(self):
        """Daily task to update date channels."""
        await self.update_date_channel()

    # -------------------- Time Management --------------------

    @tasks.loop(minutes=10)
    async def update_time_channels(self):
        """Update time channels every 10 minutes."""
        log.info("Updating time channels...")
        tz_india = pytz.timezone("Asia/Kolkata")
        tz_japan = pytz.timezone("Asia/Tokyo")
        india_time = datetime.now(tz_india).strftime("%H:%M")
        japan_time = datetime.now(tz_japan).strftime("%H:%M")

        india_name = f"🇮🇳 IST {india_time}"
        japan_name = f"🇯🇵 JST {japan_time}"

        for guild_id, config in self.server_configs.items():
            try:
                # Update India Channel
                india_channel = self.bot.get_channel(config["india"])
                if india_channel and india_channel.name != india_name:
                    await india_channel.edit(name=india_name)

                # Update Japan Channel
                japan_channel = self.bot.get_channel(config["japan"])
                if japan_channel and japan_channel.name != japan_name:
                    await japan_channel.edit(name=japan_name)

            except discord.Forbidden:
                log.warning(
                    f"Missing permissions to edit time channels in guild {guild_id}."
                )
            except Exception as e:
                log.error(f"Error updating time channels for guild {guild_id}: {e}")

    # -------------------- Before Loop Logic (NEW & MODIFIED) --------------------

    @update_date_daily.before_loop
    async def before_update_date_daily(self):
        """Wait for the bot to be fully ready before starting the daily loop."""
        await self.bot.wait_until_ready()

    @update_time_channels.before_loop
    async def before_update_time_channels(self):
        """
        Wait for the bot to be ready and then align the loop to the next
        clean 10-minute mark (e.g., :10, :20, :30).
        """
        await self.bot.wait_until_ready()

        # Calculate the delay
        now = datetime.now()
        minutes_to_wait = 10 - (now.minute % 10)
        seconds_to_wait = (minutes_to_wait * 60) - now.second

        target_time = now + timedelta(seconds=seconds_to_wait)
        log.info(
            f"Aligning time channel updates. Waiting {seconds_to_wait} seconds for the first run at {target_time.strftime('%H:%M:%S')}."
        )

        # Wait for the calculated delay
        await asyncio.sleep(seconds_to_wait)
        log.info("Time channel alignment complete. Starting loop.")

    # -------------------- Slash Command Registration --------------------

    def register_commands(self):
        """Registers all slash commands for this manager."""

        @self.bot.tree.command(
            name="t1-setup-time-channels",
            description="Set up date, India time, and Japan time channels.",
        )
        @discord.app_commands.checks.has_permissions(manage_channels=True)
        @discord.app_commands.describe(
            date_channel="The voice channel to display the current date.",
            india_channel="The voice channel to display the time in India (IST).",
            japan_channel="The voice channel to display the time in Japan (JST).",
        )
        async def setup_time_channels(
            interaction: discord.Interaction,
            date_channel: discord.VoiceChannel,
            india_channel: discord.VoiceChannel,
            japan_channel: discord.VoiceChannel,
        ):
            """Saves the time channel configuration to the database."""
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild_id

            query = """
                INSERT INTO public.time_channel_config (guild_id, guild_name, date_channel_id, india_channel_id, japan_channel_id, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (guild_id) DO UPDATE SET
                  guild_name = EXCLUDED.guild_name,
                  date_channel_id = EXCLUDED.date_channel_id,
                  india_channel_id = EXCLUDED.india_channel_id,
                  japan_channel_id = EXCLUDED.japan_channel_id,
                  updated_at = NOW();
            """
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    str(guild_id),
                    interaction.guild.name,
                    str(date_channel.id),
                    str(india_channel.id),
                    str(japan_channel.id),
                )

            self.server_configs[guild_id] = {
                "date": date_channel.id,
                "india": india_channel.id,
                "japan": japan_channel.id,
            }

            await self.update_date_channel()
            # We don't need to call update_time_channels() here anymore,
            # because the loop will align itself and start on its own schedule.

            await interaction.followup.send(
                f"✅ **Time channels configured successfully!** The channels will update at the next 10-minute mark.\n"
                f"📅 Date: {date_channel.mention}\n"
                f"🇮🇳 India Time: {india_channel.mention}\n"
                f"🇯🇵 Japan Time: {japan_channel.mention}",
                ephemeral=True,
            )

        log.info("💻 Date & Time commands registered.")
