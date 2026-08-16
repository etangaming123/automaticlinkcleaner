import discord
from discord.ext import commands
from discord import app_commands

from common import handleCommandAccess, get_guild_setting, set_guild_setting, try_match_webhook_message, mark_proxy_candidate_deleted

TUPPERBOX_WAIT_DEFAULT = False


class TupperboxWatchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="tupperbox-compat", description="Wait for a Tupperbox-proxied webhook message before cleaning/embedding links (Manage Server only)")
    @app_commands.describe(enabled="Whether to wait for a matching webhook message before acting on a link, and reply to it instead")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def tupperbox_compat(self, interaction: discord.Interaction, enabled: bool):
        if not await handleCommandAccess(interaction, interaction.user.id, "tupperbox-compat"):
            return
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(content="You need the Manage Server permission to use this command.", ephemeral=True)
            return
        set_guild_setting(interaction.guild.id, "tupperbox_wait_enabled", enabled)
        await interaction.response.send_message(content=f"Tupperbox compatibility mode is now {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.webhook_id is None:
            return
        if not get_guild_setting(message.guild.id, "tupperbox_wait_enabled", TUPPERBOX_WAIT_DEFAULT):
            return
        try_match_webhook_message(message)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
            return
        mark_proxy_candidate_deleted(message.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(TupperboxWatchCog(bot))
