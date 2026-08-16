import re
from urllib.parse import urlsplit

import discord
from discord import app_commands
from discord.ext import commands

import common

PLATFORMS = {
    "twitter": {
        "display_name": "Twitter",
        "domains": ["twitter.com", "x.com"],
        "embed_domain": "fixupx.com",
    },
    "instagram": {
        "display_name": "Instagram",
        "domains": ["instagram.com"],
        "embed_domain": "kkinstagram.com",
    },
}
DOMAIN_TO_PLATFORM = {d: k for k, v in PLATFORMS.items() for d in v["domains"]}

DEFAULT_GUILD_SETTINGS = {
    "linkembeds_enabled": False,
    "linkembeds_suppress_original": True,
    "linkembeds_platform_mode": "blacklist",  # blacklist of nothing = all known platforms active
    "linkembeds_platform_list": [],
    "linkembeds_param_mode": "blacklist",
    "linkembeds_param_list": list(common.DEFAULT_TRACKER_PARAMS),
}

URL_PATTERN = re.compile(r'(<)?(https?://[^\s<>]+)(>)?')


def get_guild_config(guild_id: int):
    return {key: common.get_guild_setting(guild_id, key, default) for key, default in DEFAULT_GUILD_SETTINGS.items()}


def _platform_allowed(platform_key: str, config: dict) -> bool:
    if config["linkembeds_platform_mode"] == "whitelist":
        return platform_key in config["linkembeds_platform_list"]
    return platform_key not in config["linkembeds_platform_list"]


