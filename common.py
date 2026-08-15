import json
import os
import time
import requests

# more options
enablecooldowns = True

# no touchy! unless you want more datastores
userdatastores = ["usersettings"]
otherdatastores = ["bannedusers", "guildsettings"]

datastores = []
for item in userdatastores:
    datastores.append(item)
for item in otherdatastores:
    datastores.append(item)

cooldowns = {}


def ensure_datastores():  # creates new datastore files if they don't exist
    for item in datastores:
        if not os.path.exists(f"{item}.json"):
            with open(f"{item}.json", "w") as file:
                json.dump({}, file)
            print(f"Created new file [{item}.json]")


def saveData(store: str, newdata: dict):
    try:
        backup = loadData(store)
        with open(f"{store}_backup.json", "w") as file:  # write a back up just in case
            json.dump(backup, file, indent=4)
        with open(f"{store}.json", "w") as file:
            json.dump(newdata, file, indent=4)
        os.remove(f"{store}_backup.json")
        return True

    except Exception as e:
        print(f"Error saving data, restoring backup: {e}")
        with open(f"{store}.json", "w") as file:
            json.dump(backup, file, indent=4)
        return False


def loadData(store: str):
    try:
        with open(f"{store}.json", "r") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}

    except Exception as e:
        print(f"Error loading data: {e}")
        return ""  # commands are written to handle empty string as error, so we return that instead of None or {}


config = loadData("config")
poweruserid = config.get("poweruserid") if config != "" else None

# in-memory caches, loaded once on startup. refresh explicitly after writes -
# do NOT call loadData() straight from a hot path (e.g. on_message), see getBannedUsers/getGuildSettings
bannedusers = loadData("bannedusers")
guildsettings = loadData("guildsettings")


def getBannedUsers(refresh: bool = False):
    global bannedusers
    if refresh:
        bannedusers = loadData("bannedusers")
    return bannedusers


def getGuildSettings(refresh: bool = False):
    global guildsettings
    if refresh:
        guildsettings = loadData("guildsettings")
    return guildsettings


def removeFormatting(string: str):  # Remove Discord formatting from a string (using backslashes to escape formatting characters)
    formatting_chars = ['*', '_', '~', '`', '>', '|']
    for char in formatting_chars:
        string = string.replace(char, f'\{char}')
    return string


def formatUsername(user):  # Fancy formatting for usernames // displayname (@username)
    if user.display_name is None:
        return f"{removeFormatting(user.name)}"
    else:
        return f"{user.display_name} (@{removeFormatting(user.name)})"


def checkIfCooldown(userid: int, commandname: str):
    if not enablecooldowns:  # always return -1 (no cooldown) if cooldowns are disabled
        return -1
    if poweruserid is not None and userid == int(poweruserid):
        return -1  # no cooldown for power user
    if userid not in cooldowns:
        cooldowns[userid] = {}
    if commandname not in cooldowns[userid]:
        return -1
    if time.time() < cooldowns[userid][commandname]:
        return round(cooldowns[userid][commandname])  # return timestamp of when they can use command again
    else:
        del cooldowns[userid][commandname]  # remove cooldown since it's expired
        return -1


def setCooldown(userid: int, commandname: str, cooldowntime: int):
    if poweruserid is not None and userid == int(poweruserid):
        return  # no cooldown for power user
    if userid not in cooldowns:
        cooldowns[userid] = {}
    cooldowns[userid][commandname] = round(time.time() + cooldowntime)


def getUserHash(userid: int):
    import hashlib
    return hashlib.sha1(str(userid).encode("utf-8")).hexdigest()


def checkIfBanned(userid: int):
    banned = getBannedUsers()
    ban_key = getUserHash(userid)
    if ban_key in banned:
        if banned[ban_key]["length"] == "ncmd":
            return banned[ban_key]
        if banned[ban_key]["length"] is not None and time.time() > banned[ban_key]["length"]:
            del banned[ban_key]
            saveData("bannedusers", banned)
            getBannedUsers(refresh=True)
            return False
        return banned[ban_key]
    return False


