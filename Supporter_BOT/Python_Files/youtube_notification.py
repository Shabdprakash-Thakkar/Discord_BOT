# Python_Files/youtube_notification.py
# A robust, database-driven YouTube notification system.

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import asyncio
import os
import asyncpg
import logging

# Use the official Google API client library
# pip install google-api-python-client
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))


class YouTubeManager:
    """Manages YouTube notifications using the Data API v3."""

    def __init__(self, bot: commands.Bot, pool: asyncpg.Pool):
        self.bot = bot
        self.pool = pool

        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY is not defined in the .env file.")

        # We need to run the synchronous Google API client in an executor
        # to prevent it from blocking the bot's asynchronous event loop.
        self.youtube = build("youtube", "v3", developerKey=api_key)
        log.info("YouTube Notification system has been initialized.")

    async def start(self):
        """Initializes and starts the background task."""
        self.check_for_videos.start()

    # --- Asynchronous API Wrappers ---

    async def _api_search_channel(self, yt_channel_id: str):
        """Runs the synchronous search API call in a non-blocking way."""
        return await self.bot.loop.run_in_executor(
            None,
            lambda: self.youtube.search()
            .list(
                part="snippet",
                channelId=yt_channel_id,
                maxResults=1,
                order="date",
                type="video",
            )
            .execute(),
        )

    async def _api_get_video_details(self, video_id: str):
        """Runs the synchronous videos API call in a non-blocking way."""
        return await self.bot.loop.run_in_executor(
            None,
            lambda: self.youtube.videos()
            .list(part="snippet,liveStreamingDetails", id=video_id)
            .execute(),
        )

    # --- Core Notification Logic ---

    @tasks.loop(minutes=15)
    async def check_for_videos(self):
        """The main loop that checks all configured channels for new videos."""
        log.info("Running YouTube notification check...")

        configs = await self.pool.fetch(
            "SELECT * FROM public.youtube_notification_config WHERE is_enabled = TRUE"
        )
        if not configs:
            log.info("No active YouTube notification configurations found.")
            return

        for config in configs:
            guild_id_str = config["guild_id"]
            yt_channel_id = config["yt_channel_id"]

            try:
                # 1. Get the latest videos from the YouTube Channel
                search_response = await self._api_search_channel(yt_channel_id)
                if not search_response.get("items"):
                    continue

                # 2. Iterate through the fetched videos (from newest to oldest)
                for item in reversed(search_response["items"]):
                    video_id = item["id"]["videoId"]

                    # 3. Check if we have ALREADY notified this specific guild about this specific video.
                    # This is the most important check to prevent duplicates.
                    log_exists = await self.pool.fetchval(
                        "SELECT 1 FROM public.youtube_notification_logs WHERE guild_id = $1 AND yt_channel_id = $2 AND video_id = $3",
                        guild_id_str,
                        yt_channel_id,
                        video_id,
                    )

                    if log_exists:
                        continue  # Skip if already logged/notified for this guild.

                    # 4. If not notified, get full video details and send the notification.
                    log.info(
                        f"New video activity found for guild {guild_id_str} on channel {yt_channel_id}: {video_id}"
                    )
                    video_details_response = await self._api_get_video_details(video_id)

                    if video_details_response.get("items"):
                        await self.send_notification(
                            config, video_details_response["items"][0]
                        )

                    # 5. Log the notification to the database to prevent future duplicates.
                    await self.pool.execute(
                        "INSERT INTO public.youtube_notification_logs (guild_id, yt_channel_id, video_id, video_status) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
                        guild_id_str,
                        yt_channel_id,
                        video_id,
                        item["snippet"].get("liveBroadcastContent", "none"),
                    )
                    await asyncio.sleep(1)  # Small delay to avoid rate-limiting

            except HttpError as e:
                log.error(f"YouTube API HTTP Error for channel {yt_channel_id}: {e}")
            except Exception as e:
                log.error(
                    f"An unexpected error occurred while processing YouTube channel {yt_channel_id}: {e}"
                )

    async def send_notification(self, config: dict, video_details: dict):
        """Formats and sends the Discord notification message."""
        guild = self.bot.get_guild(int(config["guild_id"]))
        channel = self.bot.get_channel(int(config["target_channel_id"]))
        if not guild or not channel:
            return

        role = (
            guild.get_role(int(config["mention_role_id"]))
            if config["mention_role_id"]
            else None
        )
        mention = role.mention if role else "@here"

        snippet = video_details["snippet"]
        video_id = video_details["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        event_type = snippet.get("liveBroadcastContent", "none")

        activity_line = "just uploaded a new video"
        if event_type == "live":
            activity_line = "is now LIVE"
        elif event_type == "upcoming":
            try:
                start_time_str = video_details["liveStreamingDetails"][
                    "scheduledStartTime"
                ]
                start_time_utc = datetime.fromisoformat(
                    start_time_str.replace("Z", "+00:00")
                )
                activity_line = f"has scheduled a new stream! Starting {discord.utils.format_dt(start_time_utc, 'R')}"
            except KeyError:
                activity_line = "has scheduled a new stream"

        message = f"📢 {mention} **{snippet['channelTitle']}** {activity_line}!\n\n**{snippet['title']}**\n{video_url}"

        try:
            await channel.send(message)
            log.info(
                f"Sent notification for video {video_id} to guild {config['guild_id']}"
            )
        except discord.Forbidden:
            log.warning(
                f"Missing permissions to send YouTube notification in channel {channel.id} (Guild: {guild.id})"
            )
        except Exception as e:
            log.error(f"Failed to send YouTube notification: {e}")

    @check_for_videos.before_loop
    async def before_check_for_videos(self):
        """Aligns the loop to start on a clean 15-minute mark."""
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        minutes_to_wait = 15 - (now.minute % 15)
        seconds_to_wait = (minutes_to_wait * 60) - now.second
        log.info(
            f"Aligning YouTube check. Waiting {seconds_to_wait} seconds for first run."
        )
        await asyncio.sleep(seconds_to_wait)

    # --- Slash Commands ---

    def register_commands(self):

        @self.bot.tree.command(
            name="y1-find-youtube-channel-id",
            description="Find the Channel ID for a YouTube @handle.",
        )
        @app_commands.describe(
            handle="The @handle of the YouTube channel (e.g., @MrBeast)."
        )
        async def find_youtube_channel_id(
            interaction: discord.Interaction, handle: str
        ):
            await interaction.response.defer(ephemeral=True)
            try:
                # The search API is the most reliable way to find a channel by its handle/name
                search_result = await self.bot.loop.run_in_executor(
                    None,
                    lambda: self.youtube.search()
                    .list(part="snippet", q=handle, type="channel", maxResults=1)
                    .execute(),
                )
                if not search_result.get("items"):
                    await interaction.followup.send(
                        f"❌ Could not find a channel with the handle `{handle}`."
                    )
                    return

                item = search_result["items"][0]["snippet"]
                embed = discord.Embed(title="🔍 YouTube Channel Found", color=0xFF0000)
                embed.set_thumbnail(url=item["thumbnails"]["default"]["url"])
                embed.add_field(name="Channel Name", value=item["title"], inline=False)
                embed.add_field(
                    name="Channel ID", value=f"`{item['channelId']}`", inline=False
                )
                embed.set_footer(text="Copy this Channel ID for the setup command.")
                await interaction.followup.send(embed=embed)
            except Exception as e:
                log.error(f"Error in /y1-find-youtube-channel-id: {e}")
                await interaction.followup.send(
                    "❌ An API error occurred. Please try again later."
                )

        @self.bot.tree.command(
            name="y2-setup-youtube-notifications",
            description="Set up notifications for a YouTube channel.",
        )
        @app_commands.checks.has_permissions(manage_guild=True)
        async def setup_notifications(
            interaction: discord.Interaction,
            youtube_channel_id: str,
            notification_channel: discord.TextChannel,
            role_to_mention: discord.Role,
        ):
            await interaction.response.defer(ephemeral=True)
            if not youtube_channel_id.startswith("UC"):
                await interaction.followup.send(
                    "❌ That doesn't look like a valid YouTube Channel ID. It should start with `UC`."
                )
                return

            try:
                # Verify the channel ID is valid by fetching its details
                channel_details_res = await self.bot.loop.run_in_executor(
                    None,
                    lambda: self.youtube.channels()
                    .list(part="snippet", id=youtube_channel_id)
                    .execute(),
                )
                if not channel_details_res.get("items"):
                    await interaction.followup.send(
                        "❌ Could not find a YouTube channel with that ID."
                    )
                    return
                yt_channel_name = channel_details_res["items"][0]["snippet"]["title"]

                query = """
                    INSERT INTO public.youtube_notification_config (guild_id, yt_channel_id, target_channel_id, mention_role_id, guild_name, yt_channel_name, target_channel_name, mention_role_name)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (guild_id, yt_channel_id) DO UPDATE SET
                      target_channel_id = $3, mention_role_id = $4, updated_at = NOW(),
                      yt_channel_name = $6, target_channel_name = $7, mention_role_name = $8;
                """
                await self.pool.execute(
                    query,
                    str(interaction.guild.id),
                    youtube_channel_id,
                    str(notification_channel.id),
                    str(role_to_mention.id),
                    interaction.guild.name,
                    yt_channel_name,
                    notification_channel.name,
                    role_to_mention.name,
                )

                await interaction.followup.send(
                    f"✅ Success! I will now post notifications for **{yt_channel_name}** in {notification_channel.mention} and mention {role_to_mention.mention}."
                )
            except Exception as e:
                log.error(f"Error in /y2-setup: {e}")
                await interaction.followup.send(
                    "❌ An error occurred during setup. Please check the channel ID and my permissions."
                )

        @self.bot.tree.command(
            name="y3-disable-youtube-notifications",
            description="Disable YouTube notifications for a channel.",
        )
        @app_commands.checks.has_permissions(manage_guild=True)
        async def disable_notifications(
            interaction: discord.Interaction, youtube_channel_id: str
        ):
            await interaction.response.defer(ephemeral=True)
            result = await self.pool.execute(
                "DELETE FROM public.youtube_notification_config WHERE guild_id = $1 AND yt_channel_id = $2",
                str(interaction.guild.id),
                youtube_channel_id,
            )
            if result == "DELETE 1":
                await interaction.followup.send(
                    f"✅ Notifications for the YouTube channel `{youtube_channel_id}` have been disabled."
                )
            else:
                await interaction.followup.send(
                    f"❌ No notification setup was found for that YouTube channel ID in this server."
                )

        log.info("💻 YouTube Notification commands registered.")
