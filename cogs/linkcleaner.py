import discord
from discord.ext import commands
from discord import app_commands

from common import handleCommandAccess, setCooldown, cleanLink, cleanLinkV2, cleanTiktokLink, DEFAULT_TRACKER_PARAMS, get_guild_setting, set_guild_setting
from cogs.linkembeds import URL_PATTERN, get_guild_config as get_linkembeds_config, find_platform_links

AUTO_CLEAN_DEFAULT = True


class linkCleanerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="auto-clean-links", description="Turn automatic link tracker removal on or off for this server (Manage Server only)")
    @app_commands.describe(enabled="Whether the bot should automatically strip trackers from links sent in this server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def auto_clean_links(self, interaction: discord.Interaction, enabled: bool):
        if not await handleCommandAccess(interaction, interaction.user.id, "auto-clean-links"):
            return
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(content="You need the Manage Server permission to use this command.", ephemeral=True)
            return
        set_guild_setting(interaction.guild.id, "linkcleaner_auto_enabled", enabled)
        await interaction.response.send_message(content=f"Automatic link tracker removal is now {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot or message.webhook_id is not None:
            return
        if not get_guild_setting(message.guild.id, "linkcleaner_auto_enabled", AUTO_CLEAN_DEFAULT):
            return

        embeds_config = get_linkembeds_config(message.guild.id)
        special_urls = {url for _, url in find_platform_links(message.content, embeds_config)}  # links a "special embed" cog already handles

        cleaned_links = []
        seen = set()
        for m in URL_PATTERN.finditer(message.content):
            if m.group(1) == '<' and m.group(3) == '>':  # respect discord's own embed-suppression syntax
                continue
            url = m.group(2).rstrip(').,!?;:\'"')
            if url in seen or url in special_urls:
                continue
            seen.add(url)
            cleaned = cleanLink(url, list(DEFAULT_TRACKER_PARAMS))
            if cleaned != url:
                cleaned_links.append(cleaned)

        if not cleaned_links:
            return

        try:
            await message.reply(
                "\n".join(f"Removed link trackers: {link}" for link in cleaned_links),
                allowed_mentions=discord.AllowedMentions.none(),
                mention_author=False,
            )
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Error replying with cleaned links: {e}")

        perms = message.channel.permissions_for(message.guild.me)
        if perms.manage_messages:  # only suppress if server settings actually grant us the permission
            try:
                await message.edit(suppress=True)
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"Error suppressing original embed: {e}")

    @app_commands.command(name="clean-link", description="Remove stinky link trackers.")
    @app_commands.describe(link="The link you want to clean [Valid url with http:// or https://]", additional="Any additional parameters to remove, separated by commas (optional).")
    async def clean_link(self, interaction: discord.Interaction, link: str, additional: str = None):
        if not await handleCommandAccess(interaction, interaction.user.id, "cleanlink"):
            return
        await interaction.response.defer()
        if not (link.startswith("http://") or link.startswith("https://")):
            await interaction.edit_original_response(content="Please enter a valid URL that starts with http:// or https://")
            return
        if len(link) > 2000:
            await interaction.edit_original_response(content="There's no way that's a real link. [Please enter a valid URL under 2000 characters.]")
            return
        toremove = list(DEFAULT_TRACKER_PARAMS)
        if additional:
            toremove.extend(additional.split(","))
        cleaned_link = cleanLink(link, toremove)

        if "tiktok.com" in cleaned_link and "vt.tiktok.com" not in cleaned_link:  # Fuck you tiktok, we're removing ALL your parameters
            cleaned_link = cleanLink(link, "*")

        if "www.tiktok.com/t/" in cleaned_link:  # these are the same as vt links but like you can't get the original video url from a simple http request
            code = cleaned_link.split('www.tiktok.com/t/')[1].split('/')[0]  # so we grab the share code
            cleaned_link = f"https://vt.tiktok.com/{code}"  # and convert it into something we can grab the original video url from

        if "https://vt.tiktok" in cleaned_link[:17]:  # wow tiktok that's slack
            await interaction.edit_original_response(content=f"vt.tiktok links redirect you to a URL with trackers! Please wait as we get the real URL and clean that...")
            try:
                await interaction.edit_original_response(content=f"{cleanTiktokLink(cleaned_link)}")
                return
            except Exception as e:
                print(f"Error cleaning link: {e}")
                await interaction.edit_original_response(content="Something went wrong whilst trying to remove trackers. (Check your URL!)")
                return
        await interaction.edit_original_response(content=f"Removed stinky link trackers: {cleaned_link}")

    @app_commands.command(name="clean-link-v2", description="Remove even more link trackers. May break some links.")
    @app_commands.describe(link="The link you want to clean [Valid url with http:// or https://]", whitelist="Any parameters you want to keep, separated by commas (optional). (overrides default whitelist)")
    async def clean_link_v2(self, interaction: discord.Interaction, link: str, whitelist: str = None):
        if not await handleCommandAccess(interaction, interaction.user.id, "cleanlink"):
            return
        await interaction.response.defer()
        setCooldown(interaction.user.id, "cleanlink", 5)
        if not (link.startswith("http://") or link.startswith("https://")):
            await interaction.edit_original_response(content="Please enter a valid URL that starts with http:// or https://")
            return
        if len(link) > 2000:
            await interaction.edit_original_response(content="There's no way that's a real link. [Please enter a valid URL under 2000 characters.]")
            return
        defaultwhitelist = []
        whitelist_list = whitelist.split(",") if whitelist else defaultwhitelist
        if "steamcommunity.com" in link:
            whitelist_list.append("id")  # id for sharedfiles
        if "youtube.com" in link or "youtu.be" in link:
            whitelist_list.append("v")  # video id
            whitelist_list.append("t")  # timestamp
            whitelist_list.append("list")  # playlist

        cleaned_link = cleanLinkV2(link, whitelist_list)

        if "www.tiktok.com/t/" in cleaned_link:
            code = cleaned_link.split('www.tiktok.com/t/')[1].split('/')[0]
            cleaned_link = f"https://vt.tiktok.com/{code}"

        if "https://vt.tiktok" in cleaned_link[:17]:
            await interaction.edit_original_response(content=f"vt.tiktok links redirect you to a URL with trackers! Please wait as we get the real URL and clean that...")
            try:
                await interaction.edit_original_response(content=f"{cleanTiktokLink(cleaned_link)}")
                return
            except Exception as e:
                print(f"Error cleaning link: {e}")
                await interaction.edit_original_response(content="Something went wrong whilst trying to remove trackers. (Check your URL!)")
                return

        await interaction.edit_original_response(content=f"Removed a BUNCH of query parameters: {cleaned_link}")


async def setup(bot: commands.Bot):
    await bot.add_cog(linkCleanerCog(bot))
