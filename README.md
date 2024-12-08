### Still in beta. The repo is public for people to see, but it's not meant for public use as of now. Take it as a proof of concept.

# Telegram <-> Discord Forwarder

The main purpose of these bots is to make linking Telegram and Discord groups easier, letting Discord users read messages that are sent to the linked Telegram group and vice versa.

For this to happen, send `/associate` in one of your DGC (DM / Group / Channel) and use the command the bot tells you to send to link the group/channel you'd like to link.

Discord's side will tend to use webhoooks for channels and his messages for private conversations or groups. Telegram doesn't have this feature, so it will always use his messages.

## Please note

The bots are still in beta and many features are missing. Right now, only text to text conversations are supported.  
There currently aren't many integrity checks either, as I'm still developing the remaining functions.

## Currently supported features

- Sending messages to one client to the other, splitting the message in case it doesn't fit in the client's message length limit;
- Editing sent messages and sending new ones in case it doesn't fit the client's message length limit.

## Starting the bots

Before starting the script, create a `tokens.py` file in the same folder `main.py` is at: this file is needed to identify your bot tokens.   
Creating a custom class to hide your tokens is an option (as long as these same variables are used), but to keep things simple, you can arrange it like this:

```python
DISCORD_TOKEN = "DISCORD BOT TOKEN FROM DISCORD DEVELOPERS"
TELEGRAM_TOKEN = "TELEGRAM BOT TOKEN FROM @BOTFATHER"
```

Then, simply run `main.py`

## Known problems

- Converting Telegram's markdown to Discord's is easy enough, but the opposite isn't the case. The library currently used for this purpose doesn't distinguish escaping and spaces between markdown symbols very well.
- Right now, there is no way to disassociate the associations if you don't do it yourself.

## Goals

- To make Telegram to Discord comunication seamless, so each person can use the client they want for communicating with each other;
- Letting people share their messages across different channels/groups at once.

## Libraries used

- [async-lru][al]
- [aiogram][ag]
- [discord.py][dp]
- (david-why's) [discord-markdown-ast-parser][dmap]
    - This is the least "buggy" I was able to find.

To install those at once, simply run:

```bash
pip install -r requirements.txt
```

[al]: https://github.com/aio-libs/async-lru
[ag]: https://github.com/aiogram/aiogram
[dp]: https://github.com/Rapptz/discord.py
[dmap]: https://github.com/david-why/discord-markdown-ast-parser