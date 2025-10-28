from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services import level, no_text, date_and_time, youtube_notification

app = FastAPI()

# Pydantic models for request and response data
class LevelReward(BaseModel):
    level: int
    role_id: int
    role_name: str

class NotifyChannel(BaseModel):
    channel_id: int
    channel_name: str

class AutoResetConfig(BaseModel):
    days: int

class NoTextChannel(BaseModel):
    channel_id: int
    redirect_channel_id: int

class BypassRole(BaseModel):
    role_id: int

class TimeChannels(BaseModel):
    date_channel_id: int
    india_channel_id: int
    japan_channel_id: int

class YouTubeChannel(BaseModel):
    yt_channel_id: str
    discord_channel_id: int
    role_id: int

@app.get("/")
def read_root():
    return {"message": "Welcome to the Supporter BOT API"}

# Leveling endpoints
@app.get("/guilds/{guild_id}/leaderboard")
def get_leaderboard(guild_id: int):
    leaderboard_data = level.get_leaderboard(guild_id)
    if not leaderboard_data:
        raise HTTPException(status_code=404, detail="Leaderboard not found for this guild.")
    return leaderboard_data

@app.get("/guilds/{guild_id}/users/{user_id}/level")
def get_user_level(guild_id: int, user_id: int):
    user_level = level.get_user_level(guild_id, user_id)
    if user_level is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user_level

@app.get("/guilds/{guild_id}/level-rewards")
def get_level_rewards(guild_id: int):
    return level.get_level_rewards(guild_id)

@app.post("/guilds/{guild_id}/level-rewards")
def set_level_reward(guild_id: int, reward: LevelReward):
    level.set_level_reward(guild_id, reward.level, reward.role_id, reward.role_name)
    return {"message": "Level reward set successfully."}

@app.get("/guilds/{guild_id}/notify-channel")
def get_notify_channel(guild_id: int):
    return level.get_level_notify_channel(guild_id)

@app.post("/guilds/{guild_id}/notify-channel")
def set_notify_channel(guild_id: int, channel: NotifyChannel):
    level.set_level_notify_channel(guild_id, channel.channel_id, channel.channel_name)
    return {"message": "Notify channel set successfully."}

@app.get("/guilds/{guild_id}/auto-reset")
def get_auto_reset(guild_id: int):
    return level.get_auto_reset_config(guild_id)

@app.post("/guilds/{guild_id}/auto-reset")
def set_auto_reset(guild_id: int, config: AutoResetConfig):
    level.set_auto_reset_config(guild_id, config.days)
    return {"message": "Auto-reset config set successfully."}

@app.delete("/guilds/{guild_id}/auto-reset")
def delete_auto_reset(guild_id: int):
    level.stop_auto_reset(guild_id)
    return {"message": "Auto-reset disabled successfully."}

@app.post("/guilds/{guild_id}/reset-xp")
def post_reset_xp(guild_id: int):
    level.reset_xp(guild_id)
    return {"message": "XP reset successfully."}

# No-text channel endpoints
@app.get("/guilds/{guild_id}/no-text-channels")
def get_no_text_channels(guild_id: int):
    return no_text.get_no_text_channels(guild_id)

@app.post("/guilds/{guild_id}/no-text-channels")
def add_no_text_channel(guild_id: int, channel: NoTextChannel):
    no_text.add_no_text_channel(guild_id, channel.channel_id, channel.redirect_channel_id)
    return {"message": "No-text channel added successfully."}

@app.delete("/guilds/{guild_id}/no-text-channels/{channel_id}")
def remove_no_text_channel(guild_id: int, channel_id: int):
    no_text.remove_no_text_channel(guild_id, channel_id)
    return {"message": "No-text channel removed successfully."}

@app.get("/guilds/{guild_id}/bypass-roles")
def get_bypass_roles(guild_id: int):
    return no_text.get_bypass_roles(guild_id)

@app.post("/guilds/{guild_id}/bypass-roles")
def add_bypass_role(guild_id: int, role: BypassRole):
    no_text.add_bypass_role(guild_id, role.role_id)
    return {"message": "Bypass role added successfully."}

@app.delete("/guilds/{guild_id}/bypass-roles/{role_id}")
def remove_bypass_role(guild_id: int, role_id: int):
    no_text.remove_bypass_role(guild_id, role_id)
    return {"message": "Bypass role removed successfully."}

# Time channel endpoints
@app.get("/guilds/{guild_id}/time-channels")
def get_time_channels(guild_id: int):
    return date_and_time.get_time_channels(guild_id)

@app.post("/guilds/{guild_id}/time-channels")
def set_time_channels(guild_id: int, channels: TimeChannels):
    date_and_time.set_time_channels(guild_id, channels.date_channel_id, channels.india_channel_id, channels.japan_channel_id)
    return {"message": "Time channels set successfully."}

# YouTube notification endpoints
@app.get("/youtube/find-channel")
def find_youtube_channel(username_or_handle: str):
    channel_info = youtube_notification.find_youtube_channel_id(username_or_handle)
    if not channel_info:
        raise HTTPException(status_code=404, detail="YouTube channel not found.")
    return channel_info

@app.get("/guilds/{guild_id}/youtube-notifications")
def get_youtube_notifications(guild_id: int):
    return youtube_notification.get_youtube_notifications(guild_id)

@app.post("/guilds/{guild_id}/youtube-notifications")
def add_youtube_notification(guild_id: int, channel: YouTubeChannel):
    result = youtube_notification.add_youtube_notification(guild_id, channel.yt_channel_id, channel.discord_channel_id, channel.role_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Failed to add YouTube notification. Check the channel ID and API key.")
    return {"message": "YouTube notification added successfully."}

@app.delete("/guilds/{guild_id}/youtube-notifications/{yt_channel_id}")
def remove_youtube_notification(guild_id: int, yt_channel_id: str):
    youtube_notification.remove_youtube_notification(guild_id, yt_channel_id)
    return {"message": "YouTube notification removed successfully."}

@app.get("/guilds/{guild_id}/youtube-notifications/check")
def check_new_videos(guild_id: int):
    return youtube_notification.check_for_new_videos(guild_id)