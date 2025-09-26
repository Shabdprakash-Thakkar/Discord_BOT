# Python_Files/youtube_notification.py

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import os

# Supabase and Google API Client libraries
from supabase import create_client, Client
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# A helper function for printing debug messages with a timestamp
def dprint(*args, **kwargs):
    """A helper function for printing debug messages."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] [YOUTUBE_API]", *args, **kwargs)


class YouTubeManager:
    """Manages YouTube notifications using the Data API v3."""

    def __init__(self, bot: commands.Bot):
        """
        Initializes the YouTubeManager, setting up connections to Supabase and the YouTube API.
        """
        self.bot = bot

        # Initialize Supabase Client
        sup_url = os.getenv("SUPABASE_URL")
        sup_key = os.getenv("SUPABASE_KEY")
        if not sup_url or not sup_key:
            raise ValueError(
                "Supabase URL or Key not found in .env. Please check your configuration."
            )
        self.supabase: Client = create_client(sup_url, sup_key)

        # Initialize YouTube API Client
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError(
                "YOUTUBE_API_KEY not found in .env. Please get a key from Google Cloud Console."
            )
        self.youtube = build("youtube", "v3", developerKey=api_key)

        # Cache for last known video ID to prevent duplicate notifications
        self.latest_video_ids = {}  # Format: { "yt_channel_id": "video_id" }
        dprint("YouTubeManager class has been initialized.")

    async def start(self):
        """Initializes the manager, loads data, and starts the background task."""
        await self._load_latest_videos_from_db()
        self.check_for_videos.start()
        dprint("YouTube Notification background task started.")

    async def _load_latest_videos_from_db(self):
        """Loads the last known video ID for each tracked channel from the database into the cache."""
        try:
            response = (
                self.supabase.table("youtube_notifications")
                .select("yt_channel_id, latest_video_id")
                .execute()
            )
            if response.data:
                for item in response.data:
                    self.latest_video_ids[item["yt_channel_id"]] = item.get(
                        "latest_video_id"
                    )
                dprint(
                    f"Loaded {len(self.latest_video_ids)} channels from the database into cache."
                )
        except Exception as e:
            dprint(f"Error loading latest videos from DB: {e}")

    @tasks.loop(minutes=15)
    async def check_for_videos(self):
        # ... (This entire function remains unchanged) ...
        try:
            configs = (
                self.supabase.table("youtube_notifications").select("*").execute().data
            )
            if not configs:
                return
            for config in configs:
                yt_channel_id = config["yt_channel_id"]
                try:
                    request = self.youtube.search().list(
                        part="snippet",
                        channelId=yt_channel_id,
                        maxResults=1,
                        order="date",
                        type="video",
                    )
                    api_response = request.execute()
                    if not api_response.get("items"):
                        continue
                    latest_item = api_response["items"][0]
                    video_id = latest_item["id"]["videoId"]
                    last_known_id = self.latest_video_ids.get(yt_channel_id)
                    published_at_str = latest_item["snippet"]["publishedAt"]
                    published_at = datetime.fromisoformat(
                        published_at_str.replace("Z", "+00:00")
                    )
                    if video_id != last_known_id and (
                        datetime.now(timezone.utc) - published_at
                    ) < timedelta(days=1):
                        dprint(f"New activity found for {yt_channel_id}: {video_id}")
                        self.latest_video_ids[yt_channel_id] = video_id
                        self.supabase.table("youtube_notifications").update(
                            {"latest_video_id": video_id}
                        ).eq("yt_channel_id", yt_channel_id).execute()
                        await self.send_notification(config, latest_item)
                except HttpError as e:
                    dprint(f"An HTTP Error occurred for channel {yt_channel_id}: {e}")
                except Exception as e:
                    dprint(
                        f"An error occurred while processing channel {yt_channel_id}: {e}"
                    )
        except Exception as e:
            dprint(f"A critical error occurred in the main check_for_videos loop: {e}")

    async def send_notification(self, config: dict, item: dict):
        # ... (This entire function remains unchanged) ...
        guild = self.bot.get_guild(int(config["guild_id"]))
        if not guild:
            return
        channel = guild.get_channel(int(config["discord_channel_id"]))
        if not channel:
            return
        role_to_mention = (
            guild.get_role(int(config.get("role_id")))
            if config.get("role_id")
            else None
        )
        snippet = item["snippet"]
        video_id = item["id"]["videoId"]
        video_title = snippet["title"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        event_type = snippet.get("liveBroadcastContent", "none")
        if event_type == "live":
            activity = "🔴 is LIVE now!"
        elif event_type == "upcoming":
            activity = "has scheduled a Premiere!"
        else:
            activity = "uploaded a new Video!"
        channel_name = snippet["channelTitle"]
        mention = role_to_mention.mention if role_to_mention else ""
        message = f"📢 {mention} Hey everyone! **{channel_name}** {activity}\n\n**{video_title}**\n{video_url}"
        try:
            await channel.send(message)
        except discord.Forbidden:
            dprint(
                f"Error: No permission to send messages in channel {channel.id} (Guild: {guild.id})"
            )

    @check_for_videos.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    def register_commands(self):
        """Registers all slash commands for the YouTube feature."""

        # ========= NEW COMMAND ADDED HERE =========
        @self.bot.tree.command(
            name="find-youtube-channel-id",
            description="Find the Channel ID for a YouTube username or handle (e.g., @xyzvlog).",
        )
        @app_commands.describe(
            username_or_handle="The @handle or custom username of the YouTube channel."
        )
        async def find_youtube_channel_id(
            interaction: discord.Interaction, username_or_handle: str
        ):
            await interaction.response.defer(ephemeral=True)
            try:
                # Use the search API to find a channel by its name/handle
                request = self.youtube.search().list(
                    part="snippet", q=username_or_handle, type="channel", maxResults=1
                )
                response = request.execute()

                if not response.get("items"):
                    await interaction.followup.send(
                        f"❌ Could not find a channel with the name or handle `{username_or_handle}`. Please check the spelling.",
                        ephemeral=True,
                    )
                    return

                # Extract info from the API response to show the user
                channel_item = response["items"][0]
                channel_id = channel_item["id"]["channelId"]
                channel_title = channel_item["snippet"]["title"]
                thumbnail_url = channel_item["snippet"]["thumbnails"]["default"]["url"]

                # Create an embed for a clean response
                embed = discord.Embed(
                    title="🔍 YouTube Channel Finder",
                    description=f"Found a channel that best matches your query.",
                    color=0xFF0000,  # YouTube Red
                )
                embed.set_thumbnail(url=thumbnail_url)
                embed.add_field(name="Channel Name", value=channel_title, inline=False)
                embed.add_field(
                    name="Channel ID", value=f"`{channel_id}`", inline=False
                )
                embed.set_footer(
                    text="Copy the Channel ID above to use in the /setup-youtube-notifications command."
                )

                await interaction.followup.send(embed=embed, ephemeral=True)

            except HttpError as e:
                dprint(f"YouTube API HTTP Error during channel search: {e}")
                await interaction.followup.send(
                    "❌ An error occurred while communicating with the YouTube API. The API key might be invalid or the quota may have been exceeded.",
                    ephemeral=True,
                )
            except Exception as e:
                dprint(f"Error during find-channel-id command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred. Please check the bot's console for details.",
                    ephemeral=True,
                )

        @self.bot.tree.command(
            name="setup-youtube-notifications",
            description="Set up notifications for a YouTube channel.",
        )
        @app_commands.describe(
            youtube_channel_id="The ID of the YouTube channel (e.g., UC-lHJZR3Gqxm24_Vd_AJ5Yw)",
            notification_channel="The Discord channel where notifications will be sent.",
            role_to_mention="The role to mention in the notification message.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def setup_youtube_notifications(
            interaction: discord.Interaction,
            youtube_channel_id: str,
            notification_channel: discord.TextChannel,
            role_to_mention: discord.Role,
        ):
            # ... (This command remains unchanged) ...
            await interaction.response.defer(ephemeral=True)
            if not youtube_channel_id.startswith("UC"):
                await interaction.followup.send(
                    "❌ Invalid YouTube Channel ID format. A valid ID typically starts with 'UC'.",
                    ephemeral=True,
                )
                return
            try:
                self.supabase.table("youtube_notifications").upsert(
                    {
                        "guild_id": str(interaction.guild.id),
                        "guild_name": interaction.guild.name,
                        "yt_channel_id": youtube_channel_id,
                        "discord_channel_id": str(notification_channel.id),
                        "channel_name": notification_channel.name,
                        "role_id": str(role_to_mention.id),
                        "role_name": role_to_mention.name,
                    }
                ).execute()
                request = self.youtube.search().list(
                    part="snippet",
                    channelId=youtube_channel_id,
                    maxResults=1,
                    order="date",
                    type="video",
                )
                api_response = request.execute()
                if api_response.get("items"):
                    video_id = api_response["items"][0]["id"]["videoId"]
                    self.latest_video_ids[youtube_channel_id] = video_id
                    self.supabase.table("youtube_notifications").update(
                        {"latest_video_id": video_id}
                    ).eq("yt_channel_id", youtube_channel_id).execute()
                await interaction.followup.send(
                    f"✅ Success! Notifications are configured for `{youtube_channel_id}`.",
                    ephemeral=True,
                )
            except Exception as e:
                dprint(f"Error during setup command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred.", ephemeral=True
                )

        @self.bot.tree.command(
            name="disable-youtube-notifications",
            description="Disable YouTube notifications for a specific channel.",
        )
        @app_commands.describe(
            youtube_channel_id="The YouTube channel ID to disable notifications for."
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def disable_youtube_notifications(
            interaction: discord.Interaction, youtube_channel_id: str
        ):
            # ... (This command remains unchanged) ...
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
                    self.latest_video_ids.pop(youtube_channel_id, None)
                    await interaction.followup.send(
                        f"✅ Notifications for `{youtube_channel_id}` have been disabled.",
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        "❌ No configuration was found for that YouTube channel ID on this server.",
                        ephemeral=True,
                    )
            except Exception as e:
                dprint(f"Error during disable command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred.", ephemeral=True
                )