async def handleCommandAccess(interaction, userid: int, commandname: str = None):
    banned = checkIfBanned(userid)
    if banned:
        ban_length = banned.get("length")
        reason = banned.get("reason") or "No reason provided."
        if ban_length == "ncmd":
            ban_until = "the next command you try to use."
            currentbanned = getBannedUsers(refresh=True)
            if getUserHash(userid) in currentbanned:
                del currentbanned[getUserHash(userid)]
                saveData("bannedusers", currentbanned)
                getBannedUsers(refresh=True)
        elif ban_length is not None:
            ban_until = f"<t:{round(ban_length)}:F>"
        else:
            ban_until = "the bot gets shut down, apparently."
        await interaction.response.send_message(content=f"You are banned from using this bot until {ban_until}.\n\n{reason}", ephemeral=True)
        return False

    if commandname is not None:
        cooldown = checkIfCooldown(userid, commandname)
        if cooldown != -1:
            await interaction.response.send_message(content=f"Slow down! You can use this command again <t:{cooldown}:R>", ephemeral=True)
            return False

    return True


def get_user_setting(user_id: int, key: str, default=None):
    settings = loadData("usersettings")
    if settings == "" or not isinstance(settings, dict):
        return default
    return settings.get(str(user_id), {}).get(key, default)


def set_user_setting(user_id: int, key: str, value) -> bool:
    settings = loadData("usersettings")
    if settings == "" or not isinstance(settings, dict):
        settings = {}
    settings.setdefault(str(user_id), {})[key] = value
    return saveData("usersettings", settings)


# per-guild settings mirror the per-user helpers above, but read/write the
# in-memory guildsettings cache instead of hitting disk - this is read on
# every single message (on_message listener), so it must never loadData() directly
def get_guild_setting(guild_id: int, key: str, default=None):
    settings = getGuildSettings()
    if settings == "" or not isinstance(settings, dict):
        return default
    return settings.get(str(guild_id), {}).get(key, default)


def set_guild_setting(guild_id: int, key: str, value) -> bool:
    settings = getGuildSettings()
    if settings == "" or not isinstance(settings, dict):
        settings = {}
    settings.setdefault(str(guild_id), {})[key] = value
    saved = saveData("guildsettings", settings)
    if saved:
        getGuildSettings(refresh=True)
    return saved


DEFAULT_TRACKER_PARAMS = ["igsh", "si", "fbclid", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "is", "mibextid", "gclid", "dclid", "is_from_webapp", "sender_device", "_t", "_r", "t", "igsi"]


def cleanLink(url, toremove):
    import re
    if toremove == "*":  # if toremove is *, remove all parameters from the link
        if "?" not in url:
            return url.split("&")[0]  # Tiktok is known to use & instead of ? for their parameters sometimes, so we check for both and split by the one that exists
        return url.split("?")[0]
    cleaned_link = url
    for item in toremove:
        cleaned_link = re.sub(r'([&?])' + re.escape(item) + r'=[^&]*', '', cleaned_link)
    cleaned_link = re.sub(r'[?&]+$', '', cleaned_link)  # remove trailing ? or &
    for item in toremove:
        cleaned_link = re.sub(r'([&])' + re.escape(item) + r'=[^&]*', '', cleaned_link)  # run again, this time removing & params
    return cleaned_link


def cleanLinkV2(url, whitelist):
    if whitelist is None or len(whitelist) == 0:
        if "?" not in url:
            return url.split("&")[0]
        return url.split("?")[0]
    if "?" not in url:
        return url
    base_url, query_string = url.split("?", 1)
    params = query_string.split("&")
    cleaned_params = []
    for param in params:
        key = param.split("=")[0]
        if key in whitelist:
            cleaned_params.append(param)
    if cleaned_params:
        return f"{base_url}?{'&'.join(cleaned_params)}"
    else:
        return base_url


def cleanTiktokLink(url):  # mfw vt.tiktok.com links
    response = requests.get(url)  # make a request to the link to get the final URL after tiktok's trackers redirect it
    if response.status_code != 200:
        return f"Couldn't get real video link - status code {response.status_code}."
    actuallink = response.url
    cleaned_link = cleanLink(actuallink, "*")
    return f"We are using a different method to remove trackers from this link, as this tiktok link has embedded trackers: {cleaned_link}"
