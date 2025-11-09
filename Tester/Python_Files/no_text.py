from discord import app_commands
import discord
import json
import os
import asyncio
import threading
import re
from supabase import create_client
from dotenv import load_dotenv


class NoTextManager:
    def __init__(self, bot, data_dir):
        self.bot = bot
        self.data_dir = data_dir
        self.notext_file = os.path.join(data_dir, "no_text.json")
        self.lock = threading.Lock()
        self.notext_channels = self._load_json_safe({})

        # URL pattern to detect links - improved pattern
        self.url_pattern = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|"
            r"(?:www\.)?[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}",
            re.IGNORECASE,
        )

        # Discord link pattern - matches discord.gg, discord.com/invite, discordapp.com/invite
        self.discord_link_pattern = re.compile(
            r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9]+",
            re.IGNORECASE,
        )

        # Supabase client
        dotenv_path = os.path.join(self.data_dir, ".env")
        load_dotenv(dotenv_path)
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL or Key not found in .env")
        self.supabase = create_client(url, key)

    # -----------------------------
    # JSON helpers (only for no_text.json)
    # -----------------------------
    def _save_json_safe(self, data):
        with self.lock:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.notext_file, "w") as f:
                json.dump(data, f, indent=2)

    def _load_json_safe(self, default):
        try:
            if os.path.exists(self.notext_file):
                with open(self.notext_file, "r") as f:
                    return json.load(f)
            return default
        except Exception as e:
            print(f"❌ Failed to load {self.notext_file}: {e}. Creating default file.")
            self._save_json_safe(default)
            return default

    async def start(self):
        print("🚫📝 No-Text Manager initialized")

    def get_config(self, guild_id):
        return self.notext_channels.get(str(guild_id))

    # -----------------------------
    # Bypass role check
    # -----------------------------
    def is_bypass(self, member: discord.Member):
        # Admins and owners always bypass
        if member.guild_permissions.administrator or member == member.guild.owner:
            return True

        # Check Supabase bypass_roles table
        try:
            data = (
                self.supabase.table("bypass_roles")
                .select("*")
                .eq("guild_id", str(member.guild.id))
                .execute()
            )
            if data.data:
                author_role_ids = [role.id for role in member.roles]
                for row in data.data:
                    if int(row["role_id"]) in author_role_ids:
                        return True
        except Exception as e:
            print(f"❌ Error checking bypass roles: {e}")

        return False

    # -----------------------------
    # Supabase helpers for new features
    # -----------------------------
    def _is_channel_in_no_links(self, guild_id, channel_id):
        """Check if channel is configured for no-links"""
        try:
            data = (
                self.supabase.table("no_links_channels")
                .select("*")
                .eq("guild_id", str(guild_id))
                .eq("channel_id", str(channel_id))
                .execute()
            )
            return len(data.data) > 0
        except Exception as e:
            print(f"❌ Error checking no_links_channels: {e}")
            return False

    def _is_channel_in_no_discord_links(self, guild_id, channel_id):
        """Check if channel is configured for no-discord-links"""
        try:
            data = (
                self.supabase.table("no_discord_links_channels")
                .select("*")
                .eq("guild_id", str(guild_id))
                .eq("channel_id", str(channel_id))
                .execute()
            )
            return len(data.data) > 0
        except Exception as e:
            print(f"❌ Error checking no_discord_links_channels: {e}")
            return False

    # -----------------------------
    # Core message handler
    # -----------------------------
    async def handle_message(self, message):
        if message.author.bot or not message.guild:
            return

        # Bypass roles
        if self.is_bypass(message.author):
            return

        guild_id = str(message.guild.id)
        channel_id = message.channel.id

        # Check no-links channels first (most restrictive - deletes ALL links)
        if self._is_channel_in_no_links(guild_id, channel_id):
            if self._has_any_links(message):
                try:
                    await message.delete()
                except discord.Forbidden:
                    print(f"❌ No permission to delete message in channel {channel_id}")
                except discord.NotFound:
                    print(f"❌ Message already deleted in channel {channel_id}")
                except Exception as e:
                    print(f"❌ Error deleting message with links: {e}")
                return

        # Check no-discord-links channels (deletes Discord invite links)
        # This will delete the message if it contains ANY Discord invite link
        # Even if the message also contains YouTube or other links
        if self._is_channel_in_no_discord_links(guild_id, channel_id):
            if self._has_discord_links(message):
                try:
                    await message.delete()
                except discord.Forbidden:
                    print(f"❌ No permission to delete message in channel {channel_id}")
                except discord.NotFound:
                    print(f"❌ Message already deleted in channel {channel_id}")
                except Exception as e:
                    print(f"❌ Error deleting message with Discord links: {e}")
                return

        # Original no-text channel logic (JSON-based)
        if guild_id not in self.notext_channels:
            return

        config = self.notext_channels[guild_id]
        if channel_id not in config["channels"]:
            return

        # Allow messages with attachments, links, or embeds
        if self._has_media_or_links(message):
            return

        # Delete plain text messages
        if message.content.strip():  # only if message is not empty
            try:
                await message.delete()
                redirect_id = config["redirects"].get(str(channel_id))
                if redirect_id:
                    # Check if redirect channel exists
                    redirect_channel = self.bot.get_channel(redirect_id)
                    if redirect_channel:
                        warning_msg = await message.channel.send(
                            f"🚫📝 {message.author.mention}, this channel is for **media and links only**! "
                            f"Plain text messages are not allowed. Please use {redirect_channel.mention} for text-only messages.\n\n"
                            f"**Allowed:** Images, Videos, YouTube/Instagram/Other links\n"
                            f"**Not Allowed:** Plain text only"
                        )
                    else:
                        # Fallback if redirect channel doesn't exist
                        warning_msg = await message.channel.send(
                            f"🚫📝 {message.author.mention}, this channel is for **media and links only**! "
                            f"Plain text messages are not allowed.\n\n"
                            f"**Allowed:** Images, Videos, YouTube/Instagram/Other links\n"
                            f"**Not Allowed:** Plain text only"
                        )

                    async def delete_warning():
                        await asyncio.sleep(30)
                        try:
                            await warning_msg.delete()
                        except Exception as e:
                            print(f"❌ Could not delete warning message: {e}")

                    self.bot.loop.create_task(delete_warning())
            except discord.Forbidden:
                print(f"❌ No permission to delete message in channel {channel_id}")
            except discord.NotFound:
                print(f"❌ Message already deleted in channel {channel_id}")
            except Exception as e:
                print(f"❌ Error handling no-text message in guild {guild_id}: {e}")

    # -----------------------------
    # Helper to detect media/links
    # -----------------------------
    def _has_media_or_links(self, message):
        return bool(
            message.attachments
            or self.url_pattern.search(message.content)
            or message.embeds
        )

    def _has_any_links(self, message):
        """Check if message contains any links"""
        return bool(self.url_pattern.search(message.content))

    def _has_discord_links(self, message):
        """Check if message contains Discord invite links"""
        return bool(self.discord_link_pattern.search(message.content))

    # -----------------------------
    # Slash commands
    # -----------------------------
    async def setup_channel(self, interaction, notext_channel, redirect_channel):
        guild_id = str(interaction.guild_id)
        if guild_id not in self.notext_channels:
            self.notext_channels[guild_id] = {"channels": [], "redirects": {}}
        if notext_channel.id not in self.notext_channels[guild_id]["channels"]:
            self.notext_channels[guild_id]["channels"].append(notext_channel.id)
        self.notext_channels[guild_id]["redirects"][
            str(notext_channel.id)
        ] = redirect_channel.id
        self._save_json_safe(self.notext_channels)
        await interaction.followup.send(
            f"✅ **No-Text channel configured!**\n🚫📝 {notext_channel.mention}\n💬 {redirect_channel.mention}",
            ephemeral=True,
        )

    async def remove_channel(self, interaction, channel):
        guild_id = str(interaction.guild_id)
        if guild_id not in self.notext_channels:
            await interaction.followup.send(
                "❌ No no-text channels configured.", ephemeral=True
            )
            return
        if channel.id in self.notext_channels[guild_id]["channels"]:
            self.notext_channels[guild_id]["channels"].remove(channel.id)
            self.notext_channels[guild_id]["redirects"].pop(str(channel.id), None)
            self._save_json_safe(self.notext_channels)
            await interaction.followup.send(
                f"✅ Removed no-text restriction from {channel.mention}", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ {channel.mention} was not configured as no-text.", ephemeral=True
            )

    async def setup_no_discord_links(self, interaction, channel):
        guild_id = str(interaction.guild_id)
        guild_name = interaction.guild.name
        channel_name = channel.name

        try:
            # Check if already exists
            existing = (
                self.supabase.table("no_discord_links_channels")
                .select("*")
                .eq("guild_id", guild_id)
                .eq("channel_id", str(channel.id))
                .execute()
            )

            if existing.data:
                await interaction.followup.send(
                    f"❌ {channel.mention} is already configured for no Discord links.",
                    ephemeral=True,
                )
                return

            # Insert new configuration
            self.supabase.table("no_discord_links_channels").insert(
                {
                    "guild_id": guild_id,
                    "guild_name": guild_name,
                    "channel_id": str(channel.id),
                    "channel_name": channel_name,
                }
            ).execute()

            await interaction.followup.send(
                f"✅ **No Discord links configured!**\n🚫🔗 {channel.mention}\n\n"
                f"Messages with Discord server/channel invite links will be deleted silently to prevent promotion.\n\n"
                f"**Example - DELETED:**\n"
                f"• `Check youtube.com/video and join discord.gg/abc123` ❌\n"
                f"• `discord.gg/abc123` ❌\n"
                f"• `Join my server discord.com/invite/xyz` ❌\n\n"
                f"**Example - ALLOWED:**\n"
                f"• `Check this video: youtube.com/watch?v=123` ✅\n"
                f"• `Follow me: instagram.com/user` ✅",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Error setting up no-discord-links: {e}")
            await interaction.followup.send(
                "❌ Error configuring no Discord links. Check bot permissions.",
                ephemeral=True,
            )

    async def setup_no_links(self, interaction, channel):
        guild_id = str(interaction.guild_id)
        guild_name = interaction.guild.name
        channel_name = channel.name

        try:
            # Check if already exists
            existing = (
                self.supabase.table("no_links_channels")
                .select("*")
                .eq("guild_id", guild_id)
                .eq("channel_id", str(channel.id))
                .execute()
            )

            if existing.data:
                await interaction.followup.send(
                    f"❌ {channel.mention} is already configured for no links.",
                    ephemeral=True,
                )
                return

            # Insert new configuration
            self.supabase.table("no_links_channels").insert(
                {
                    "guild_id": guild_id,
                    "guild_name": guild_name,
                    "channel_id": str(channel.id),
                    "channel_name": channel_name,
                }
            ).execute()

            await interaction.followup.send(
                f"✅ **No links configured!**\n🚫🔗 {channel.mention}\n\n"
                f"ALL links will be deleted silently (most restrictive).\n\n"
                f"**Everything DELETED:**\n"
                f"• Discord links ❌\n"
                f"• YouTube links ❌\n"
                f"• Instagram links ❌\n"
                f"• Any website links ❌",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Error setting up no-links: {e}")
            await interaction.followup.send(
                "❌ Error configuring no links. Check bot permissions.",
                ephemeral=True,
            )

    async def remove_no_discord_links(self, interaction, channel):
        guild_id = str(interaction.guild_id)

        try:
            result = (
                self.supabase.table("no_discord_links_channels")
                .delete()
                .eq("guild_id", guild_id)
                .eq("channel_id", str(channel.id))
                .execute()
            )

            if result.data:
                await interaction.followup.send(
                    f"✅ Removed no-discord-links restriction from {channel.mention}",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"❌ {channel.mention} was not configured for no-discord-links.",
                    ephemeral=True,
                )
        except Exception as e:
            print(f"❌ Error removing no-discord-links: {e}")
            await interaction.followup.send(
                "❌ Error removing restriction.", ephemeral=True
            )

    async def remove_no_links(self, interaction, channel):
        guild_id = str(interaction.guild_id)

        try:
            result = (
                self.supabase.table("no_links_channels")
                .delete()
                .eq("guild_id", guild_id)
                .eq("channel_id", str(channel.id))
                .execute()
            )

            if result.data:
                await interaction.followup.send(
                    f"✅ Removed no-links restriction from {channel.mention}",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"❌ {channel.mention} was not configured for no-links.",
                    ephemeral=True,
                )
        except Exception as e:
            print(f"❌ Error removing no-links: {e}")
            await interaction.followup.send(
                "❌ Error removing restriction.", ephemeral=True
            )

    def register_commands(self):
        # Command to allow a certain role to bypass no-text
        @self.bot.tree.command(
            name="n3-bypass-no-text",
            description="Allow a role to bypass no-text restriction",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def bypass_no_text(interaction: discord.Interaction, role: discord.Role):
            try:
                guild_name = interaction.guild.name
                role_name = role.name
                self.supabase.table("bypass_roles").upsert(
                    {
                        "guild_id": str(interaction.guild.id),
                        "guild_name": guild_name,
                        "role_id": str(role.id),
                        "role_name": role_name,
                    }
                ).execute()
                await interaction.response.send_message(
                    f"✅ {role.mention} can now bypass no-text channels.",
                    ephemeral=True,
                )
            except Exception as e:
                print(f"❌ Error adding bypass role: {e}")
                await interaction.response.send_message(
                    "❌ Error configuring bypass role. Check bot permissions.",
                    ephemeral=True,
                )

        # Command to show bypass roles
        @self.bot.tree.command(
            name="n4-show-bypass-roles",
            description="Show all roles that can bypass no-text restrictions",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def show_bypass_roles(interaction: discord.Interaction):
            try:
                data = (
                    self.supabase.table("bypass_roles")
                    .select("*")
                    .eq("guild_id", str(interaction.guild.id))
                    .execute()
                )

                if not data.data:
                    await interaction.response.send_message(
                        "❌ No bypass roles configured.", ephemeral=True
                    )
                    return

                bypass_info = "🚫📝 **No-Text Bypass Roles:**\n"
                for row in data.data:
                    role = interaction.guild.get_role(int(row["role_id"]))
                    role_name = (
                        role.mention if role else f"Role ID {row['role_id']} (Deleted)"
                    )
                    bypass_info += f"• {role_name}\n"

                await interaction.response.send_message(bypass_info, ephemeral=True)

            except Exception as e:
                print(f"❌ Error fetching bypass roles: {e}")
                await interaction.response.send_message(
                    "❌ Error fetching bypass roles.", ephemeral=True
                )

        # Command to remove bypass role
        @self.bot.tree.command(
            name="n5-remove-bypass-role",
            description="Remove a role's ability to bypass no-text restrictions",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def remove_bypass_role(
            interaction: discord.Interaction, role: discord.Role
        ):
            try:
                result = (
                    self.supabase.table("bypass_roles")
                    .delete()
                    .eq("guild_id", str(interaction.guild.id))
                    .eq("role_id", str(role.id))
                    .execute()
                )

                if result.data:
                    await interaction.response.send_message(
                        f"✅ {role.mention} can no longer bypass no-text channels.",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"❌ {role.mention} was not configured as a bypass role.",
                        ephemeral=True,
                    )

            except Exception as e:
                print(f"❌ Error removing bypass role: {e}")
                await interaction.response.send_message(
                    "❌ Error removing bypass role.", ephemeral=True
                )

        # New command: n6-no-discord-link
        @self.bot.tree.command(
            name="n6-no-discord-link",
            description="Delete Discord invite links silently (prevents server promotion)",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def no_discord_link(
            interaction: discord.Interaction, channel: discord.TextChannel
        ):
            await interaction.response.defer(ephemeral=True)
            await self.setup_no_discord_links(interaction, channel)

        # New command: n7-no-links
        @self.bot.tree.command(
            name="n7-no-links",
            description="Set channel to delete ALL links silently (most restrictive)",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def no_links(
            interaction: discord.Interaction, channel: discord.TextChannel
        ):
            await interaction.response.defer(ephemeral=True)
            await self.setup_no_links(interaction, channel)

        # Command to remove no-discord-links restriction
        @self.bot.tree.command(
            name="n8-remove-no-discord-link",
            description="Remove no-discord-links restriction from a channel",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def remove_no_discord_link(
            interaction: discord.Interaction, channel: discord.TextChannel
        ):
            await interaction.response.defer(ephemeral=True)
            await self.remove_no_discord_links(interaction, channel)

        # Command to remove no-links restriction
        @self.bot.tree.command(
            name="n9-remove-no-links",
            description="Remove no-links restriction from a channel",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def remove_no_links(
            interaction: discord.Interaction, channel: discord.TextChannel
        ):
            await interaction.response.defer(ephemeral=True)
            await self.remove_no_links(interaction, channel)
