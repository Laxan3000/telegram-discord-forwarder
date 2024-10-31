import discord
from typing import Any


def get_channel_name(channel: Any) -> str:
    match channel:
        case discord.abc.PrivateChannel():
            return channel.recipients[0].name \
            if isinstance(channel, discord.DMChannel) \
            else getattr(channel, "name") or "Recipient"
        
        case discord.PartialMessageable():
            return channel.guild.name if channel.guild else "Recipient"
        
        case _:
            return channel.name or "Recipient"
    