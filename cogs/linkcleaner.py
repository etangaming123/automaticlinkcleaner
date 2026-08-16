import discord
from discord.ext import commands
from discord import app_commands

from common import handleCommandAccess, setCooldown, cleanLink, cleanLinkV2, cleanTiktokLink, DEFAULT_TRACKER_PARAMS, get_guild_setting, set_guild_setting, get_user_setting, set_user_setting, safe_respond
from cogs.linkembeds import URL_PATTERN, get_guild_config as get_linkembeds_config, find_platform_links

AUTO_CLEAN_DEFAULT = True

DEFAULT_USER_SETTINGS = {
    "linkcleaner_extra_blacklist": [],
    "linkcleaner_extra_whitelist": [],
    "linkcleaner_apply_to_autoclean": False,
}


def get_user_config(user_id: int):
    return {key: get_user_setting(user_id, key, default) for key, default in DEFAULT_USER_SETTINGS.items()}


class AddExtraParamModal(discord.ui.Modal):
    params = discord.ui.TextInput(
        label="Parameter name(s)",
        placeholder="utm_source, utm_campaign, ...",
        style=discord.TextStyle.short,
        required=True,
        max_length=200,
    )

    def __init__(self, view: "LinkCleanerSettingsView", setting_key: str, title: str):
        super().__init__(title=title)
        self.view_ref = view
        self.setting_key = setting_key

    async def on_submit(self, interaction: discord.Interaction):
        config = get_user_config(self.view_ref.user_id)
        plist = list(config[self.setting_key])
        added = []
        for raw in self.params.value.split(","):
            name = raw.strip()
            if name and name not in plist:
                plist.append(name)
                added.append(name)
        if added:
            set_user_setting(self.view_ref.user_id, self.setting_key, plist)
        await self.view_ref.refresh(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"Error adding link-cleaner param(s): {error}")
        try:
            await interaction.response.send_message(content="Failed to add the parameter(s).", ephemeral=True)
        except (discord.Forbidden, discord.HTTPException):
            pass


