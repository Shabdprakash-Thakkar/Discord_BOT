from .db import get_db_client

def get_time_channels(guild_id: int):
    """
    Retrieves the time channel configurations for a given guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("time_channels")
        .select("date_channel_id, india_channel_id, japan_channel_id")
        .eq("guild_id", str(guild_id))
        .execute()
    )
    return data.data[0] if data.data else None

def set_time_channels(guild_id: int, date_channel_id: int, india_channel_id: int, japan_channel_id: int):
    """
    Sets the time channel configurations for a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("time_channels").upsert({
        "guild_id": str(guild_id),
        "date_channel_id": str(date_channel_id),
        "india_channel_id": str(india_channel_id),
        "japan_channel_id": str(japan_channel_id),
    }).execute()
    return data