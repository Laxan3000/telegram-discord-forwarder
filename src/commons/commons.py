from asyncio import AbstractEventLoop, Runner


def close() -> None:
    runner.close()
    telegram_loop.close()
    discord_loop.close()


def init() -> None:
    global runner, telegram_loop, discord_loop

    runner = Runner()
    telegram_loop = AbstractEventLoop()
    discord_loop = AbstractEventLoop()