class LinkCleanerSettingsView(discord.ui.View):
    def __init__(self, user_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.message: discord.Message | None = None
        self._update_state()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(content="This isn't your settings panel.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(content="Settings panel timed out. Run the command again to make more changes.", embed=self.build_embed(), view=self)
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"Error disabling link-cleaner settings panel on timeout: {e}")

    def _config(self):
        return get_user_config(self.user_id)

    def build_embed(self) -> discord.Embed:
        config = self._config()
        embed = discord.Embed(title="Your Personal Link-Cleaner Settings", color=discord.Color.blurple())
        embed.add_field(name="Apply to Auto-Clean", value="Yes" if config["linkcleaner_apply_to_autoclean"] else "No", inline=False)
        embed.add_field(name="Extra Blacklist Params (used in /clean-link)", value=", ".join(f"`{p}`" for p in config["linkcleaner_extra_blacklist"]) if config["linkcleaner_extra_blacklist"] else "*empty*", inline=False)
        embed.add_field(name="Extra Whitelist Params (used in /clean-link-v2)", value=", ".join(f"`{p}`" for p in config["linkcleaner_extra_whitelist"]) if config["linkcleaner_extra_whitelist"] else "*empty*", inline=False)
        return embed

    def _update_state(self):
        config = self._config()
        self.toggle_apply_autoclean.style = discord.ButtonStyle.success if config["linkcleaner_apply_to_autoclean"] else discord.ButtonStyle.secondary
        self.toggle_apply_autoclean.label = f"Apply to Auto-Clean: {'On' if config['linkcleaner_apply_to_autoclean'] else 'Off'}"

        blacklist = config["linkcleaner_extra_blacklist"][:25]
        if blacklist:
            self.blacklist_select.options = [discord.SelectOption(label=p, value=p) for p in blacklist]
            self.blacklist_select.disabled = False
            self.blacklist_select.placeholder = "Select blacklist param(s) to remove..."
            self.blacklist_select.max_values = len(blacklist)
        else:
            self.blacklist_select.options = [discord.SelectOption(label="(none)", value="__none__")]
            self.blacklist_select.disabled = True
            self.blacklist_select.placeholder = "No extra blacklist params configured"
            self.blacklist_select.max_values = 1

        whitelist = config["linkcleaner_extra_whitelist"][:25]
        if whitelist:
            self.whitelist_select.options = [discord.SelectOption(label=p, value=p) for p in whitelist]
            self.whitelist_select.disabled = False
            self.whitelist_select.placeholder = "Select whitelist param(s) to remove..."
            self.whitelist_select.max_values = len(whitelist)
        else:
            self.whitelist_select.options = [discord.SelectOption(label="(none)", value="__none__")]
            self.whitelist_select.disabled = True
            self.whitelist_select.placeholder = "No extra whitelist params configured"
            self.whitelist_select.max_values = 1

    async def refresh(self, interaction: discord.Interaction):
        self._update_state()
        await safe_respond(interaction, embed=self.build_embed(), view=self)

    @discord.ui.button(label="Apply to Auto-Clean: Off", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_apply_autoclean(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = self._config()
        set_user_setting(self.user_id, "linkcleaner_apply_to_autoclean", not config["linkcleaner_apply_to_autoclean"])
        await self.refresh(interaction)

    @discord.ui.select(placeholder="No extra blacklist params configured", min_values=1, max_values=1, options=[discord.SelectOption(label="(none)", value="__none__")], row=1)
    async def blacklist_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if select.values == ["__none__"]:
            await interaction.response.defer()
            return
        config = self._config()
        plist = [p for p in config["linkcleaner_extra_blacklist"] if p not in select.values]
        set_user_setting(self.user_id, "linkcleaner_extra_blacklist", plist)
        await self.refresh(interaction)

    @discord.ui.select(placeholder="No extra whitelist params configured", min_values=1, max_values=1, options=[discord.SelectOption(label="(none)", value="__none__")], row=2)
    async def whitelist_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if select.values == ["__none__"]:
            await interaction.response.defer()
            return
        config = self._config()
        plist = [p for p in config["linkcleaner_extra_whitelist"] if p not in select.values]
        set_user_setting(self.user_id, "linkcleaner_extra_whitelist", plist)
        await self.refresh(interaction)

    @discord.ui.button(label="Add Blacklist Param", style=discord.ButtonStyle.secondary, row=3)
    async def add_blacklist_param(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(AddExtraParamModal(self, "linkcleaner_extra_blacklist", "Add Extra Blacklist Parameter(s)"))
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Error opening add-blacklist-param modal: {e}")

    @discord.ui.button(label="Add Whitelist Param", style=discord.ButtonStyle.secondary, row=3)
    async def add_whitelist_param(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(AddExtraParamModal(self, "linkcleaner_extra_whitelist", "Add Extra Whitelist Parameter(s)"))
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Error opening add-whitelist-param modal: {e}")


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

    @app_commands.command(name="clean-link-settings", description="Manage your personal extra link-cleaner parameters (applies across all servers)")
    async def clean_link_settings(self, interaction: discord.Interaction):
        if not await handleCommandAccess(interaction, interaction.user.id, "clean-link-settings"):
            return
        view = LinkCleanerSettingsView(interaction.user.id)
        try:
            await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
            view.message = await interaction.original_response()
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Error opening link-cleaner settings panel: {e}")

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
            toremove = list(DEFAULT_TRACKER_PARAMS)
            if get_user_setting(message.author.id, "linkcleaner_apply_to_autoclean", False):
                toremove.extend(get_user_setting(message.author.id, "linkcleaner_extra_blacklist", []))
            cleaned = cleanLink(url, toremove)
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
        toremove.extend(get_user_setting(interaction.user.id, "linkcleaner_extra_blacklist", []))
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
        whitelist_list.extend(get_user_setting(interaction.user.id, "linkcleaner_extra_whitelist", []))
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
