import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone


class HelpManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def register_commands(self):
        @self.bot.tree.command(
            name="help", description="Show instructions for moderators and users"
        )
        async def help_command(interaction: discord.Interaction):
            embed = discord.Embed(
                title="🤖 Supporter Bot Help",
                color=0x00FF00,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(
                name="Leveling Commands",
                value=(
                    "/setup-level-reward → Set role for level reward\n"
                    "/level-reward-show → View level rewards\n"
                    "/notify-level-msg → Set channel for level-up notifications\n"
                    "/level → Check your or another user's level\n"
                    "/leaderboard → Show top 10 leaderboard"
                ),
                inline=False,
            )
            embed.add_field(
                name="No-Text Commands",
                value=(
                    "/setup-no-text → Configure a media-only channel\n"
                    "/remove-no-text → Remove no-text restrictions\n"
                    "/bypass-no-text → Allow role to bypass no-text"
                ),
                inline=False,
            )
            embed.add_field(
                name="Other Commands",
                value=(
                    "/set-auto-reset → Set XP auto-reset schedule\n"
                    "/reset-xp → Reset all XP manually"
                ),
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
