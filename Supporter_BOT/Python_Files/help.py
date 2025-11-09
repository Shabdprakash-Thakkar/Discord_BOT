# Python_Files/help.py

import discord
from discord.ext import commands
from datetime import datetime, timezone


class HelpManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def register_commands(self):
        @self.bot.tree.command(
            name="g1-help", description="Show instructions for moderators and users"
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
                    "`/l1-level` → Check your or another user's level and XP\n"
                    "`/l2-leaderboard` → Show top 10 users\n"
                    "`/l3-setup-level-reward` → Set role reward for a level\n"
                    "`/l4-level-reward-show` → Show configured level rewards\n"
                    "`/l5-notify-level-msg` → Set channel for level-up notifications\n"
                    "`/l10-upgrade-all-roles` → Manually sync roles for all users"
                ),
                inline=False,
            )

            embed.add_field(
                name="♻️ XP Reset System",
                value=(
                    "`/l6-set-auto-reset` → Set automatic XP reset schedule (1-365 days)\n"
                    "`/l7-show-auto-reset` → Show current auto-reset configuration\n"
                    "`/l8-stop-auto-reset` → Disable automatic XP reset\n"
                    "`/l9-reset-xp` → Manually reset all XP and roles"
                ),
                inline=False,
            )

            embed.add_field(
                name="📢 YouTube Notifications",
                value=(
                    "`/y1-find-youtube-channel-id` → Find a channel's ID from its username\n"
                    "`/y2-setup-youtube-notifications` → Set up notifications for a channel\n"
                    "`/y3-disable-youtube-notifications` → Stop notifications for a channel"
                ),
                inline=False,
            )

            embed.add_field(
                name="🚫📝 No-Text Channels",
                value=(
                    "`/n1-setup-no-text` → Configure a media-only channel\n"
                    "`/n2-remove-no-text` → Remove no-text restrictions\n"
                    "`/n3-bypass-no-text` → Allow a role to bypass restrictions\n"
                    "`/n4-show-bypass-roles` → Show roles that can bypass\n"
                    "`/n5-remove-bypass-role` → Remove a role's bypass ability"
                ),
                inline=False,
            )

            embed.add_field(
                name="🔗 Link Restrictions",
                value=(
                    "`/n6-no-discord-link` → Delete Discord invite links (prevent server promotion)\n"
                    "`/n7-no-links` → Delete ALL links silently (most restrictive)\n"
                    "`/n8-remove-no-discord-link` → Remove Discord link restriction\n"
                    "`/n9-remove-no-links` → Remove no-links restriction"
                ),
                inline=False,
            )

            embed.add_field(
                name="⏰ Time & Date Channels",
                value=(
                    "`/t1-setup-time-channels` → Set up date, India, and Japan time channels"
                ),
                inline=False,
            )

            embed.add_field(
                name="⚙️ Configuration",
                value=(
                    "`/g1-help` → Show this help message\n"
                    "`/g2-show-config` → Show current bot configuration for your server"
                ),
                inline=False,
            )

            # Conditionally add the owner commands section
            if await self.bot.is_owner(interaction.user):
                embed.add_field(
                    name="👑 Owner Commands",
                    value=(
                        "`/g3-serverlist` → Lists all servers the bot is in\n"
                        "`/g4-leaveserver` → Force the bot to leave a server\n"
                        "`/g5-banguild` → Ban a server from using the bot\n"
                        "`/g6-unbanguild` → Unban a server"
                    ),
                    inline=False,
                )

            embed.set_footer(
                text=f"Server: {interaction.guild.name}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
