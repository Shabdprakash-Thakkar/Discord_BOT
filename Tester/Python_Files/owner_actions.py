# Python_Files/owner_actions.py

import discord
from discord import app_commands
from discord.ext import commands
import os
from supabase import create_client, Client
from datetime import datetime, timezone


class OwnerActionsManager:
    """Manages owner-exclusive actions like leaving or banning guilds."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Initialize Supabase client
        sup_url = os.getenv("SUPABASE_URL")
        sup_key = os.getenv("SUPABASE_KEY")
        if not sup_url or not sup_key:
            raise ValueError(
                "Supabase URL or Key not found in .env for OwnerActionsManager."
            )
        self.supabase: Client = create_client(sup_url, sup_key)
        print("🔑 OwnerActionsManager initialized.")

    async def is_guild_banned(self, guild_id: int) -> bool:
        """Check if a guild ID is in the banned_guilds table."""
        try:
            response = (
                self.supabase.table("banned_guilds")
                .select("guild_id")
                .eq("guild_id", str(guild_id))
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            print(f"❌ Error checking if guild {guild_id} is banned: {e}")
            return False

    def register_commands(self):
        """Registers all slash commands for the owner actions feature."""

        @self.bot.tree.command(
            name="g4-leaveserver",
            description="Forces the bot to leave a specific server (Bot Owner only).",
        )
        @app_commands.describe(guild_id="The ID of the server to leave.")
        async def leaveserver(interaction: discord.Interaction, guild_id: str):
            if not await self.bot.is_owner(interaction.user):
                await interaction.response.send_message(
                    "❌ You do not have permission to use this command.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            try:
                target_guild_id = int(guild_id)
                guild = self.bot.get_guild(target_guild_id)

                if not guild:
                    await interaction.followup.send(
                        f"❌ I am not a member of a server with the ID `{guild_id}`.",
                        ephemeral=True,
                    )
                    return

                await guild.leave()
                await interaction.followup.send(
                    f"✅ Successfully left the server: **{guild.name}** (`{guild_id}`).",
                    ephemeral=True,
                )

            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid Guild ID format. Please provide a numeric ID.",
                    ephemeral=True,
                )
            except Exception as e:
                print(f"Error during /leaveserver command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred while trying to leave the server.",
                    ephemeral=True,
                )

        @self.bot.tree.command(
            name="g5-banguild",
            description="Bans a server from using the bot and forces it to leave (Bot Owner only).",
        )
        @app_commands.describe(guild_id="The ID of the server to ban.")
        async def banguild(interaction: discord.Interaction, guild_id: str):
            if not await self.bot.is_owner(interaction.user):
                await interaction.response.send_message(
                    "❌ You do not have permission to use this command.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            try:
                target_guild_id = int(guild_id)

                # Add to Supabase banned_guilds table
                self.supabase.table("banned_guilds").upsert(
                    {
                        "guild_id": str(target_guild_id),
                        "banned_at": datetime.now(timezone.utc).isoformat(),
                        "banned_by": str(interaction.user.id),
                    }
                ).execute()

                # If the bot is in the server, leave it
                guild = self.bot.get_guild(target_guild_id)
                if guild:
                    await guild.leave()
                    await interaction.followup.send(
                        f"✅ Server **{guild.name}** (`{guild_id}`) has been banned and I have left.",
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        f"✅ Server ID `{guild_id}` has been added to the ban list. I was not a member of it.",
                        ephemeral=True,
                    )

            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid Guild ID format. Please provide a numeric ID.",
                    ephemeral=True,
                )
            except Exception as e:
                print(f"Error during /banguild command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred while banning the server.",
                    ephemeral=True,
                )

        @self.bot.tree.command(
            name="g6-unbanguild",
            description="Removes a server from the ban list (Bot Owner only).",
        )
        @app_commands.describe(guild_id="The ID of the server to unban.")
        async def unbanguild(interaction: discord.Interaction, guild_id: str):
            if not await self.bot.is_owner(interaction.user):
                await interaction.response.send_message(
                    "❌ You do not have permission to use this command.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            try:
                # Remove from Supabase banned_guilds table
                result = (
                    self.supabase.table("banned_guilds")
                    .delete()
                    .eq("guild_id", guild_id)
                    .execute()
                )

                if result.data:
                    await interaction.followup.send(
                        f"✅ Server ID `{guild_id}` has been unbanned.", ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Server ID `{guild_id}` was not found in the ban list.",
                        ephemeral=True,
                    )

            except Exception as e:
                print(f"Error during /unbanguild command: {e}")
                await interaction.followup.send(
                    "❌ An unexpected error occurred.", ephemeral=True
                )
