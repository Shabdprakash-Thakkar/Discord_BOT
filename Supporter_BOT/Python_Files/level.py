import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone
import asyncio
import os
from supabase import create_client, Client


class LevelManager:
    def __init__(self, bot: commands.Bot, data_dir: str):
        self.bot = bot
        self.data_dir = data_dir
        self.cooldowns = {}  # {(guild_id, user_id): datetime}

        # Load Supabase
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        print(f"SUPABASE_URL: {url}")
        print(f"SUPABASE_KEY: {key[:5]}...")

        if not url or not key:
            raise ValueError(
                "⚠ Supabase URL or KEY not found! Make sure .env has SUPABASE_URL and SUPABASE_KEY"
            )

        self.supabase: Client = create_client(url, key)

    # -----------------------------
    # Message handler with cooldown, rewards, and notification
    # -----------------------------
    async def handle_message(self, message: discord.Message):
        #print(f"--- [DEBUG] handle_message triggered by {message.author.name} ---")

        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.utcnow()
        key = (guild_id, user_id)

        if key in self.cooldowns and (now - self.cooldowns[key]).total_seconds() < 10:
            return
        self.cooldowns[key] = now

        xp, level = self.update_user_xp(guild_id, user_id, 10)
        last_level = self.get_user_last_notified_level(guild_id, user_id)

        print(
            f"[DEBUG] Level Check: Current Level={level}, Last Notified Level={last_level}"
        )

        if level > last_level:
            print("[DEBUG] Level up condition MET. Proceeding to notify.")

            # Get notification channel
            channel_id = self.get_notify_channel(guild_id)
            print(f"[DEBUG] Fetched notification channel_id from DB: {channel_id}")

            if not channel_id:
                print("[ERROR] No notification channel configured in database!")
                return

            # Try multiple ways to get the channel
            channel = None

            # Method 1: bot.get_channel()
            try:
                channel = self.bot.get_channel(int(channel_id))
                print(f"[DEBUG] Method 1 - bot.get_channel(): {channel}")
            except Exception as e:
                print(f"[ERROR] Method 1 failed: {e}")

            # Method 2: fetch_channel() if get_channel() fails
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(int(channel_id))
                    print(f"[DEBUG] Method 2 - bot.fetch_channel(): {channel}")
                except Exception as e:
                    print(f"[ERROR] Method 2 failed: {e}")

            # Method 3: Get channel through guild
            if not channel:
                try:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        channel = guild.get_channel(int(channel_id))
                        print(f"[DEBUG] Method 3 - guild.get_channel(): {channel}")
                    else:
                        print("[ERROR] Could not get guild object")
                except Exception as e:
                    print(f"[ERROR] Method 3 failed: {e}")

            if not channel:
                print(f"[FINAL ERROR] Could not find channel with ID {channel_id}")
                print("[TROUBLESHOOTING TIPS]:")
                print("1. Check if the channel ID in your database is correct")
                print(
                    "2. Verify the bot has 'View Channel' permission for that channel"
                )
                print("3. Make sure the channel exists and wasn't deleted")
                print("4. Check if the bot is in the same server as the channel")
                return

            # Check bot permissions
            permissions = channel.permissions_for(message.guild.me)
            print(
                f"[DEBUG] Bot permissions in channel: Send Messages: {permissions.send_messages}, View Channel: {permissions.view_channel}"
            )

            if not permissions.send_messages:
                print(
                    "[ERROR] Bot does not have Send Messages permission in the notification channel!"
                )
                return

            # Get reward role if exists
            reward_role_id = self.get_reward_role(guild_id, level)
            print(f"[DEBUG] Reward role ID for level {level}: {reward_role_id}")

            # Handle role reward
            if reward_role_id:
                try:
                    role = message.guild.get_role(int(reward_role_id))
                    print(f"[DEBUG] Found role object: {role}")

                    if role:
                        # Check if user already has the role
                        if role in message.author.roles:
                            print(f"[DEBUG] User already has role {role.name}")
                        else:
                            # Check bot permissions to manage roles
                            if not message.guild.me.guild_permissions.manage_roles:
                                print(
                                    "[ERROR] Bot does not have Manage Roles permission!"
                                )
                            elif role >= message.guild.me.top_role:
                                print(
                                    f"[ERROR] Role {role.name} is higher than bot's highest role!"
                                )
                            else:
                                await message.author.add_roles(role)
                                print(f"[SUCCESS] Added role {role.name} to user")

                        # Send notification with role
                        await channel.send(
                            f"🎉 Congrats {message.author.mention}! You reached **Level {level}**!\n"
                            f"🏅 {message.author.mention} received **{role.mention}**!"
                        )
                        print("[SUCCESS] Role reward message sent.")
                    else:
                        print(
                            f"[ERROR] Role with ID {reward_role_id} not found in guild"
                        )
                        # Send notification without role mention
                        await channel.send(
                            f"🎉 {message.author.mention} reached Level {level}!"
                        )
                        print("[SUCCESS] Level-up message sent (without role).")

                except Exception as e:
                    print(f"[CRITICAL ERROR] Role assignment/notification failed: {e}")
                    # Try to send basic notification
                    try:
                        await channel.send(
                            f"🎉 {message.author.mention} reached Level {level}!"
                        )
                        print("[SUCCESS] Basic level-up message sent after role error.")
                    except Exception as e2:
                        print(f"[CRITICAL ERROR] Even basic message failed: {e2}")
                        return
            else:
                # Normal level-up notification (no role reward)
                try:
                    await channel.send(
                        f"🎉 {message.author.mention} reached Level {level}!"
                    )
                    print("[SUCCESS] Normal level-up message sent.")
                except Exception as e:
                    print(f"[CRITICAL ERROR] Could not send level-up message: {e}")
                    return

            # Update last notified level only if message was sent successfully
            self.set_user_last_notified_level(guild_id, user_id, level)
            print(f"[SUCCESS] Updated last notified level to {level}")
        else:
            print("[DEBUG] Level up condition NOT MET. No notification sent.")

    # -----------------------------
    # Start auto-reset loop
    # -----------------------------
    async def start(self):
        print("🎮 LevelManager started")
        if not self.reset_loop.is_running():
            self.reset_loop.start()

    # -----------------------------
    # Database helpers
    # -----------------------------
    def get_user(self, guild_id: int, user_id: int):
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
            self.supabase.table("users").insert(
                {
                    "guild_id": str(guild_id),
                    "user_id": str(user_id),
                    "xp": 0,
                    "level": 0,
                }
            ).execute()
            return {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "xp": 0,
                "level": 0,
            }

    def update_user_xp(self, guild_id: int, user_id: int, amount: int):
        user = self.get_user(guild_id, user_id)
        new_xp = user["xp"] + amount
        new_level = new_xp // 1000
        self.supabase.table("users").update({"xp": new_xp, "level": new_level}).eq(
            "guild_id", str(guild_id)
        ).eq("user_id", str(user_id)).execute()
        return new_xp, new_level

    def get_reward_role(self, guild_id: int, level: int):
        data = (
            self.supabase.table("level_roles")
            .select("*")
            .eq("guild_id", str(guild_id))
            .eq("level", level)
            .execute()
        )
        return data.data[0]["role_id"] if data.data else None

    def get_notify_channel(self, guild_id: int):
        data = (
            self.supabase.table("level_notify_channel")
            .select("*")
            .eq("guild_id", str(guild_id))
            .execute()
        )
        return data.data[0]["channel_id"] if data.data else None

    def get_user_last_notified_level(self, guild_id: int, user_id: int):
        data = (
            self.supabase.table("last_notified_level")
            .select("*")
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
    # Auto-reset loop
    # -----------------------------
    @tasks.loop(hours=24)
    async def reset_loop(self):
        data = self.supabase.table("auto_reset").select("*").execute()
        now = datetime.utcnow()
        for row in data.data:
            last_reset = datetime.fromisoformat(row["last_reset"])
            days = row["days"]
            if (now - last_reset).days >= days:
                self.supabase.table("users").update({"xp": 0, "level": 0}).eq(
                    "guild_id", row["guild_id"]
                ).execute()
                self.supabase.table("auto_reset").update(
                    {"last_reset": now.isoformat()}
                ).eq("guild_id", row["guild_id"]).execute()
                print(f"♻️ Auto-reset XP in guild {row['guild_id']}")

    @reset_loop.before_loop
    async def before_reset_loop(self):
        await self.bot.wait_until_ready()

    # -----------------------------
    # Slash commands
    # -----------------------------
    def register_commands(self):

        @self.bot.tree.command(
            name="setup-level-reward",
            description="Set a role reward for reaching a specific level",
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
            description="Show configured level rewards in this server",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def level_reward_show(interaction: discord.Interaction):
            data = (
                self.supabase.table("level_roles")
                .select("*")
                .eq("guild_id", str(interaction.guild.id))
                .order("level", desc=False)
                .execute()
            )
            if not data.data:
                await interaction.response.send_message(
                    "❌ No level rewards configured yet.", ephemeral=True
                )
                return

            msg = "🏅 **Level Rewards:**\n"
            for row in data.data:
                role = interaction.guild.get_role(int(row["role_id"]))
                role_name = role.mention if role else f"Role ID {row['role_id']}"
                msg += f"Level {row['level']} → {role_name}\n"

            await interaction.response.send_message(msg, ephemeral=True)

        @self.bot.tree.command(
            name="notify-level-msg",
            description="Set a channel where the bot sends level-up messages",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def notify_level_msg(
            interaction: discord.Interaction, channel: discord.TextChannel
        ):
            self.supabase.table("level_notify_channel").upsert(
                {"guild_id": str(interaction.guild.id), "channel_id": str(channel.id)}
            ).execute()
            await interaction.response.send_message(
                f"✅ Level-up messages will be sent in {channel.mention}",
                ephemeral=True,
            )

        @self.bot.tree.command(
            name="level", description="Check your or another user's level"
        )
        async def level(
            interaction: discord.Interaction, member: discord.Member = None
        ):
            member = member or interaction.user
            user = self.get_user(interaction.guild.id, member.id)
            embed = discord.Embed(
                title=f"📊 Level Info for {member.display_name}",
                color=0x3498DB,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Level", value=user["level"])
            embed.add_field(name="XP", value=user["xp"])
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.bot.tree.command(
            name="leaderboard", description="Show top 10 leaderboard"
        )
        async def leaderboard(interaction: discord.Interaction):
            data = (
                self.supabase.table("users")
                .select("*")
                .eq("guild_id", str(interaction.guild.id))
                .order("xp", desc=True)
                .limit(10)
                .execute()
            )
            embed = discord.Embed(
                title=f"🏆 Leaderboard - {interaction.guild.name}",
                color=0xF1C40F,
                timestamp=datetime.now(timezone.utc),
            )
            for i, row in enumerate(data.data, start=1):
                member = interaction.guild.get_member(int(row["user_id"]))
                name = member.display_name if member else row["user_id"]
                embed.add_field(
                    name=f"#{i} {name}",
                    value=f"Lvl {row['level']} ({row['xp']} XP)",
                    inline=False,
                )
            await interaction.response.send_message(embed=embed)

        @self.bot.tree.command(
            name="set-auto-reset", description="Set automatic XP reset schedule (days)"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def set_auto_reset(interaction: discord.Interaction, days: int):
            if days < 1 or days > 365:
                await interaction.response.send_message(
                    "❌ Days must be between 1 and 365.", ephemeral=True
                )
                return
            now = datetime.utcnow()
            self.supabase.table("auto_reset").upsert(
                {
                    "guild_id": str(interaction.guild.id),
                    "days": days,
                    "last_reset": now.isoformat(),
                }
            ).execute()
            await interaction.response.send_message(
                f"♻️ Auto-reset set every {days} days."
            )

        @self.bot.tree.command(name="reset-xp", description="Manually reset all XP")
        @app_commands.checks.has_permissions(administrator=True)
        async def reset_xp(interaction: discord.Interaction):
            self.supabase.table("users").update({"xp": 0, "level": 0}).eq(
                "guild_id", str(interaction.guild.id)
            ).execute()
            await interaction.response.send_message("♻️ All XP reset successfully.")

        # Add a debug command to help troubleshoot
        @self.bot.tree.command(
            name="debug-level", description="Debug level system configuration"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def debug_level(interaction: discord.Interaction):
            guild_id = interaction.guild.id

            # Check notification channel
            channel_id = self.get_notify_channel(guild_id)
            channel = self.bot.get_channel(int(channel_id)) if channel_id else None

            # Check level rewards
            rewards_data = (
                self.supabase.table("level_roles")
                .select("*")
                .eq("guild_id", str(guild_id))
                .execute()
            )

            embed = discord.Embed(title="🔧 Level System Debug Info", color=0xFF9900)

            # Notification channel info
            if channel_id:
                channel_info = f"Channel ID: {channel_id}\n"
                channel_info += f"Channel Found: {'✅' if channel else '❌'}\n"
                if channel:
                    perms = channel.permissions_for(interaction.guild.me)
                    channel_info += (
                        f"Send Messages: {'✅' if perms.send_messages else '❌'}\n"
                    )
                    channel_info += (
                        f"View Channel: {'✅' if perms.view_channel else '❌'}"
                    )
                embed.add_field(
                    name="Notification Channel", value=channel_info, inline=False
                )
            else:
                embed.add_field(
                    name="Notification Channel", value="❌ Not configured", inline=False
                )

            # Role rewards info
            if rewards_data.data:
                rewards_info = ""
                for reward in rewards_data.data[:5]:  # Show first 5
                    role = interaction.guild.get_role(int(reward["role_id"]))
                    rewards_info += f"Level {reward['level']}: {'✅' if role else '❌'} {reward['role_id']}\n"
                embed.add_field(name="Level Rewards", value=rewards_info, inline=False)
            else:
                embed.add_field(
                    name="Level Rewards", value="❌ None configured", inline=False
                )

            # Bot permissions
            bot_perms = interaction.guild.me.guild_permissions
            perms_info = f"Manage Roles: {'✅' if bot_perms.manage_roles else '❌'}\n"
            perms_info += (
                f"Send Messages: {'✅' if bot_perms.send_messages else '❌'}\n"
            )
            perms_info += f"View Channels: {'✅' if bot_perms.view_channel else '❌'}"
            embed.add_field(name="Bot Permissions", value=perms_info, inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