def find_platform_links(content: str, config: dict):
    results = []
    seen = set()
    for m in URL_PATTERN.finditer(content):
        if m.group(1) == '<' and m.group(3) == '>':  # respect discord's own embed-suppression syntax
            continue
        url = m.group(2).rstrip(').,!?;:\'"')
        if url in seen:
            continue
        host = (urlsplit(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        platform_key = DOMAIN_TO_PLATFORM.get(host)
        if platform_key is None or not _platform_allowed(platform_key, config):
            continue
        seen.add(url)
        results.append((platform_key, url))
    return results


def build_replacement_links(url: str, platform_key: str, param_mode: str, param_list: list):
    platform = PLATFORMS[platform_key]
    cleaned = common.cleanLinkV2(url, param_list) if param_mode == "whitelist" else common.cleanLink(url, param_list)
    orig_host = urlsplit(url).hostname or ""
    fixed = cleaned.replace(orig_host, platform["embed_domain"], 1)
    return cleaned, fixed


class AddParamModal(discord.ui.Modal, title="Add Tracker Parameter(s)"):
    params = discord.ui.TextInput(
        label="Parameter name(s)",
        placeholder="utm_source, utm_campaign, ...",
        style=discord.TextStyle.short,
        required=True,
        max_length=200,
    )

    def __init__(self, view: "LinkEmbedsView"):
        super().__init__()
        self.view_ref = view

    async def on_submit(self, interaction: discord.Interaction):
        config = get_guild_config(self.view_ref.guild_id)
        plist = list(config["linkembeds_param_list"])
        added = []
        for raw in self.params.value.split(","):
            name = raw.strip()
            if name and name not in plist:
                plist.append(name)
                added.append(name)
        if added:
            common.set_guild_setting(self.view_ref.guild_id, "linkembeds_param_list", plist)
        await self.view_ref.refresh(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"Error adding tracker param(s): {error}")
        try:
            await interaction.response.send_message(content="Failed to add the parameter(s).", ephemeral=True)
        except (discord.Forbidden, discord.HTTPException):
            pass


class LinkEmbedsView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
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
                print(f"Error disabling linkembeds settings panel on timeout: {e}")

    def _config(self):
        return get_guild_config(self.guild_id)

    def build_embed(self) -> discord.Embed:
        config = self._config()
        platform_names = [PLATFORMS[k]["display_name"] for k in config["linkembeds_platform_list"] if k in PLATFORMS]
        embed = discord.Embed(title="Link Embed-Fixer Settings", color=discord.Color.blurple())
        embed.add_field(name="Enabled", value="Yes" if config["linkembeds_enabled"] else "No", inline=True)
        embed.add_field(name="Suppress Original Embed", value="Yes" if config["linkembeds_suppress_original"] else "No", inline=True)
        embed.add_field(name="​", value="​", inline=True)
        embed.add_field(name=f"Platforms ({config['linkembeds_platform_mode']})", value=", ".join(platform_names) if platform_names else "*empty*", inline=False)
        embed.add_field(name=f"Tracker Params ({config['linkembeds_param_mode']})", value=", ".join(f"`{p}`" for p in config["linkembeds_param_list"]) if config["linkembeds_param_list"] else "*empty*", inline=False)
        return embed

    def _update_state(self):
        config = self._config()
        self.toggle_enabled.style = discord.ButtonStyle.success if config["linkembeds_enabled"] else discord.ButtonStyle.secondary
        self.toggle_enabled.label = f"Enabled: {'On' if config['linkembeds_enabled'] else 'Off'}"
        self.toggle_suppress.style = discord.ButtonStyle.success if config["linkembeds_suppress_original"] else discord.ButtonStyle.secondary
        self.toggle_suppress.label = f"Suppress Original: {'On' if config['linkembeds_suppress_original'] else 'Off'}"
        self.toggle_platform_mode.label = f"Platform Mode: {config['linkembeds_platform_mode']}"
        self.toggle_param_mode.label = f"Param Mode: {config['linkembeds_param_mode']}"

        for option in self.platform_select.options:
            option.default = option.value in config["linkembeds_platform_list"]

        param_list = config["linkembeds_param_list"][:25]
        if param_list:
            self.param_select.options = [discord.SelectOption(label=p, value=p) for p in param_list]
            self.param_select.disabled = False
            self.param_select.placeholder = "Select param(s) to remove..."
            self.param_select.max_values = len(param_list)
        else:
            self.param_select.options = [discord.SelectOption(label="(none)", value="__none__")]
            self.param_select.disabled = True
            self.param_select.placeholder = "No tracker params configured"
            self.param_select.max_values = 1

    async def refresh(self, interaction: discord.Interaction):
        self._update_state()
        await common.safe_respond(interaction, embed=self.build_embed(), view=self)

    @discord.ui.button(label="Enabled: Off", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_enabled(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = self._config()
        common.set_guild_setting(self.guild_id, "linkembeds_enabled", not config["linkembeds_enabled"])
        await self.refresh(interaction)

    @discord.ui.button(label="Suppress Original: Off", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_suppress(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = self._config()
        common.set_guild_setting(self.guild_id, "linkembeds_suppress_original", not config["linkembeds_suppress_original"])
        await self.refresh(interaction)

    @discord.ui.button(label="Platform Mode: blacklist", style=discord.ButtonStyle.primary, row=1)
    async def toggle_platform_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = self._config()
        new_mode = "whitelist" if config["linkembeds_platform_mode"] == "blacklist" else "blacklist"
        common.set_guild_setting(self.guild_id, "linkembeds_platform_mode", new_mode)
        await self.refresh(interaction)

    @discord.ui.button(label="Param Mode: blacklist", style=discord.ButtonStyle.primary, row=1)
    async def toggle_param_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = self._config()
        new_mode = "whitelist" if config["linkembeds_param_mode"] == "blacklist" else "blacklist"
        common.set_guild_setting(self.guild_id, "linkembeds_param_mode", new_mode)
        await self.refresh(interaction)

    @discord.ui.select(
        placeholder="Select active platforms...",
        min_values=0,
        max_values=len(PLATFORMS),
        options=[discord.SelectOption(label=v["display_name"], value=k) for k, v in PLATFORMS.items()],
        row=2,
    )
    async def platform_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        common.set_guild_setting(self.guild_id, "linkembeds_platform_list", list(select.values))
        await self.refresh(interaction)

    @discord.ui.select(placeholder="No tracker params configured", min_values=1, max_values=1, options=[discord.SelectOption(label="(none)", value="__none__")], row=3)
    async def param_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if select.values == ["__none__"]:
            await interaction.response.defer()
            return
        config = self._config()
        plist = [p for p in config["linkembeds_param_list"] if p not in select.values]
        common.set_guild_setting(self.guild_id, "linkembeds_param_list", plist)
        await self.refresh(interaction)

    @discord.ui.button(label="Add Parameter", style=discord.ButtonStyle.secondary, row=4)
    async def add_param(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(AddParamModal(self))
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Error opening add-param modal: {e}")


@app_commands.command(name="linkembeds-settings", description="Configure auto embed-fixing for links (Manage Server only)")
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
async def linkembeds_settings_command(interaction: discord.Interaction):
    if not await common.handleCommandAccess(interaction, interaction.user.id, "linkembeds-settings"):
        return
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(content="You need the Manage Server permission to use this command.", ephemeral=True)
        return

    view = LinkEmbedsView(interaction.guild.id, interaction.user.id)
    try:
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
        view.message = await interaction.original_response()
    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"Error opening linkembeds settings panel: {e}")


class LinkEmbeds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot or message.webhook_id is not None:
            return

        config = get_guild_config(message.guild.id)
        if not config["linkembeds_enabled"]:
            return

        matches = find_platform_links(message.content, config)
        if not matches:
            return

        try:
            await message.channel.typing()
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Error showing typing indicator: {e}")

        lines = []
        for platform_key, url in matches:
            cleaned, fixed = build_replacement_links(url, platform_key, config["linkembeds_param_mode"], config["linkembeds_param_list"])
            name = PLATFORMS[platform_key]["display_name"]
            embed_domain = urlsplit(fixed).netloc
            lines.append(f"[{name} link](<{cleaned}>) • [Embed via {embed_domain}]({fixed})")

        try:
            await message.reply("\n".join(lines), allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Error replying with fixed embed links: {e}")

        if config["linkembeds_suppress_original"]:
            perms = message.channel.permissions_for(message.guild.me)
            if perms.manage_messages:
                try:
                    await message.edit(suppress=True)
                except (discord.Forbidden, discord.HTTPException) as e:
                    print(f"Error suppressing original embed: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(LinkEmbeds(bot))
    bot.tree.add_command(linkembeds_settings_command)
