# Automatic Link Cleaner

A Discord bot that automatically 'cleans' links.

[Website](https://alc.etangaming.xyz/ "alc website") • [Terms of Service](https://alc.etangaming.xyz/termsofservice.html "etanbot terms of service") • [Privacy Policy](https://alc.etangaming.xyz/privacypolicy.html "etanbot privacy policy")

[Add to your Discord](https://discord.com/oauth2/authorize?client_id=1537818424854581250 "Add Automatic Link Cleaner to your Discord Server")

> [!NOTE]
> Uptime of this bot is flaky.
> You are free to selfhost the bot and run it on your own bot account.

## Features

### Server

* Automatic link cleaning (removing known ?parameter trackers from links)
* Better embeds (see [fixtweetbot](https://github.com/Kyrela/FixTweetBot "FixTweetBot GitHub repository"))
* Various configuration for your server (add or remove url parameters, change whitelist, change action(s) to original message, etc.)

### User

* Clean links via slash command (`/clean-link` or `/clean-link-v2`)

## Quickstart

Open [this link](https://discord.com/oauth2/authorize?client_id=1537818424854581250 "Add Automatic Link Cleaner to your Discord account") to authorise the official instance of Automatic Link Cleaner with your Discord account, and select whether you wish to install to a guild (server) or to yourself. 

## Selfhosting

### You will need:

* A Discord bot
* Python (3.0 or above)
* The required Python libraries in `requirements.txt`

The following are optional, but recommended:

* A device capable of running the Python program for a while (if you plan on leaving the bot online most of the time)

### Discord Bot

1. Log on to the [Discord Developer Portal](https://discord.com/developers/applications "Leads you to the Discord Developer Portal").
2. Create a new application using the button on the top right.
3. Add a new app icon. This will be the bot's profile picture.
4. Under the Overview tab, click on "Bot", and reset the bot's token. Copy the new token and keep it somewhere, you'll need it later.
5. Go to the Installation tab, and make sure the installation context is set to "User Install" and "Guild Install". Select "Discord Provided Link" for the Install link, then copy the generated URL.
6. Paste the url into your favourite browser, and add the bot to your account.

### Python Code

Ensure you have everything with:
`git clone https://github.com/etangaming123/automaticlinkcleaner`

Get all the required modules with:
`pip install -r requirements.txt`

Then, create a `config.json` file in the same directory as `main.py` with the following content:

```json
{
	"token": "Your Discord Bot Token here",
	"poweruserid": "Your Discord User ID here (optional, for owner-only commands)"
}
```

## License

Automatic Link Cleaner is licenced under the **[MIT License](./LICENSE "Leads you to the license for this repository").**