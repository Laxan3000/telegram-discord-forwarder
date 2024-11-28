from aiogram.types import User
from typing import Optional
from tokens import TELEGRAM_TOKEN
from async_lru import alru_cache


@alru_cache(ttl=60*60*24)
async def get_avatar(user: User) -> Optional[str]:
    if not user.bot:
        return None

    file_path: Optional[str] = None

    try:
        # Get the profile photos of the user
        pfps = await user.bot.get_user_profile_photos(user.id, 0, 1)
        
        # Get the file from the file id of the current profile picture of the user
        file_path = (await user.bot.get_file(pfps.photos[0][0].file_id)).file_path
    except:
        # If, for any reason that can also be the user not having
        # set a profile photo, it fails, then return no avatar.
        return None
    
    # Return the file path as an URL.
    # Discord will then download the image from the url and upload
    # it to their own servers (so the telegram token won't be shared).
    return f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}" \
    if file_path else None
