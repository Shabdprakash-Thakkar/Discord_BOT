from .db import get_db_client

def get_no_text_channels(guild_id: int):
    """
    Retrieves the no-text channel configurations for a given guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("no_text_channels")
        .select("channel_id, redirect_channel_id")
        .eq("guild_id", str(guild_id))
        .execute()
    )
    return data.data

def add_no_text_channel(guild_id: int, channel_id: int, redirect_channel_id: int):
    """
    Adds a no-text channel configuration for a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("no_text_channels").upsert({
        "guild_id": str(guild_id),
        "channel_id": str(channel_id),
        "redirect_channel_id": str(redirect_channel_id),
    }).execute()
    return data

def remove_no_text_channel(guild_id: int, channel_id: int):
    """
    Removes a no-text channel configuration for a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("no_text_channels").delete().match({
        "guild_id": str(guild_id),
        "channel_id": str(channel_id),
    }).execute()
    return data

def get_bypass_roles(guild_id: int):
    """
    Retrieves the bypass roles for a given guild.
    """
    supabase = get_db_client()
    data = (
        supabase.table("bypass_roles")
        .select("role_id")
        .eq("guild_id", str(guild_id))
        .execute()
    )
    return [item['role_id'] for item in data.data]

def add_bypass_role(guild_id: int, role_id: int):
    """
    Adds a bypass role for a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("bypass_roles").upsert({
        "guild_id": str(guild_id),
        "role_id": str(role_id),
    }).execute()
    return data

def remove_bypass_role(guild_id: int, role_id: int):
    """
    Removes a bypass role for a guild.
    """
    supabase = get_db_client()
    data, count = supabase.table("bypass_roles").delete().match({
        "guild_id": str(guild_id),
        "role_id": str(role_id),
    }).execute()
    return data