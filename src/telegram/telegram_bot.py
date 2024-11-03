import asyncio
from uuid import uuid4
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandObject
from aiogram.filters.command import Command
from tokens import TELEGRAM_TOKEN
from limits import DISCORD_MESSAGE_LENGTH_LIMIT
from typing import Optional
from textwrap import wrap
from ..commons import commons, signals
from ..commons.database import database
from ..commons.methods.parse_telegram_entities import parse_markdown
from ..commons.methods.discord.manage_webhook import edit_webhook_message, get_channel, delete_webhook_messages
from ..commons.methods.discord.get_channel_name import get_channel_name
from ..commons.methods.discord.forward_new_messages import forward_new_messages

dp = Dispatcher()
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(
        parse_mode=None
    )
)


@dp.startup()
async def on_ready() -> None:
    print(f"Telegram bot @{(await bot.get_me()).username} started up succesfully.")


@dp.shutdown()
async def on_shutdown() -> None:
    print(f"Telegram bot @{(await bot.get_me()).username} shat down succesfully.")


@dp.message(Command(commands="associate"))
async def associate(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        return
    
    reply: Optional[Message] = None
    
    if command.args:
        chat_name: str = database.accept_pending(
            uuid=command.args,
            telegram_chat_id=message.chat.id,
            owner_telegram_id=message.from_user.id,
        )
    else:
        uuid: str = str(uuid4())

        database.pend_association(
            uuid=uuid,
            telegram_chat_id=message.chat.id,
            owner_telegram_id=message.from_user.id,
            chat_name=message.chat.full_name,
            creation_date_unix=int(message.date.timestamp())
        )
        
        reply = await message.answer(
            text=f"Use this on Discord: <code>/associate {uuid}</code>",
            parse_mode="HTML"
        )
        
        if not await signals.wait_association_acceptance(uuid):
            return
    
        try:
            chat_name: str = get_channel_name(asyncio.run_coroutine_threadsafe(
                coro=get_channel(database.get_chat_id(uuid)[0]),
                loop=commons.discord_loop
            ).result())
        except:
            chat_name: str = "Pending Channel"
    
    await message.answer(
        text=f"Association with <b><i>{chat_name}</i></b> went smoothly!",
        parse_mode="HTML",
        reply_to_message_id=(reply or message).message_id
    )


@dp.message()
async def on_message(message: Message) -> None:
    if not message.text \
    or not (from_user := message.from_user):
        return

    forward_to: set[int] = database.lookup_discord_chats(message.chat.id)
    
    if not forward_to:
        return

    text: str = parse_markdown(
        original_text=message.text,
        entities=message.entities,
        disable_link_preview=(
            isinstance(message.link_preview_options.is_disabled, bool)
            if message.link_preview_options
            else False
        )
    )
    
    # Lookup all the chats the message has to be forwarded into
    for chat_id in forward_to:
        asyncio.run_coroutine_threadsafe(
            coro=forward_new_messages(
                text=text,
                from_user=from_user,
                discord_chat_id=chat_id,
                telegram_chat_id=message.chat.id,
                telegram_message_id=message.message_id
            ),
            loop=commons.discord_loop
        )


@dp.edited_message()
async def on_message_edit(edited_message: Message) -> None:
    if not edited_message.text \
    or not (from_user := edited_message.from_user):
        return
    
    associations: dict[int, list[int]] = database.lookup_discord_messages(
        telegram_chat_id=edited_message.chat.id,
        telegram_message_id=edited_message.message_id
    )
    
    # If there were no associations, for some reason
    if not associations:
        return
    
    wrapped_text: list[str] = wrap(
        text=parse_markdown(
            original_text=edited_message.text,
            entities=edited_message.entities,
            disable_link_preview=(
                isinstance(edited_message.link_preview_options.is_disabled, bool)
                if edited_message.link_preview_options
                else False
            )
        ),
        width=DISCORD_MESSAGE_LENGTH_LIMIT,
        break_long_words=False,
        replace_whitespace=False
    )
    messages_to_edit: int = len(wrapped_text)
    
    for chat_id, message_ids in associations.items():
        for i, message_id in enumerate(message_ids, 0):
            # If the new message is shorter in messages length
            if i >= messages_to_edit:
                messages_to_delete: list[int] = message_ids[i:]
                
                asyncio.run_coroutine_threadsafe(
                    coro=delete_webhook_messages(chat_id, messages_to_delete),
                    loop=commons.discord_loop
                )
                
                database.delete_message_associations(
                    discord_chat_id=chat_id,
                    telegram_chat_id=edited_message.chat.id,
                    message_ids=messages_to_delete
                )
                
                break
            else:
                result = asyncio.run_coroutine_threadsafe(
                    coro=edit_webhook_message(
                        telegram_user=from_user,
                        chat_id=chat_id,
                        message_id=message_id,
                        text=wrapped_text[i],
                        first_call=i == 0
                    ),
                    loop=commons.discord_loop
                ).result()
        else:
            if len(message_ids) >= len(wrapped_text):
                break
            
            # If the edit message is longer than what Discord can handle (probable)

            asyncio.run_coroutine_threadsafe(
                coro=forward_new_messages(
                    text="".join(wrapped_text[i:]), # type: ignore
                    from_user=from_user,
                    discord_chat_id=chat_id,
                    telegram_chat_id=edited_message.chat.id,
                    telegram_message_id=edited_message.message_id,
                    reference=result # type: ignore
                ),
                loop=commons.discord_loop
            )


async def _launch() -> None:
    # Memorize the current loop
    commons.telegram_loop = asyncio.get_event_loop()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


def init() -> None:
    global dp, bot
    commons.runner.run(_launch())
