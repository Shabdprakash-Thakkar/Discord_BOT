import os
from .db import get_db_client
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timezone

def get_youtube_service():
    """
    Initializes and returns the YouTube Data API v3 service object.
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY not found in .env file.")
    return build("youtube", "v3", developerKey=api_key)

def find_youtube_channel_id(username_or_handle: str):
    """
    Finds the Channel ID for a YouTube username or handle.
    """
    youtube = get_youtube_service()
    try:
        request = youtube.search().list(
            part="snippet", q=username_or_handle, type="channel", maxResults=1
        )
        response = request.execute()
        if not response.get("items"):
            return None

        channel_item = response["items"][0]
        return {
            "channel_id": channel_item["id"]["channelId"],
            "channel_title": channel_item["snippet"]["title"],
            "thumbnail_url": channel_item["snippet"]["thumbnails"]["default"]["url"]
        }
    except HttpError as e:
        print(f"An HTTP Error occurred: {e}")
        return None

def get_youtube_notifications(guild_id: int):
    """
    Retrieves all YouTube notification configurations for a given guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("youtube_notifications")
        .select("yt_channel_id, discord_channel_id, role_id, yt_channel_name")
        .eq("guild_id", str(guild_id))
        .execute()
    )
    return data.data

def add_youtube_notification(guild_id: int, yt_channel_id: str, discord_channel_id: int, role_id: int):
    """
    Adds a YouTube notification configuration for a guild.
    """
    supabase = get_db_client()
    youtube = get_youtube_service()

    try:
        # Get channel name
        request = youtube.channels().list(part="snippet", id=yt_channel_id)
        response = request.execute()
        if not response.get("items"):
            raise ValueError("Invalid YouTube Channel ID")
        yt_channel_name = response["items"][0]["snippet"]["title"]

        data, count = supabase.table("youtube_notifications").upsert({
            "guild_id": str(guild_id),
            "yt_channel_id": yt_channel_id,
            "discord_channel_id": str(discord_channel_id),
            "role_id": str(role_id),
            "yt_channel_name": yt_channel_name,
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return data
    except HttpError as e:
        print(f"An HTTP Error occurred: {e}")
        return None

def remove_youtube_notification(guild_id: int, yt_channel_id: str):
    """
    Removes a YouTube notification configuration for a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("youtube_notifications").delete().match({
        "guild_id": str(guild_id),
        "yt_channel_id": yt_channel_id,
    }).execute()
    return data

def check_for_new_videos(guild_id: int):
    """
    Checks for new videos for all configured channels in a guild and updates the database.
    This function is intended to be called periodically by an external scheduler.
    """
    supabase = get_db_client()
    youtube = get_youtube_service()

    configs = get_youtube_notifications(guild_id)
    if not configs:
        return []

    new_videos = []
    for config in configs:
        yt_channel_id = config["yt_channel_id"]
        try:
            search_request = youtube.search().list(
                part="snippet",
                channelId=yt_channel_id,
                maxResults=1,
                order="date",
                type="video",
            )
            search_response = search_request.execute()
            if not search_response.get("items"):
                continue

            latest_item = search_response["items"][0]
            video_id = latest_item["id"]["videoId"]

            # Check if this video has been notified before
            db_entry = supabase.table("youtube_notifications").select("latest_video_id").eq("yt_channel_id", yt_channel_id).execute()
            last_known_id = db_entry.data[0]['latest_video_id'] if db_entry.data else None

            if video_id != last_known_id:
                # New video found, update DB and add to notification list
                supabase.table("youtube_notifications").update({
                    "latest_video_id": video_id,
                    "last_updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("yt_channel_id", yt_channel_id).execute()

                new_videos.append({
                    "guild_id": guild_id,
                    "discord_channel_id": config["discord_channel_id"],
                    "role_id": config["role_id"],
                    "video_title": latest_item["snippet"]["title"],
                    "video_url": f"https://www.youtube.com/watch?v={video_id}",
                    "channel_name": latest_item["snippet"]["channelTitle"]
                })

        except HttpError as e:
            print(f"An HTTP Error occurred for channel {yt_channel_id}: {e}")
        except Exception as e:
            print(f"An error occurred while processing channel {yt_channel_id}: {e}")

    return new_videos