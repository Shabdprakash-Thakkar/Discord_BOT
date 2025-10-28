from .db import get_db_client

def get_leaderboard(guild_id: int):
    """
    Retrieves the top 10 users from the leaderboard for a given guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("users")
        .select("user_id, username, level, xp")
        .eq("guild_id", str(guild_id))
        .order("xp", desc=True)
        .limit(10)
        .execute()
    )
    return data.data

def get_user_level(guild_id: int, user_id: int):
    """
    Retrieves the level and XP for a specific user in a guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("users")
        .select("level, xp")
        .eq("guild_id", str(guild_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    return data.data[0] if data.data else None

def get_level_rewards(guild_id: int):
    """
    Retrieves all configured level rewards for a given guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("level_roles")
        .select("level, role_id, role_name")
        .eq("guild_id", str(guild_id))
        .order("level", desc=True)
        .execute()
    )
    return data.data

def set_level_reward(guild_id: int, level: int, role_id: int, role_name: str):
    """
    Sets a role reward for a specific level in a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("level_roles").upsert({
        "guild_id": str(guild_id),
        "level": level,
        "role_id": str(role_id),
        "role_name": role_name,
    }).execute()
    return data

def get_level_notify_channel(guild_id: int):
    """
    Retrieves the channel ID for level-up notifications in a guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("level_notify_channel")
        .select("channel_id, channel_name")
        .eq("guild_id", str(guild_id))
        .execute()
    )
    return data.data[0] if data.data else None

def set_level_notify_channel(guild_id: int, channel_id: int, channel_name: str):
    """
    Sets the channel for level-up notification messages in a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("level_notify_channel").upsert({
        "guild_id": str(guild_id),
        "channel_id": str(channel_id),
        "channel_name": channel_name,
    }).execute()
    return data

def get_auto_reset_config(guild_id: int):
    """
    Retrieves the auto-reset configuration for a guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("auto_reset")
        .select("days, last_reset")
        .eq("guild_id", str(guild_id))
        .execute()
    )
    return data.data[0] if data.data else None

def set_auto_reset_config(guild_id: int, days: int):
    """
    Sets the auto-reset configuration for a guild.
    """
    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    supabase = get_db_client()
    data, count = supabase.table("auto_reset").upsert({
        "guild_id": str(guild_id),
        "days": days,
        "last_reset": now.isoformat(),
    }).execute()
    return data

def stop_auto_reset(guild_id: int):
    """
    Disables automatic XP reset for a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("auto_reset").delete().eq("guild_id", str(guild_id)).execute()
    return data

def reset_xp(guild_id: int):
    """
    Resets all XP and levels for a guild.
    """
    supabase = get_db_client()
    # This is a simplified version. The original also removed roles.
    # The role removal logic will need to be handled by the bot itself.
    data, count = supabase.table("users").update({"xp": 0, "level": 0, "voice_xp_earned": 0}).eq("guild_id", str(guild_id)).execute()
    supabase.table("last_notified_level").update({"level": 0}).eq("guild_id", str(guild_id)).execute()
    return data