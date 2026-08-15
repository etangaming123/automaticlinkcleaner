import discord
from discord import app_commands
from discord.ext import commands

from common import handleCommandAccess

GUIDE_TEXT = (
    "**Link Cleaner**\n"
    "`/auto-clean-links <on/off>` - Toggle automatic tracker removal from links posted in this server.\n"
    "`/clean-link` and `/clean-link-v2` - Manually clean a link. No permission needed, works anywhere.\n\n"
    "**Link Embed Fixer**\n"
    "`/linkembeds-settings` - Opens a settings panel to toggle embed-fixing, choose platforms, and manage tracker parameters.\n\n"
    "Server configuration commands require the **Manage Server** permission."
)


class GuideCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="guide", description="Learn how to configure the bot's settings")
    async def guide(self, interaction: discord.Interaction):
        if not await handleCommandAccess(interaction, interaction.user.id, "guide"):
            return

        embed = discord.Embed(title="Bot Configuration Guide", description=GUIDE_TEXT, color=discord.Color.blurple())

        if interaction.guild is not None:
            can_configure = interaction.user.guild_permissions.manage_guild
            embed.add_field(
                name="Your Access",
                value=(
                    "✅ You have permission to configure the bot in this server."
                    if can_configure
                    else "❌ You do **not** have permission to configure the bot in this server. (Missing: Manage Server)"
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name="Your Access",
                value="Run this command in a server to see whether you can configure the bot there.",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GuideCog(bot))
