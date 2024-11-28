import discord, asyncio
from tokens import DISCORD_TOKEN
from limits import TELEGRAM_MESSAGE_LENGTH_LIMIT
from discord.ext.commands import Bot, Context
from typing import Optional
from uuid import uuid4
from ..commons import commons, signals
from ..commons.database import database
from ..telegram import telegram_bot
from ..commons.methods.parse_discord_entities import get_entities_wrapped
from ..commons.methods.discord.get_channel_name import get_channel_name

bot = Bot(
    command_prefix="/",
    intents=discord.Intents.all()
)


@bot.event
async def on_ready() -> None:
    if not bot.user:
        return

    print(f"Discord bot @{bot.user.name} started up successfully.")


@bot.event
async def on_disconnect() -> None:
    if not bot.user:
        return
    
    print(f"Discord bot @{bot.user.name} shat down successfully.")


@bot.command()
async def associate(ctx: Context, *args: str) -> None:
    reply: Optional[discord.Message] = None
    
    if args:
        chat_name: str = database.accept_pending(
            uuid=args[0],
            discord_chat_id=ctx.channel.id,
            owner_discord_id=ctx.author.id
        )
    else:
        uuid: str = str(uuid4())
        
        database.pend_association(
            uuid=uuid,
            discord_chat_id=ctx.channel.id,
            owner_discord_id=ctx.author.id,
            chat_name=get_channel_name(ctx.channel),
            creation_date_unix=int(ctx.message.created_at.timestamp())
        )
        
        reply = await ctx.send(f"Use this on Telegram: `/associate {uuid}`")
        
        if not await signals.wait_association_acceptance(uuid):
            return
    
        chat_name: str = asyncio.run_coroutine_threadsafe(
            coro=telegram_bot.bot.get_chat(database.get_chat_ids(uuid)[1]),
            loop=commons.telegram_loop
        ).result().full_name
    
    await ctx.send(
        content=f"Association with ***{chat_name}*** went smoothly!",
        reference=reply or ctx.message
    )


@bot.event
async def on_message(message: discord.Message) -> None:
    # Process normal commands instead if the context is valid
    if (await bot.get_context(message)).valid:
        await bot.process_commands(message)
        return
    
    # Ignore messages sent from bots
    if message.author.bot:
        return
    
    forward_to: set[int] = database.lookup_telegram_chats(message.channel.id)
    
    if not forward_to:
        return
    
    
    wrapped_text, entities, link_preview_options = get_entities_wrapped(
        suffix=f"{message.author.global_name}\n",
        text=message.content
    )

    # Lookup all the chats the message has to be forwarded into
    for chat_id in forward_to:
        # Split text if it's too long.
        for i, content in enumerate(wrapped_text, 0):
            result = asyncio.run_coroutine_threadsafe(
                coro=telegram_bot.bot.send_message(
                    chat_id=chat_id,
                    text=content,
                    entities=entities[i],
                    link_preview_options=link_preview_options
                ),
                loop=commons.telegram_loop
            ).result()
            
            if not result:
                continue
            
            # Register the message to the database
            database.associate_messages(
                discord_chat_id=message.channel.id,
                discord_message_id=message.id,
                telegram_chat_id=chat_id,
                telegram_message_id=result.message_id,
                forward_date_unix=int(result.date.timestamp()) # Date from Telegram
            )
    
    # Now process normal commands
    await bot.process_commands(message)


@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent) -> None:
    message = payload.data
    
    # Ignore messages sent from bots
    if message["author"].get("bot", False):
        return

    associations: dict[int, list[int]] = database.lookup_telegram_messages(
        discord_chat_id=payload.channel_id,
        discord_message_id=payload.message_id
    )
    
    # If there were no associations, for some reason
    if not associations:
        return
    
    wrapped_text, entities, link_preview_options = get_entities_wrapped(
        suffix=f"{message["author"].get("global_name")} (edited)\n",
        text=message["content"]
    )
    messages_to_edit: int = len(wrapped_text)
    
    # Lookup all the chats the message has to be edited
    for chat_id, message_ids in associations.items():
        for i, message_id in enumerate(message_ids, 0):
            # If the new message is shorter in messages length
            if i >= messages_to_edit:
                messages_to_delete: list[int] = message_ids[i:]
                
                asyncio.run_coroutine_threadsafe(
                    coro=telegram_bot.bot.delete_messages(
                        chat_id=chat_id,
                        message_ids=messages_to_delete
                    ),
                    loop=commons.telegram_loop
                )
                
                database.delete_message_associations(
                    discord_chat_id=payload.channel_id,
                    telegram_chat_id=chat_id,
                    message_ids=messages_to_delete
                )
                
                break
            else:
                asyncio.run_coroutine_threadsafe(
                    coro=telegram_bot.bot.edit_message_text(
                        text=wrapped_text[i],
                        chat_id=chat_id,
                        message_id=message_id,
                        entities=entities[i],
                        link_preview_options=link_preview_options
                    ),
                    loop=commons.telegram_loop
                )
        else:
            if len(message_ids) >= len(wrapped_text):
                break
            
            # If the edit message is longer than what Telegram can handle (unprobable)
            
            # Split text if it's too long.
            for i, content in enumerate(wrapped_text[i:], i): # type: ignore
                result = asyncio.run_coroutine_threadsafe(
                    coro=telegram_bot.bot.send_message(
                        chat_id=chat_id,
                        text=content,
                        entities=entities[i],
                        link_preview_options=link_preview_options,
                        reply_to_message_id=message_id # type: ignore
                    ),
                    loop=commons.telegram_loop
                ).result()
                
                if not result:
                    continue
                
                # Register the message to the database
                database.associate_messages(
                    discord_chat_id=payload.channel_id,
                    discord_message_id=payload.message_id,
                    telegram_chat_id=chat_id,
                    telegram_message_id=result.message_id,
                    forward_date_unix=int(result.date.timestamp()) # Date from Telegram
                )   
        

async def _launch() -> None:
    # Memorize the current loop
    commons.discord_loop = asyncio.get_event_loop()
    
    await bot.start(DISCORD_TOKEN)


def close() -> None:
    asyncio.run_coroutine_threadsafe(
        coro=bot.close(),
        loop=commons.discord_loop
    )


def init() -> None:
    global bot
    commons.runner.run(_launch())
