import discord
from discord.ext import tasks
import pytz
import json
import os
import asyncio
import threading
from datetime import datetime, timedelta


def log_time_msg(message):
    """Helper for clean timestamped logging"""
    tz_india = pytz.timezone("Asia/Kolkata")
    print(
        f"[{datetime.now(tz_india).strftime('%Y-%m-%d %H:%M:%S')}] [TIME_MANAGER] {message}"
    )


class DateTimeManager:
    def __init__(self, bot, data_dir):
        self.bot = bot
        self.data_dir = data_dir
        self.time_file = os.path.join(data_dir, "date_and_time.json")
        self.lock = threading.Lock()
        self.server_configs = self._load_json_safe({})
        log_time_msg("Date and Time system is active ✅")

    # -------------------- File Safety --------------------

    def _save_json_safe(self, data):
        """Thread-safe JSON saving"""
        with self.lock:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.time_file, "w") as f:
                json.dump(data, f, indent=2)

    def _load_json_safe(self, default):
        """Load JSON configuration safely"""
        try:
            if os.path.exists(self.time_file):
                with open(self.time_file, "r") as f:
                    return json.load(f)
            return default
        except Exception as e:
            log_time_msg(
                f"❌ Failed to load {self.time_file}: {e}. Creating default file."
            )
            self._save_json_safe(default)
            return default

    # -------------------- Initialization --------------------

    async def start(self):
        """Start the date and time update loops"""
        if not self.update_time_channels.is_running():
            self.update_time_channels.start()
        if not self.update_date_daily.is_running():
            self.update_date_daily.start()

        # Do an initial date update immediately
        await self.update_date_channel()

    def get_config(self, guild_id):
        """Get configuration for a specific guild"""
        return self.server_configs.get(guild_id)

    async def setup_channels(
        self, interaction, date_channel, india_channel, japan_channel
    ):
        """Setup time channels for a server"""
        guild_id = str(interaction.guild_id)

        self.server_configs[guild_id] = {
            "date": date_channel.id,
            "india": india_channel.id,
            "japan": japan_channel.id,
        }

        self._save_json_safe(self.server_configs)

        # Update channels immediately
        await self.update_date_channel()
        await self.update_time_channels()

        await interaction.followup.send(
            f"✅ **Time channels configured successfully!**\n"
            f"📅 Date: {date_channel.mention}\n"
            f"🇮🇳 India Time: {india_channel.mention}\n"
            f"🇯🇵 Japan Time: {japan_channel.mention}",
            ephemeral=True,
        )

    # -------------------- Date Management --------------------

    async def update_date_channel(self):
        """Update date channels for all configured servers"""
        for guild_id, config in self.server_configs.items():
            try:
                tz_india = pytz.timezone("Asia/Kolkata")
                date_str = datetime.now(tz_india).strftime("%d %B, %Y")
                new_name = f"📅 {date_str}"

                channel = self.bot.get_channel(config["date"])
                if channel and channel.name != new_name:
                    await channel.edit(name=new_name)
                    log_time_msg(
                        f"✅ Updated date channel for guild {guild_id}: {new_name}"
                    )
            except Exception as e:
                log_time_msg(
                    f"❌ Error updating date channel for guild {guild_id}: {e}"
                )

    @tasks.loop(hours=24)
    async def update_date_daily(self):
        """Daily task to update date channels"""
        tz_india = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz_india)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        delay = (next_midnight - now).total_seconds()
        await asyncio.sleep(delay)

        while True:
            await self.update_date_channel()
            await asyncio.sleep(24 * 60 * 60)

    # -------------------- Time Management --------------------

    @tasks.loop(minutes=10)
    async def update_time_channels(self):
        """Update time channels every 10 minutes"""
        for guild_id, config in self.server_configs.items():
            try:
                tz_india = pytz.timezone("Asia/Kolkata")
                tz_japan = pytz.timezone("Asia/Tokyo")

                india_time = datetime.now(tz_india).strftime("%H:%M")
                japan_time = datetime.now(tz_japan).strftime("%H:%M")

                india_channel = self.bot.get_channel(config["india"])
                japan_channel = self.bot.get_channel(config["japan"])

                if india_channel:
                    india_name = f"🇮🇳 IST {india_time}"
                    if india_channel.name != india_name:
                        await india_channel.edit(name=india_name)

                if japan_channel:
                    japan_name = f"🇯🇵 JST {japan_time}"
                    if japan_channel.name != japan_name:
                        await japan_channel.edit(name=japan_name)

            except Exception as e:
                log_time_msg(
                    f"❌ Error updating time channels for guild {guild_id}: {e}"
                )

    @update_time_channels.before_loop
    async def before_update_time_channels(self):
        """Align to the next 10-minute mark before starting"""
        await self.bot.wait_until_ready()
        tz_india = pytz.timezone("Asia/Kolkata")

        now = datetime.now(tz_india)
        # Compute next 10-minute mark
        minute_offset = (10 - (now.minute % 10)) % 10
        if minute_offset == 0:
            minute_offset = 10  # if already exact, skip to next mark
        next_mark = (now + timedelta(minutes=minute_offset)).replace(
            second=0, microsecond=0
        )
        delay = (next_mark - now).total_seconds()

        log_time_msg(
            f"⏳ Aligning to next 10-minute mark ({next_mark.strftime('%H:%M')}) — waiting {int(delay)}s."
        )
        await asyncio.sleep(delay)
        log_time_msg(
            f"🕒 First time update triggered at {next_mark.strftime('%H:%M')} IST."
        )

    @update_date_daily.before_loop
    async def before_update_date_daily(self):
        """Wait for bot to be ready before starting date updates"""
        await self.bot.wait_until_ready()
