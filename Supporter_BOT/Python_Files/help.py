# Python_Files/help.py

import discord
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

            embed.add_field(
                name="📊 Leveling System",
                value=(
                    "`/setup-level-reward` → Set role reward for a level\n"
                    "`/level-reward-show` → Show configured level rewards\n"
                    "`/notify-level-msg` → Set channel for level-up notifications\n"
                    "`/level` → Check your or another user's level and XP\n"
                    "`/leaderboard` → Show top 10 users\n"
                    "`/upgrade-all-roles` → Manually sync roles for all users"
                ),
                inline=False,
            )

            embed.add_field(
                name="♻️ XP Reset System",
                value=(
                    "`/set-auto-reset` → Set automatic XP reset schedule (1-365 days)\n"
                    "`/show-auto-reset` → Show current auto-reset configuration\n"
                    "`/stop-auto-reset` → Disable automatic XP reset\n"
                    "`/reset-xp` → Manually reset all XP and roles"
                ),
                inline=False,
            )
            
            embed.add_field(
                name="📢 YouTube Notifications",
                value=(
                    "`/find-youtube-channel-id` → Find a channel's ID from its username\n"
                    "`/setup-youtube-notifications` → Set up notifications for a channel\n"
                    "`/disable-youtube-notifications` → Stop notifications for a channel"
                ),
                inline=False,
            )

            embed.add_field(
                name="🚫📝 No-Text Channels",
                value=(
                    "`/setup-no-text` → Configure a media-only channel\n"
                    "`/remove-no-text` → Remove no-text restrictions\n"
                    "`/bypass-no-text` → Allow a role to bypass restrictions\n"
                    "`/show-bypass-roles` → Show roles that can bypass\n"
                    "`/remove-bypass-role` → Remove a role's bypass ability"
                ),
                inline=False,
            )

            embed.add_field(
                name="⏰ Time & Date Channels",
                value=(
                    "`/setup-time-channels` → Set up date, India, and Japan time channels"
                ),
                inline=False,
            )

            embed.add_field(
                name="⚙️ Configuration",
                value=(
                    "`/show-config` → Show current bot configuration for your server\n"
                    "`/help` → Show this help message"
                ),
                inline=False,
            )

            # Conditionally add the owner commands section
            if await self.bot.is_owner(interaction.user):
                embed.add_field(
                    name="👑 Owner Commands",
                    value=(
                        "`/serverlist` → Lists all servers the bot is in\n"
                        "`/leaveserver` → Force the bot to leave a server\n"
                        "`/banguild` → Ban a server from using the bot\n"
                        "`/unbanguild` → Unban a server"
                    ),
                    inline=False
                )

            embed.set_footer(
                text=f"Server: {interaction.guild.name}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)