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
# Debug toggle
# -----------------------------
DEBUG = True  # Change to True if you want detailed print statements for debugging


def dprint(*args, **kwargs):
    if DEBUG:
        print(f"[{datetime.now(IST).isoformat()}]", *args, **kwargs)


class LevelManager:
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.data_dir = data_dir
        self.cooldowns = {}  # {(guild_id, user_id): datetime}

        # Load Supabase
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        dprint(f"SUPABASE_URL: {url}")
        dprint(f"SUPABASE_KEY: {key[:5]}...")

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

    # -----------------------------
    # ROLE MANAGEMENT LOGIC
    # -----------------------------
    def get_all_level_roles(self, guild_id: int):
        """Get all level roles configured for a guild, ordered by level."""
        try:
            data = (
                self.supabase.table("level_roles")
                .select("*")
                .eq("guild_id", str(guild_id))
                .order("level", desc=True)  # Order from highest level to lowest
                .execute()
            )
            return data.data if data.data else []
        except Exception as e:
            dprint(f"[ERROR] Failed to get level roles: {e}")
            return []

    async def upgrade_user_roles(self, member: discord.Member, new_level: int):
        """
        Handles role updates on level-up.
        Removes all old level roles and adds the single, highest-level role the user qualifies for.
        """
        try:
            guild_id = member.guild.id
            all_level_roles_data = self.get_all_level_roles(guild_id)

            if not all_level_roles_data:
                dprint(f"[DEBUG] No level roles configured for guild {guild_id}")
                return None, False

            # Find the highest role the user should have
            target_role_id = None
            for role_data in all_level_roles_data:
                if new_level >= role_data["level"]:
                    target_role_id = int(role_data["role_id"])
                    break  # Since it's ordered high to low, the first match is the correct one

            # Get a list of all possible level role IDs for this guild
            all_level_role_ids = {int(r["role_id"]) for r in all_level_roles_data}

            roles_to_remove = []
            user_has_target_role = False

            # Check current user roles
            for role in member.roles:
                if role.id in all_level_role_ids:
                    if role.id == target_role_id:
                        user_has_target_role = True
                    else:
                        roles_to_remove.append(role)

            roles_changed = False
            # Remove old level roles
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Level role upgrade")
                dprint(
                    f"[SUCCESS] Removed roles from {member.display_name}: {[r.name for r in roles_to_remove]}"
                )
                roles_changed = True

            # Add the new role if they don't have it
            target_role_obj = None
            if target_role_id and not user_has_target_role:
                target_role_obj = member.guild.get_role(target_role_id)
                if target_role_obj:
                    await member.add_roles(
                        target_role_obj, reason=f"Reached Level {new_level}"
                    )
                    dprint(
                        f"[SUCCESS] Added role {target_role_obj.name} to {member.display_name}"
                    )
                    roles_changed = True  # This also counts as a change
                else:
                    dprint(
                        f"[ERROR] Target role with ID {target_role_id} not found in guild."
                    )

            elif user_has_target_role:
                target_role_obj = member.guild.get_role(target_role_id)

            return target_role_obj, roles_changed

        except discord.Forbidden:
            dprint(
                f"[ERROR] Bot lacks permission to manage roles in guild {member.guild.id}"
            )
            return None, False
        except Exception as e:
            dprint(
                f"[CRITICAL ERROR] Failed to upgrade user roles for {member.display_name}: {e}"
            )
            return None, False

    async def remove_level_reward_roles(self, guild: discord.Guild):
        """Remove all configured level reward roles from all members in the guild."""
        if not guild:
            return 0, 0

        level_roles_data = self.get_all_level_roles(guild.id)
        if not level_roles_data:
            dprint(f"ℹ️ No level reward roles configured for guild {guild.id}")
            return 0, 0

        reward_role_ids = {int(row["role_id"]) for row in level_roles_data}
        roles_removed_count = 0
        users_affected_count = 0

        dprint(f"🔄 Starting role removal for guild {guild.name}...")
        for member in guild.members:
            if member.bot:
                continue

            roles_to_remove = [
                role for role in member.roles if role.id in reward_role_ids
            ]

            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="XP Reset")
                    roles_removed_count += len(roles_to_remove)
                    users_affected_count += 1
                    dprint(
                        f"[SUCCESS] Removed {len(roles_to_remove)} roles from {member.display_name}"
                    )
                except discord.Forbidden:
                    print(
                        f"❌ No permission to remove roles from {member.display_name}"
                    )
                except Exception as e:
                    print(f"❌ Error removing roles from {member.display_name}: {e}")

        print(
            f"✅ Role removal complete for guild {guild.name}: {roles_removed_count} roles removed from {users_affected_count} users."
        )
        return roles_removed_count, users_affected_count

    # -----------------------------
    # EVENT HANDLERS
    # -----------------------------
    async def handle_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.now(timezone.utc)
        key = (guild_id, user_id)

        # Cooldown check
        if key in self.cooldowns and (now - self.cooldowns[key]).total_seconds() < 10:
            return
        self.cooldowns[key] = now

        # Update XP and check for level up
        xp, level = self.update_user_xp(guild_id, user_id, 10, message.author.name)
        last_level = self.get_user_last_notified_level(guild_id, user_id)

        if level > last_level:
            dprint(f"[LEVEL UP] {message.author.name} reached Level {level}")

            # Get notification channel
            channel_id = self.get_notify_channel(guild_id)
            if not channel_id:
                dprint(f"[ERROR] No notification channel set for guild {guild_id}")
                return

            channel = self.bot.get_channel(int(channel_id))
            if (
                not channel
                or not channel.permissions_for(message.guild.me).send_messages
            ):
                dprint(
                    f"[ERROR] Cannot find or send messages in notification channel {channel_id}"
                )
                return

            # Perform role upgrade
            new_role, roles_changed = await self.upgrade_user_roles(
                message.author, level
            )

            # Send notification
            if new_role:
                await channel.send(
                    f"🎉 Congrats {message.author.mention}! You reached **Level {level}** and earned the **{new_role.mention}** role!"
                )
            else:
                await channel.send(
                    f"🎉 Congrats {message.author.mention}! You reached **Level {level}**!"
                )

            # Update notified level in DB
            self.set_user_last_notified_level(guild_id, user_id, level)

    # -----------------------------
    # DATABASE HELPERS
    # -----------------------------
    def get_user(self, guild_id: int, user_id: int, username: str = "Unknown"):
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
            # Create user if not exist
            new_user = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "username": username,
                "xp": 0,
                "level": 0,
            }
            self.supabase.table("users").insert(new_user).execute()
            return new_user

    def update_user_xp(self, guild_id: int, user_id: int, amount: int, username: str):
        user = self.get_user(guild_id, user_id, username)
        new_xp = user["xp"] + amount
        new_level = new_xp // 1000  # 1000 XP per level
        self.supabase.table("users").update(
            {"xp": new_xp, "level": new_level, "username": username}
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

    def set_user_last_notified_level(self, guild_id: int, user_id: int, level: int):
        self.supabase.table("last_notified_level").upsert(
            {"guild_id": str(guild_id), "user_id": str(user_id), "level": level}
        ).execute()

    # -----------------------------
    # AUTO-RESET TASK
    # -----------------------------
    @tasks.loop(hours=24)
    async def reset_loop(self):
        now = datetime.now(IST)
        configs = self.supabase.table("auto_reset").select("*").execute().data

        for row in configs:
            last_reset = datetime.fromisoformat(row["last_reset"])
            if (now - last_reset).days >= row["days"]:
                guild = self.bot.get_guild(int(row["guild_id"]))
                if not guild:
                    print(f"Auto-reset failed: Guild {row['guild_id']} not found.")
                    continue

                print(f"♻️ Auto-reset triggered for guild {guild.name} ({guild.id})")

                # 1. Remove reward roles
                await self.remove_level_reward_roles(guild)

                # 2. Reset database tables
                self.supabase.table("users").update({"xp": 0, "level": 0}).eq(
                    "guild_id", row["guild_id"]
                ).execute()
                self.supabase.table("last_notified_level").update({"level": 0}).eq(
                    "guild_id", row["guild_id"]
                ).execute()

                # 3. Update last reset time
                self.supabase.table("auto_reset").update(
                    {"last_reset": now.isoformat()}
                ).eq("guild_id", row["guild_id"]).execute()
                print(f"✅ Auto-reset complete for guild {guild.name}")

    @reset_loop.before_loop
    async def before_reset_loop(self):
        await self.bot.wait_until_ready()

    # -----------------------------
    # SLASH COMMANDS
    # -----------------------------
    def register_commands(self):

        @self.bot.tree.command(
            name="setup-level-reward",
            description="Set a role reward for reaching a specific level.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def setup_level_reward(
            interaction: discord.Interaction, level: int, role: discord.Role
        ):
            self.supabase.table("level_roles").upsert(
                {
                    "guild_id": str(interaction.guild.id),
                    "level": level,
                    "role_id": str(role.id),
                }
            ).execute()
            await interaction.response.send_message(
                f"✅ Reward set: Level {level} → {role.mention}", ephemeral=True
            )

        @self.bot.tree.command(
            name="level-reward-show",
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
                role_name = (
                    role.mention if role else f"Unknown Role (ID: {row['role_id']})"
                )
                msg += f"Level {row['level']} → {role_name}\n"
            await interaction.response.send_message(msg, ephemeral=True)

        @self.bot.tree.command(
            name="notify-level-msg", description="Set a channel for level-up messages."
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def notify_level_msg(
            interaction: discord.Interaction, channel: discord.TextChannel
        ):
            self.supabase.table("level_notify_channel").upsert(
                {"guild_id": str(interaction.guild.id), "channel_id": str(channel.id)}
            ).execute()
            await interaction.response.send_message(
                f"✅ Level-up messages will now be sent in {channel.mention}",
                ephemeral=True,
            )

        @self.bot.tree.command(
            name="level", description="Check your or another user's level."
        )
        async def level(
            interaction: discord.Interaction, member: discord.Member = None
        ):
            target_member = member or interaction.user
            user_data = self.get_user(
                interaction.guild.id, target_member.id, target_member.name
            )
            embed = discord.Embed(
                title=f"📊 Level Info for {target_member.display_name}", color=0x3498DB
            )
            embed.add_field(name="Level", value=user_data["level"])
            embed.add_field(name="XP", value=user_data["xp"])
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.bot.tree.command(
            name="leaderboard", description="Show the top 10 users on the leaderboard."
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

        @self.bot.tree.command(
            name="set-auto-reset",
            description="Set automatic XP reset schedule (in days).",
        )
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
                    "days": days,
                    "last_reset": now.isoformat(),
                }
            ).execute()
            await interaction.response.send_message(
                f"♻️ Auto-reset has been set for every {days} days."
            )

        @self.bot.tree.command(
            name="stop-auto-reset",
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
            name="reset-xp",
            description="MANUALLY reset all XP and remove reward roles.",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def reset_xp(interaction: discord.Interaction):
            await interaction.response.defer(thinking=True)

            # 1. Remove roles
            roles_removed, users_affected = await self.remove_level_reward_roles(
                interaction.guild
            )

            # 2. Reset DB
            self.supabase.table("users").update({"xp": 0, "level": 0}).eq(
                "guild_id", str(interaction.guild.id)
            ).execute()
            self.supabase.table("last_notified_level").update({"level": 0}).eq(
                "guild_id", str(interaction.guild.id)
            ).execute()

            await interaction.followup.send(
                f"♻️ **Manual XP Reset Complete!**\n"
                f"- All user XP and levels have been reset to 0.\n"
                f"- Removed {roles_removed} reward roles from {users_affected} users."
            )

        @self.bot.tree.command(
            name="upgrade-all-roles",
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

            users_changed_count = 0
            for user in users_data:
                member = interaction.guild.get_member(int(user["user_id"]))
                if member:
                    _, roles_changed = await self.upgrade_user_roles(
                        member, user["level"]
                    )
                    if roles_changed:
                        users_changed_count += 1

            await interaction.followup.send(
                f"🔄 Role synchronization complete! {users_changed_count} users had their roles updated."
            )
