print("Loading modules...")
import discord
from discord.ext import commands
from discord import app_commands
import json
import os

from common import ensure_datastores, config, handleCommandAccess, setCooldown

intents = discord.Intents.default()
intents.message_content = True  # required for the link embed-fixer to read message.content - also must be enabled in the Discord Developer Portal (Bot > Privileged Gateway Intents)
ensure_datastores()

if not os.path.exists("config.json"):
    with open("config.json", "w") as f:
        json.dump({"token": "your token here", "poweruserid": "your user id here (for certain commands)"}, f, indent=4)
    input("Created config.json with default values. Please edit the file with your bot token and user id, then press enter to continue...")

cogs = ["linkcleaner", "linkembeds", "tupperboxwatch", "guide"]

print("Loading additional commands...")


class alcBot(commands.Bot):
    async def setup_hook(self):
        for item in cogs:
            try:
                await self.load_extension(f"cogs.{item}")
                print(f"Loaded cog {item}")
            except Exception as e:
                print(f"Failed to load cog {item}: {e}")


bot = alcBot(command_prefix='!', intents=intents)
bot.tree.allowed_installs = app_commands.AppInstallationType(guild=True, user=True)
bot.tree.allowed_contexts = app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        print("Syncing commands...")
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error syncing commands: {e}')
    print("Bot is up and running!")


@bot.tree.command(name="ping", description="Ping the bot")
async def ping(interaction: discord.Interaction):
    if not await handleCommandAccess(interaction, interaction.user.id):
        return
    await interaction.response.defer()
    await interaction.edit_original_response(content=f"Pong! [{round(bot.latency * 1000)}ms]")


bot.run(config["token"])
