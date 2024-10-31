import asyncio, discord
from aiogram.types import User
from typing import Optional, Union
from .manage_webhook import send_webhook_message
from ..telegram.get_avatar_url import get_avatar
from ...database import database
from ... import commons


async def forward_new_messages(
    text: str,
    from_user: User,
    discord_chat_id: int,
    telegram_chat_id: int,
    telegram_message_id: int,
    reference: Optional[Union[
        discord.Message,
        discord.MessageReference,
        discord.PartialMessage
    ]] = None
) -> None:
    # Split text if it's too long.
    for result in await send_webhook_message(
        telegram_user=from_user,
        avatar_url=asyncio.run_coroutine_threadsafe(
            coro=get_avatar(from_user),
            loop=commons.telegram_loop
        ).result(),
        chat_id=discord_chat_id,
        text=text,
        reference=reference
    ):
        if not result:
            continue
        
        # Register the messages to the database
        database.associate_messages(
            discord_chat_id=discord_chat_id,
            discord_message_id=result.id,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
            forward_date_unix=int(result.created_at.timestamp()) # Date from Discord
        )
