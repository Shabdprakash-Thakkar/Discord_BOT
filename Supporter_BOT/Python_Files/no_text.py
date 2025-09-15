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

        # Supabase client
        dotenv_path = os.path.join(self.data_dir, ".env")
        load_dotenv(dotenv_path)
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL or Key not found in .env")
        self.supabase = create_client(url, key)

    # -----------------------------
    # JSON helpers
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
    # Core message handler
    # -----------------------------
    async def handle_message(self, message):
        if message.author.bot or not message.guild:
            return

        # Bypass roles
        if self.is_bypass(message.author):
            return

        guild_id = str(message.guild.id)
        if guild_id not in self.notext_channels:
            return

        config = self.notext_channels[guild_id]
        if message.channel.id not in config["channels"]:
            return

        # Allow messages with attachments, links, or embeds
        if self._has_media_or_links(message):
            return

        # Delete plain text messages
        if message.content.strip():  # only if message is not empty
            try:
                await message.delete()
                redirect_id = config["redirects"].get(str(message.channel.id))
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
                print(
                    f"❌ No permission to delete message in channel {message.channel.id}"
                )
            except discord.NotFound:
                print(f"❌ Message already deleted in channel {message.channel.id}")
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

    def register_commands(self):
        # Command to allow a certain role to bypass no-text
        @self.bot.tree.command(
            name="bypass-no-text",
            description="Allow a role to bypass no-text restriction",
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def bypass_no_text(interaction: discord.Interaction, role: discord.Role):
            try:
                self.supabase.table("bypass_roles").upsert(
                    {"guild_id": str(interaction.guild.id), "role_id": str(role.id)}
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
            name="show-bypass-roles",
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
            name="remove-bypass-role",
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
