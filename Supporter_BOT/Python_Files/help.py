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
                description="Complete list of available commands organized by category",
                color=0x00FF00,
                timestamp=datetime.now(timezone.utc),
            )

            # Leveling System Commands
            embed.add_field(
                name="📊 Leveling System",
                value=(
                    "`/setup-level-reward` → Set role reward for reaching a specific level\n"
                    "`/level-reward-show` → Show configured level rewards\n"
                    "`/notify-level-msg` → Set channel for level-up notifications\n"
                    "`/level` → Check your or another user's level and XP\n"
                    "`/leaderboard` → Show top 10 users on the server leaderboard\n"
                    "`/upgrade-all-roles` → Manually sync roles for all users based on current levels"
                ),
                inline=False,
            )

            # XP Reset Commands
            embed.add_field(
                name="♻️ XP Reset System",
                value=(
                    "`/set-auto-reset` → Set automatic XP reset schedule (1-365 days)\n"
                    "`/show-auto-reset` → Show current auto-reset configuration\n"
                    "`/stop-auto-reset` → Disable automatic XP reset\n"
                    "`/reset-xp` → Manually reset all XP and remove reward roles"
                ),
                inline=False,
            )

            # No-Text Channel Commands
            embed.add_field(
                name="🚫📝 No-Text Channels",
                value=(
                    "`/setup-no-text` → Configure a media-only channel\n"
                    "`/remove-no-text` → Remove no-text restrictions from a channel\n"
                    "`/bypass-no-text` → Allow a role to bypass no-text restrictions\n"
                    "`/show-bypass-roles` → Show roles that can bypass no-text channels\n"
                    "`/remove-bypass-role` → Remove a role's bypass ability"
                ),
                inline=False,
            )

            # Time & Date Commands
            embed.add_field(
                name="⏰ Time & Date Channels",
                value=(
                    "`/setup-time-channels` → Set up date, India time, and Japan time channels"
                ),
                inline=False,
            )

            # Configuration Commands
            embed.add_field(
                name="⚙️ Configuration",
                value=(
                    "`/show-config` → Show current bot configuration for your server\n"
                    "`/help` → Show this help message"
                ),
                inline=False,
            )

            # Additional Information
            embed.add_field(
                name="📝 How XP Works",
                value=(
                    "• **Text Messages**: 1 XP per message\n"
                    "• **Image Messages**: 2 XP per message\n"
                    "• **Voice Chat**: 3 XP per 120 seconds\n"
                    "• **Level Up**: Every 1000 XP = 1 Level"
                ),
                inline=False,
            )

            embed.add_field(
                name="🎯 No-Text Channels",
                value=(
                    "**Allowed**: Images, Videos, Links (YouTube, Instagram, etc.)\n"
                    "**Not Allowed**: Plain text-only messages\n"
                    "**Bypass**: Administrators and configured roles can send text"
                ),
                inline=False,
            )

            embed.set_footer(
                text=f"Server: {interaction.guild.name} • Bot made with ❤️",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
