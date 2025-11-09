import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import os
from supabase import create_client, Client

# -----------------------------
# Define IST Timezone
# -----------------------------
IST = timezone(timedelta(hours=5, minutes=30))

# -----------------------------
# Voice XP Limit Constant
# -----------------------------
VOICE_XP_LIMIT = 1500

# -----------------------------
# Debug toggle
# -----------------------------
DEBUG = True  # Change to True if you want detailed print statements for debugging


def dprint(*args, **kwargs):
    if DEBUG:
        print(f"[{datetime.now(IST).isoformat()}]", *args, **kwargs)


def safe_parse_iso(dt_str: str) -> datetime:
    """Parse ISO-ish strings from DB (handles 'Z' or missing tz) and return IST-aware datetime."""
    s = str(dt_str or "").strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    except Exception:
        # Try without fractional seconds
        try:
            s2 = s.split(".")[0]
            dt = datetime.fromisoformat(s2)
        except Exception:
            # Fallback: now in IST
            return datetime.now(IST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


class LevelManager:
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.data_dir = data_dir
        self.voice_sessions = {}  # {(guild_id, user_id): datetime}
        self.cooldowns = {}  # {(guild_id, user_id): datetime}

        # Load Supabase
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError(
                "⚠ Supabase URL or KEY not found! Make sure .env has SUPABASE_URL and SUPABASE_KEY"
            )

        self.supabase: Client = create_client(url, key)

    async def start(self):
        """Starts the manager and its background tasks."""
        print("🎮 LevelManager started")
        if not self.reset_loop.is_running():
            self.reset_loop.start()
        if not self.voice_tick_loop.is_running():
            self.voice_tick_loop.start()
        try:
            self.bot.add_listener(self.on_voice_state_update, "on_voice_state_update")
        except Exception as e:
            dprint(f"[WARN] Could not add voice listener: {e}")
        try:
            await self.check_and_run_auto_reset()
        except Exception as e:
            dprint(f"[WARN] Initial auto-reset check failed: {e}")

    async def _check_and_handle_level_up(self, member: discord.Member, new_level: int):
        guild_id = member.guild.id
        user_id = member.id
        last_level = self.get_user_last_notified_level(guild_id, user_id)

        if new_level > last_level:
            dprint(f"[LEVEL UP] {member.name} reached Level {new_level}")
            await self.upgrade_user_roles(member, new_level)
            all_roles_data = self.get_all_level_roles(guild_id)
            earned_role = None
            for role_data in all_roles_data:
                if role_data["level"] == new_level:
                    role_obj = member.guild.get_role(int(role_data["role_id"]))
                    if role_obj:
                        earned_role = role_obj
                        break

            channel_id = self.get_notify_channel(guild_id)
            if not channel_id:
                dprint(f"[ERROR] No notification channel set for guild {guild_id}")
                return

            channel = self.bot.get_channel(int(channel_id))
            if (
                not channel
                or not channel.permissions_for(member.guild.me).send_messages
            ):
                dprint(
                    f"[ERROR] Cannot find or send messages in notification channel {channel_id}"
                )
                return

            try:
                if earned_role:
                    await channel.send(
                        f"🎉 Congrats {member.mention}! You've reached **Level {new_level}** and unlocked the role {earned_role.mention}!"
                    )
                else:
                    await channel.send(
                        f"🚀 Congrats {member.mention}! You've reached **Level {new_level}**! Keep it up!"
                    )
            except Exception as e:
                dprint(
                    f"  [CRITICAL FAIL] An error occurred while trying to send the message: {e}"
                )
                return

            # MODIFIED: Pass names to the function
            self.set_user_last_notified_level(
                guild_id, user_id, new_level, member.guild.name, member.name
            )

    def get_all_level_roles(self, guild_id: int):
        try:
            data = (
                self.supabase.table("level_roles")
                .select("*")
                .eq("guild_id", str(guild_id))
                .order("level", desc=True)
                .execute()
            )
            return data.data if data.data else []
        except Exception as e:
            dprint(f"[ERROR] Failed to get level roles: {e}")
            return []

    async def upgrade_user_roles(self, member: discord.Member, new_level: int):
        """
        Upgrades a user's roles based on their new level.
        Returns True if roles were changed, False otherwise.
        """
        try:
            guild_id = member.guild.id
            all_level_roles_data = self.get_all_level_roles(guild_id)
            if not all_level_roles_data:
                return False

            target_role_id = None
            for role_data in all_level_roles_data:
                if new_level >= role_data["level"]:
                    target_role_id = int(role_data["role_id"])
                    break

            all_level_role_ids = {int(r["role_id"]) for r in all_level_roles_data}
            roles_to_remove = []
            user_has_target_role = False
            for role in member.roles:
                if role.id in all_level_role_ids:
                    if role.id == target_role_id:
                        user_has_target_role = True
                    else:
                        roles_to_remove.append(role)

            roles_changed = False
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Level role sync")
                roles_changed = True

            if target_role_id and not user_has_target_role:
                target_role_obj = member.guild.get_role(target_role_id)
                if target_role_obj:
                    await member.add_roles(
                        target_role_obj, reason=f"Reached Level {new_level}"
                    )
                    roles_changed = True

            return roles_changed

        except discord.Forbidden:
            dprint(
                f"[ERROR] Bot lacks permission to manage roles in guild {member.guild.id}"
            )
        except Exception as e:
            dprint(
                f"[CRITICAL ERROR] Failed to upgrade user roles for {member.display_name}: {e}"
            )
        return False

    async def remove_level_reward_roles(self, guild: discord.Guild):
        if not guild:
            return 0, 0
        level_roles_data = self.get_all_level_roles(guild.id)
        if not level_roles_data:
            return 0, 0
        reward_role_ids = {int(row["role_id"]) for row in level_roles_data}
        roles_removed, users_affected = 0, 0
        for member in guild.members:
            if member.bot:
                continue
            roles_to_remove = [
                role for role in member.roles if role.id in reward_role_ids
            ]
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="XP Reset")
                    roles_removed += len(roles_to_remove)
                    users_affected += 1
                except discord.Forbidden:
                    dprint(
                        f"[WARN] No permission to remove roles from {member.display_name} in {guild.name}"
                    )
                except Exception as e:
                    dprint(
                        f"[WARN] Failed to remove roles from {member.display_name}: {e}"
                    )
        return roles_removed, users_affected

    async def _award_voice_xp(self, member: discord.Member, start_time: datetime):
        """Awards XP for voice activity, respecting the voice XP limit."""
        user = self.get_user(member.guild.id, member.id, member.name, member.guild.name)
        current_voice_xp = user.get("voice_xp_earned", 0)

        if current_voice_xp >= VOICE_XP_LIMIT:
            # dprint(f"[VOICE LIMIT] {member.name} has reached the voice XP limit.")
            return datetime.now(IST) - start_time

        elapsed_seconds = (datetime.now(IST) - start_time).total_seconds()
        blocks = int(elapsed_seconds // 120)

        if blocks > 0:
            xp_to_add = blocks * 3
            remaining_room = VOICE_XP_LIMIT - current_voice_xp
            xp_to_add = min(xp_to_add, remaining_room)

            if xp_to_add > 0:
                new_total_xp = user["xp"] + xp_to_add
                new_level = new_total_xp // 1000
                new_voice_xp = current_voice_xp + xp_to_add

                self.supabase.table("users").update(
                    {
                        "xp": new_total_xp,
                        "level": new_level,
                        "voice_xp_earned": new_voice_xp,
                        "username": member.name,
                        "guild_name": member.guild.name,
                    }
                ).eq("guild_id", str(member.guild.id)).eq(
                    "user_id", str(member.id)
                ).execute()

                await self._check_and_handle_level_up(member, new_level)

        return timedelta(seconds=elapsed_seconds % 120)

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot or not member.guild:
            return
        key = (member.guild.id, member.id)
        now = datetime.now(IST)

        if not before.channel and after.channel:
            self.voice_sessions[key] = now
            return

        if before.channel and not after.channel:
            start_time = self.voice_sessions.pop(key, None)
            if start_time:
                await self._award_voice_xp(member, start_time)
            return

        if before.channel != after.channel:
            start_time = self.voice_sessions.get(key)
            if start_time:
                await self._award_voice_xp(member, start_time)
            if after.channel:
                self.voice_sessions[key] = now
            else:
                self.voice_sessions.pop(key, None)

    @tasks.loop(seconds=120)
    async def voice_tick_loop(self):
        """Periodically awards XP to users in voice chat and resets their timers."""
        now = datetime.now(IST)
        for (guild_id, user_id), start_time in list(self.voice_sessions.items()):
            guild = self.bot.get_guild(guild_id)
            if not guild:
                self.voice_sessions.pop((guild_id, user_id), None)
                continue

            member = guild.get_member(user_id)
            if not member or not member.voice:
                self.voice_sessions.pop((guild_id, user_id), None)
                continue

            remainder_delta = await self._award_voice_xp(member, start_time)
            self.voice_sessions[(guild_id, user_id)] = now - remainder_delta

    @voice_tick_loop.before_loop
    async def before_voice_tick_loop(self):
        await self.bot.wait_until_ready()

    async def handle_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        def _is_image(att):
            ct = (att.content_type or "").lower()
            return ct.startswith("image/") or att.filename.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".svg")
            )

        is_image_msg = any(_is_image(a) for a in getattr(message, "attachments", []))
        amount = 2 if is_image_msg else 1
        _, level = self.update_user_xp(
            message.guild.id,
            message.author.id,
            amount,
            message.author.name,
            message.guild.name,
        )
        await self._check_and_handle_level_up(message.author, level)

    def get_user(
        self,
        guild_id: int,
        user_id: int,
        username: str = "Unknown",
        guild_name: str = "Unknown Guild",
    ):
        data = (
            self.supabase.table("users")
            .select("*")
            .eq("guild_id", str(guild_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        if data.data:
            return data.data[0]
        else:
            new_user = {
                "guild_id": str(guild_id),
                "guild_name": guild_name,
                "user_id": str(user_id),
                "username": username,
                "xp": 0,
                "level": 0,
                "voice_xp_earned": 0,
            }
            self.supabase.table("users").insert(new_user).execute()
            return new_user

    def update_user_xp(
        self, guild_id: int, user_id: int, amount: int, username: str, guild_name: str
    ):
        """Updates XP for non-voice activities (text, images)."""
        user = self.get_user(guild_id, user_id, username, guild_name)
        new_xp = user["xp"] + amount
        new_level = new_xp // 1000
        self.supabase.table("users").update(
            {
                "xp": new_xp,
                "level": new_level,
                "username": username,
                "guild_name": guild_name,
            }
        ).eq("guild_id", str(guild_id)).eq("user_id", str(user_id)).execute()
        return new_xp, new_level

    def get_notify_channel(self, guild_id: int):
        data = (
            self.supabase.table("level_notify_channel")
            .select("channel_id")
            .eq("guild_id", str(guild_id))
            .execute()
        )
        return data.data[0]["channel_id"] if data.data else None

    def get_user_last_notified_level(self, guild_id: int, user_id: int):
        data = (
            self.supabase.table("last_notified_level")
            .select("level")
            .eq("guild_id", str(guild_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return data.data[0]["level"] if data.data else 0

    # MODIFIED: Accepts names to store in the database.
    def set_user_last_notified_level(
        self, guild_id: int, user_id: int, level: int, guild_name: str, username: str
    ):
        self.supabase.table("last_notified_level").upsert(
            {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "level": level,
                "guild_name": guild_name,
                "username": username,
            }
        ).execute()

    async def check_and_run_auto_reset(self):
        now = datetime.now(IST)
        try:
            configs = self.supabase.table("auto_reset").select("*").execute().data
        except Exception as e:
            dprint(f"[AUTO-RESET] Failed to load configs: {e}")
            return

        for row in configs or []:
            try:
                last_reset, days_cfg = safe_parse_iso(row.get("last_reset")), int(
                    row.get("days", 0)
                )
                if (
                    days_cfg <= 0
                    or (now - last_reset).total_seconds() < days_cfg * 86400
                ):
                    continue

                guild = self.bot.get_guild(int(row.get("guild_id")))
                if not guild:
                    dprint(f"[AUTO-RESET] Guild {row.get('guild_id')} not found.")
                    continue

                dprint(f"♻️ Auto-reset triggered for guild {guild.name} ({guild.id})")

                await self.remove_level_reward_roles(guild)
                self.supabase.table("users").update(
                    {"xp": 0, "level": 0, "voice_xp_earned": 0}
                ).eq("guild_id", str(guild.id)).execute()
                self.supabase.table("last_notified_level").update({"level": 0}).eq(
                    "guild_id", str(guild.id)
                ).execute()
                self.supabase.table("auto_reset").update(
                    {
                        "last_reset": now.isoformat(),
                        "guild_name": guild.name,
                    }  # MODIFIED: Update guild name on reset
                ).eq("guild_id", str(guild.id)).execute()

                dprint(f"✅ Auto-reset complete for guild {guild.name}")
            except Exception as e:
                dprint(f"[AUTO-RESET ERROR] {e}")

    @tasks.loop(hours=1)
    async def reset_loop(self):
        await self.check_and_run_auto_reset()

    @reset_loop.before_loop
    async def before_reset_loop(self):
        await self.bot.wait_until_ready()

    def register_commands(self):
        # MODIFIED: This command now saves the role and guild name.
        @self.bot.tree.command(
            name="l3-setup-level-reward",
            description="Set a role reward for reaching a specific level.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def setup_level_reward(
            interaction: discord.Interaction, level: int, role: discord.Role
        ):
            self.supabase.table("level_roles").upsert(
                {
                    "guild_id": str(interaction.guild.id),
                    "guild_name": interaction.guild.name,
                    "level": level,
                    "role_id": str(role.id),
                    "role_name": role.name,
                }
            ).execute()
            await interaction.response.send_message(
                f"✅ Reward set: Level {level} → {role.mention}", ephemeral=True
            )

        @self.bot.tree.command(
            name="l4-level-reward-show",
            description="Show configured level rewards in this server.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def level_reward_show(interaction: discord.Interaction):
            data = self.get_all_level_roles(interaction.guild.id)
            if not data:
                await interaction.response.send_message(
                    "❌ No level rewards configured yet.", ephemeral=True
                )
                return
            msg = "🏅 **Level Rewards (Highest First):**\n"
            for row in data:
                role = interaction.guild.get_role(int(row["role_id"]))
                # Display stored role name as a fallback
                role_mention = (
                    role.mention
                    if role
                    else f'**{row.get("role_name", "Unknown Role")}** (Deleted)'
                )
                msg += f"Level {row['level']} → {role_mention}\n"
            await interaction.response.send_message(
                msg, ephemeral=True, suppress_embeds=True
            )

        # MODIFIED: This command now saves the channel and guild name.
        @self.bot.tree.command(
            name="l5-notify-level-msg", description="Set a channel for level-up messages."
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def notify_level_msg(
            interaction: discord.Interaction, channel: discord.TextChannel
        ):
            self.supabase.table("level_notify_channel").upsert(
                {
                    "guild_id": str(interaction.guild.id),
                    "guild_name": interaction.guild.name,
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                }
            ).execute()
            await interaction.response.send_message(
                f"✅ Level-up messages will now be sent in {channel.mention}",
                ephemeral=True,
            )

        @self.bot.tree.command(
            name="l1-level", description="Check your or another user's level."
        )
        async def level(
            interaction: discord.Interaction, member: discord.Member = None
        ):
            target = member or interaction.user
            user_data = self.get_user(
                interaction.guild.id, target.id, target.name, interaction.guild.name
            )
            embed = discord.Embed(
                title=f"📊 Level Info for {target.display_name}", color=0x3498DB
            )
            embed.add_field(name="Level", value=user_data.get("level", 0))
            embed.add_field(name="Total XP", value=user_data.get("xp", 0))

            voice_xp = user_data.get("voice_xp_earned", 0)
            embed.add_field(
                name="Voice XP This Period",
                value=f"{voice_xp} / {VOICE_XP_LIMIT}",
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.bot.tree.command(
            name="l2-leaderboard", description="Show the top 10 users on the leaderboard."
        )
        async def leaderboard(interaction: discord.Interaction):
            data = (
                self.supabase.table("users")
                .select("*")
                .eq("guild_id", str(interaction.guild.id))
                .order("xp", desc=True)
                .limit(10)
                .execute()
                .data
            )
            embed = discord.Embed(
                title=f"🏆 Leaderboard - {interaction.guild.name}", color=0xF1C40F
            )
            for i, row in enumerate(data, start=1):
                member = interaction.guild.get_member(int(row["user_id"]))
                name = (
                    member.display_name
                    if member
                    else row.get("username", "Unknown User")
                )
                embed.add_field(
                    name=f"#{i} {name}",
                    value=f"Lvl {row['level']} ({row['xp']} XP)",
                    inline=False,
                )
            await interaction.response.send_message(embed=embed)

        # MODIFIED: This command now saves the guild name.
        @self.bot.tree.command(
            name="l6-set-auto-reset",
            description="Set automatic XP reset schedule (in days).",
        )
        @app_commands.describe(days="Number of days between automatic resets (1-365)")
        @app_commands.checks.has_permissions(administrator=True)
        async def set_auto_reset(interaction: discord.Interaction, days: int):
            if not 1 <= days <= 365:
                await interaction.response.send_message(
                    "❌ Days must be between 1 and 365.", ephemeral=True
                )
                return
            now = datetime.now(IST)
            self.supabase.table("auto_reset").upsert(
                {
                    "guild_id": str(interaction.guild.id),
                    "guild_name": interaction.guild.name,
                    "days": days,
                    "last_reset": now.isoformat(),
                }
            ).execute()
            await interaction.response.send_message(
                f"♻️ Auto-reset has been set for every {days} day{'s' if days > 1 else ''}.\nThe next reset will occur in {days} day{'s' if days > 1 else ''} from now.",
                ephemeral=True,
            )

        @self.bot.tree.command(
            name="l7-show-auto-reset",
            description="Show the current auto-reset configuration for this server.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def show_auto_reset(interaction: discord.Interaction):
            try:
                data = (
                    self.supabase.table("auto_reset")
                    .select("*")
                    .eq("guild_id", str(interaction.guild.id))
                    .execute()
                )
                if not data.data:
                    await interaction.response.send_message(
                        "❌ Auto-reset is not configured for this server.",
                        ephemeral=True,
                    )
                    return
                config, now = data.data[0], datetime.now(IST)
                days = config.get("days", 0)
                last_reset = safe_parse_iso(config.get("last_reset"))
                next_reset = last_reset + timedelta(days=days)
                time_until = next_reset - now
                embed = discord.Embed(
                    title="♻️ Auto-Reset Configuration", color=0x3498DB
                )
                embed.add_field(
                    name="Reset Interval",
                    value=f"{days} day{'s' if days != 1 else ''}",
                    inline=True,
                )
                embed.add_field(
                    name="Last Reset",
                    value=last_reset.strftime("%Y-%m-%d %H:%M IST"),
                    inline=True,
                )
                embed.add_field(
                    name="Next Reset",
                    value=next_reset.strftime("%Y-%m-%d %H:%M IST"),
                    inline=False,
                )
                embed.add_field(
                    name="Time Remaining",
                    value=f"{max(0, time_until.days)} day{'s' if time_until.days != 1 else ''}, {max(0, time_until.seconds // 3600)} hour{'s' if (time_until.seconds // 3600) != 1 else ''}",
                    inline=False,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                dprint(f"[ERROR] Failed to show auto-reset config: {e}")
                await interaction.response.send_message(
                    "❌ Failed to retrieve auto-reset configuration.", ephemeral=True
                )

        @self.bot.tree.command(
            name="l8-stop-auto-reset",
            description="Disable the automatic XP reset for this server.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def stop_auto_reset(interaction: discord.Interaction):
            self.supabase.table("auto_reset").delete().eq(
                "guild_id", str(interaction.guild.id)
            ).execute()
            await interaction.response.send_message(
                "♻️ Automatic XP reset has been disabled.", ephemeral=True
            )

        @self.bot.tree.command(
            name="l9-reset-xp",
            description="MANUALLY reset all XP and remove reward roles.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def reset_xp(interaction: discord.Interaction):
            await interaction.response.defer(thinking=True)
            roles_removed, users_affected = await self.remove_level_reward_roles(
                interaction.guild
            )
            self.supabase.table("users").update(
                {"xp": 0, "level": 0, "voice_xp_earned": 0}
            ).eq("guild_id", str(interaction.guild.id)).execute()
            self.supabase.table("last_notified_level").update({"level": 0}).eq(
                "guild_id", str(interaction.guild.id)
            ).execute()
            await interaction.followup.send(
                f"♻️ **Manual XP Reset Complete!**\n- All user XP, levels, and voice XP have been reset to 0.\n- Removed {roles_removed} reward roles from {users_affected} users."
            )

        @self.bot.tree.command(
            name="l10-upgrade-all-roles",
            description="Manually sync roles for all users based on their current level.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def upgrade_all_roles(interaction: discord.Interaction):
            await interaction.response.defer(thinking=True)
            users_data = (
                self.supabase.table("users")
                .select("*")
                .eq("guild_id", str(interaction.guild.id))
                .execute()
                .data
            )
            if not users_data:
                await interaction.followup.send(
                    "No users found in the database for this server."
                )
                return

            changed_count = 0
            users_scanned = 0
            for user in users_data:
                member = interaction.guild.get_member(int(user["user_id"]))
                if member:
                    users_scanned += 1
                    if await self.upgrade_user_roles(member, user["level"]):
                        changed_count += 1

            await interaction.followup.send(
                f"🔄 Role synchronization complete!\n- Scanned {users_scanned} members.\n- Updated roles for {changed_count} members."
            )
