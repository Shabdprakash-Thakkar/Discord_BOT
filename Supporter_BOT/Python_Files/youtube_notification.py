# Python_Files/youtube_notification.py

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import asyncio
import os

# Supabase and Google API Client libraries
from supabase import create_client, Client
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the IST timezone for conversions
IST = timezone(timedelta(hours=5, minutes=30))


# Helper for consistent timestamped debug logging
def dprint(*args, **kwargs):
    print(f"[{datetime.now(IST).isoformat()}] [YOUTUBE_API]", *args, **kwargs)


class YouTubeManager:
    """Manages YouTube notifications using the Data API v3."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        sup_url = os.getenv("SUPABASE_URL")
        sup_key = os.getenv("SUPABASE_KEY")
        if not sup_url or not sup_key:
            raise ValueError("Supabase URL or Key not found in .env.")
        self.supabase: Client = create_client(sup_url, sup_key)

        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY not found in .env.")
        self.youtube = build("youtube", "v3", developerKey=api_key)

        # Cache structure: { "yt_channel_id": {"id": "latest_video_id", "status": "live/none/upcoming"} }
        self.channel_cache = {}
        self.last_notified = {}  # cooldown tracker per channel
        dprint("YouTubeManager class has been initialized.")

    async def start(self):
        """Initializes the manager, loads data, and starts the background task."""
        await self._load_cache_from_db()
        self.check_for_videos.start()
        dprint("YouTube Notification background task started.")

    async def _load_cache_from_db(self):
        """Loads the last known video ID and status for each channel from the DB into the local cache."""
        try:
            response = (
                self.supabase.table("youtube_notifications")
                .select("yt_channel_id, latest_video_id, last_video_status")
                .execute()
            )
            if response.data:
                for item in response.data:
                    self.channel_cache[item["yt_channel_id"]] = {
                        "id": item.get("latest_video_id"),
                        "status": item.get("last_video_status"),
                    }
                dprint(
                    f"Loaded {len(self.channel_cache)} channels from the database into cache."
                )
        except Exception as e:
            dprint(f"Error loading cache from DB: {e}")

    @tasks.loop(minutes=15)
    async def check_for_videos(self):
        """Checks all configured channels for new videos or live events."""
        try:
            configs = (
                self.supabase.table("youtube_notifications").select("*").execute().data
            )
            if not configs:
                return

            for config in configs:
                yt_channel_id = config["yt_channel_id"]

                try:
                    search_response = (
                        self.youtube.search()
                        .list(
                            part="snippet",
                            channelId=yt_channel_id,
                            maxResults=1,
                            order="date",
                            type="video",
                        )
                        .execute()
                    )

                    if not search_response.get("items"):
                        continue

                    latest_item = search_response["items"][0]
                    video_id = latest_item["id"]["videoId"]
                    event_type = latest_item["snippet"].get(
                        "liveBroadcastContent", "none"
                    )
                    video_title = latest_item["snippet"]["title"]

                    cached_data = self.channel_cache.get(
                        yt_channel_id, {"id": None, "status": None}
                    )
                    last_known_id = cached_data.get("id")
                    last_known_status = cached_data.get("status")

                    dprint(
                        f"Check {yt_channel_id}: DB={last_known_id}/{last_known_status}, API={video_id}/{event_type}"
                    )

                    # Skip if same ID and status (no new event)
                    if video_id == last_known_id and event_type == last_known_status:
                        continue

                    should_notify = False

                    # New upload or different video ID
                    if video_id != last_known_id:
                        should_notify = True

                    # Livestream started
                    elif (
                        video_id == last_known_id
                        and event_type == "live"
                        and last_known_status in ("upcoming", "none")
                    ):
                        should_notify = True

                    # Cooldown (1 hour)
                    now = datetime.now(timezone.utc)
                    last_time = self.last_notified.get(yt_channel_id)
                    if (
                        should_notify
                        and last_time
                        and (now - last_time).total_seconds() < 3600
                    ):
                        dprint(
                            f"Skipping duplicate within cooldown for {yt_channel_id}"
                        )
                        should_notify = False

                    if not should_notify:
                        continue

                    # Send notification
                    dprint(
                        f"New activity for {yt_channel_id}: ID={video_id}, Status={event_type}."
                    )
                    await self.send_notification(config, latest_item)
                    self.last_notified[yt_channel_id] = now

                    # Update database & cache
                    title_preview = " ".join(video_title.split()[:3])
                    self.supabase.table("youtube_notifications").update(
                        {
                            "latest_video_id": video_id,
                            "last_video_status": event_type,
                            "latest_video_title_preview": title_preview,
                            "last_updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("yt_channel_id", yt_channel_id).execute()

                    self.channel_cache[yt_channel_id] = {
                        "id": video_id,
                        "status": event_type,
                    }

                    await asyncio.sleep(1)

                except HttpError as e:
                    dprint(f"HTTP Error for {yt_channel_id}: {e}")
                except Exception as e:
                    dprint(f"Error processing {yt_channel_id}: {e}")

        except Exception as e:
            dprint(f"Critical error in main YouTube loop: {e}")

    async def send_notification(self, config: dict, item: dict):
        """Formats and sends the notification message."""
        guild = self.bot.get_guild(int(config["guild_id"]))
        if not guild:
            return

        channel = guild.get_channel(int(config["discord_channel_id"]))
        if not channel:
            return

        role = (
            guild.get_role(int(config.get("role_id")))
            if config.get("role_id")
            else None
        )
        mention = role.mention if role else ""

        snippet = item["snippet"]
        video_id = item["id"]["videoId"]
        video_title = snippet["title"]
        channel_name = snippet["channelTitle"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        event_type = snippet.get("liveBroadcastContent", "none")

        # Determine message type
        activity_line = ""
        if event_type == "upcoming":
            try:
                video_request = self.youtube.videos().list(
                    part="liveStreamingDetails", id=video_id
                )
                video_response = video_request.execute()
                details = video_response["items"][0]["liveStreamingDetails"]
                start_time_utc_str = details["scheduledStartTime"]
                start_time_utc = datetime.fromisoformat(
                    start_time_utc_str.replace("Z", "+00:00")
                )
                start_time_ist = start_time_utc.astimezone(IST)
                time_str = start_time_ist.strftime("%d %B, %Y at %H:%M IST")
                activity_line = f"has scheduled a new Premiere:\n*Starts on {time_str}*"
            except Exception as e:
                dprint(f"Could not fetch premiere time for {video_id}: {e}")
                activity_line = "has scheduled a new Premiere"
        elif event_type == "live":
            activity_line = "is now LIVE"
        else:
            activity_line = "just uploaded a new video"

        message = f"Hey {mention}! **{channel_name}** {activity_line}:\n\n{video_url}"

        try:
            await channel.send(message)
        except discord.Forbidden:
            dprint(f"Permission error: cannot send in {channel.id}")
        except Exception as e:
            dprint(f"Error sending message in {channel.id}: {e}")

    @check_for_videos.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ---------------- SLASH COMMANDS ---------------- #
    def register_commands(self):
        """Registers all slash commands for YouTube features."""

        @self.bot.tree.command(
            name="y1-find-youtube-channel-id",
            description="Find the Channel ID for a YouTube username or handle.",
        )
        @app_commands.describe(
            username_or_handle="The @handle or custom username of the YouTube channel."
        )
        async def find_youtube_channel_id(
            interaction: discord.Interaction, username_or_handle: str
        ):
            await interaction.response.defer(ephemeral=True)
            try:
                request = self.youtube.search().list(
                    part="snippet", q=username_or_handle, type="channel", maxResults=1
                )
                response = request.execute()
                if not response.get("items"):
                    await interaction.followup.send(
                        f"❌ Could not find a channel with the name or handle `{username_or_handle}`.",
                        ephemeral=True,
                    )
                    return

                channel_item = response["items"][0]
                channel_id = channel_item["id"]["channelId"]
                channel_title = channel_item["snippet"]["title"]
                thumbnail_url = channel_item["snippet"]["thumbnails"]["default"]["url"]

                embed = discord.Embed(
                    title="🔍 YouTube Channel Finder",
                    description="Found a channel that best matches your query.",
                    color=0xFF0000,
                )
                embed.set_thumbnail(url=thumbnail_url)
                embed.add_field(name="Channel Name", value=channel_title, inline=False)
                embed.add_field(
                    name="Channel ID", value=f"`{channel_id}`", inline=False
                )
                embed.set_footer(
                    text="Copy the Channel ID to use in /setup-youtube-notifications."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                dprint(f"Error during find-channel-id command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred.", ephemeral=True
                )

        @self.bot.tree.command(
            name="y2-setup-youtube-notifications",
            description="Set up notifications for a YouTube channel.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def setup_youtube_notifications(
            interaction: discord.Interaction,
            youtube_channel_id: str,
            notification_channel: discord.TextChannel,
            role_to_mention: discord.Role,
        ):
            await interaction.response.defer(ephemeral=True)
            if not youtube_channel_id.startswith("UC"):
                await interaction.followup.send(
                    "❌ Invalid YouTube Channel ID format.", ephemeral=True
                )
                return

            try:
                search_request = self.youtube.search().list(
                    part="snippet",
                    channelId=youtube_channel_id,
                    maxResults=1,
                    order="date",
                    type="video",
                )
                api_response = search_request.execute()

                latest_video_id, latest_video_status, yt_channel_name, title_preview = (
                    None,
                    None,
                    "Unknown Channel",
                    None,
                )

                if api_response.get("items"):
                    item = api_response["items"][0]
                    latest_video_id = item["id"]["videoId"]
                    latest_video_status = item["snippet"].get(
                        "liveBroadcastContent", "none"
                    )
                    yt_channel_name = item["snippet"]["channelTitle"]
                    title_preview = " ".join(item["snippet"]["title"].split()[:3])

                self.supabase.table("youtube_notifications").upsert(
                    {
                        "guild_id": str(interaction.guild.id),
                        "guild_name": interaction.guild.name,
                        "yt_channel_id": youtube_channel_id,
                        "discord_channel_id": str(notification_channel.id),
                        "channel_name": notification_channel.name,
                        "role_id": str(role_to_mention.id),
                        "role_name": role_to_mention.name,
                        "latest_video_id": latest_video_id,
                        "last_video_status": latest_video_status,
                        "yt_channel_name": yt_channel_name,
                        "latest_video_title_preview": title_preview,
                        "last_updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).execute()

                self.channel_cache[youtube_channel_id] = {
                    "id": latest_video_id,
                    "status": latest_video_status,
                }

                await interaction.followup.send(
                    f"✅ Success! Notifications are configured for **{yt_channel_name}**.",
                    ephemeral=True,
                )
            except Exception as e:
                dprint(f"Error during setup command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred.", ephemeral=True
                )

        @self.bot.tree.command(
            name="y3-disable-youtube-notifications",
            description="Disable YouTube notifications for a specific channel.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def disable_youtube_notifications(
            interaction: discord.Interaction, youtube_channel_id: str
        ):
            await interaction.response.defer(ephemeral=True)
            try:
                result = (
                    self.supabase.table("youtube_notifications")
                    .delete()
                    .match(
                        {
                            "guild_id": str(interaction.guild.id),
                            "yt_channel_id": youtube_channel_id,
                        }
                    )
                    .execute()
                )
                if result.data:
                    self.channel_cache.pop(youtube_channel_id, None)
                    await interaction.followup.send(
                        f"✅ Notifications for `{youtube_channel_id}` have been disabled.",
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        "❌ No configuration was found for that YouTube channel ID.",
                        ephemeral=True,
                    )
            except Exception as e:
                dprint(f"Error during disable command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred.", ephemeral=True
                )
