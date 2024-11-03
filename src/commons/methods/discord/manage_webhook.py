import discord
from typing import Optional, Union
from aiogram.types import User
from async_lru import alru_cache
from textwrap import wrap
from ....discord import discord_bot
from limits import DISCORD_MESSAGE_LENGTH_LIMIT


@alru_cache()
async def get_channel(chat_id: int):
    return discord_bot.bot.get_channel(chat_id) \
    or await discord_bot.bot.fetch_channel(chat_id)


async def get_or_create_webhook(
    channel: Union[
        discord.TextChannel,
        discord.VoiceChannel,
        discord.StageChannel
    ]
) -> discord.Webhook:
    webhooks: list[discord.Webhook] = await channel.webhooks()
    webhook: discord.Webhook
    
    # If our webhook is not present, create it
    for webhook in webhooks:
        if webhook.name == "telegram":
            break
    else:
        webhook = await channel.create_webhook(
            name="telegram"
        )
    
    # Get a partial webhook from the first webhook of the list
    return discord.Webhook.from_url(
        webhook.url,
        client=discord_bot.bot
    )


async def send_webhook_message(
    telegram_user: User,
    avatar_url: Optional[str],
    chat_id: int,
    text: str,
    reference: Optional[Union[
        discord.Message,
        discord.MessageReference,
        discord.PartialMessage
    ]] = None
) -> list[Union[discord.Message, discord.WebhookMessage]]:
    thread_name: str = discord.utils.MISSING
    
    # Get the channel the message has to be sent
    match channel := await get_channel(chat_id):
        # You can't send messages to categories or if the message was not found
        case discord.CategoryChannel() | None:
            return []
        
        # If the channel is a thread, take his parent
        case discord.Thread():
            thread_name = channel.name
            if not (channel := channel.parent):
                return []
        
        # If a DM or a group, send the message regularly without webhooks
        case discord.abc.PrivateChannel():
            return [
                await channel.send( # type: ignore
                    content=content,
                    reference=reference
                )
                for content in wrap(
                    text=f"### {telegram_user.full_name}\n{text}",
                    width=DISCORD_MESSAGE_LENGTH_LIMIT,
                    break_long_words=False,
                    replace_whitespace=False
                )
            ]
            
    
    # You can't send messages to forums (as a channel) either
    if isinstance(channel, discord.channel.ForumChannel):
        return []
    
    # For any other type, continue from here instead
    return [
        await (await get_or_create_webhook(channel)).send(
            content=content,
            username=f"{telegram_user.full_name} (from Telegram)",
            avatar_url=avatar_url or discord.utils.MISSING,
            thread_name=thread_name,
            wait=True
        )
        for content in wrap(
            text=text,
            width=DISCORD_MESSAGE_LENGTH_LIMIT,
            break_long_words=False,
            replace_whitespace=False
        )
    ]


async def edit_webhook_message(
    telegram_user: User,
    chat_id: int,
    message_id: int,
    text: str,
    first_call: bool
) -> Optional[Union[discord.Message, discord.WebhookMessage]]:
    # Get the channel the message has to be sent
    match channel := await get_channel(chat_id):
        # This shouldn't be the case in the first place
        case discord.CategoryChannel() | None:
            return
        
        # If the channel is a thread, take his parent
        case discord.threads.Thread():
            if not (channel := channel.parent):
                return
        
        case discord.ForumChannel():
            pass
        
        # If a DM or a group, edit the message regularly without webhooks
        case discord.abc.PrivateChannel():
            return await (await channel.fetch_message(message_id)).edit( # type: ignore
                content=(
                    f"### {telegram_user.full_name}\n{text}"
                    if first_call
                    else text
                )
            )
    
    # You can't send messages to forums (as a channel) either
    if isinstance(channel, discord.ForumChannel):
        return
    
    # For any other type, continue from here instead
    
    return await (
        await (
            await get_or_create_webhook(channel)
        ).fetch_message(message_id)
    ).edit(content=text)


async def delete_webhook_messages(
    chat_id: int,
    message_ids: list[int],
) -> None:
    
    # Get the channel the message has to be deleted
    match channel := await get_channel(chat_id):
        # This shouldn't be the case in the first place
        case discord.CategoryChannel() | None:
            return
        
        # If the channel is a thread, take his parent
        case discord.threads.Thread():
            if not (channel := channel.parent):
                return
        
        case discord.ForumChannel():
            pass

        # If a DM or a group, delete the message regularly
        case discord.abc.PrivateChannel():
            for message_id in message_ids:
                await (await channel.fetch_message(message_id)).delete() # type: ignore
                
            return
    
    # You can't send messages to forums (as a channel) either
    if isinstance(channel, discord.ForumChannel):
        return
    
    await channel.delete_messages([
        channel.get_partial_message(message_id)
        for message_id in message_ids
    ])