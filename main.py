if __name__ == "__main__":
    from threading import Thread
    from src.discord import discord_bot
    from src.telegram import telegram_bot
    from src.commons import commons
    from src.commons.database import database

    # Init commons
    commons.init()
    database.init()
    
    # Initialize discord as a separate thread
    discord_client: Thread = Thread(
        target=discord_bot.init
    )

    # Start the discord process
    discord_client.start()

    # Start the telegram process in the main thread
    # This will also wait until its process is done.
    # Luckily, aiogram automatically closes the bot
    # in case of a KeyboardInterrupt.
    telegram_bot.init()

    # Close Discord and wait for it to end its process (necessary)
    discord_bot.close()
    discord_client.join()

    # Close what was opened before
    commons.close()
    database.close()
