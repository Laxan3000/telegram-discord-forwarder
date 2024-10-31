import sqlite3
from pathlib import Path
from itertools import chain
from typing import Optional
from gvars import DATABASE_NAME, PENDING_TIMEOUT


def lookup_discord_chats(telegram_chat_id: int) -> set[int]:
    return set(chain(*cursor.execute(
        """
        SELECT DiscordChatID FROM Associations
        WHERE TelegramChatID = ?;
        """,
        [telegram_chat_id]
    ).fetchall()))


def lookup_discord_messages(
    telegram_chat_id: int,
    telegram_message_id: int
) -> dict[int, tuple[int, ...]]:
    return {
        chat_id: tuple(chain(*cursor.execute(
                """
                SELECT DiscordMessageID FROM MessageAssociations
                WHERE TelegramChatID = ?
                    AND TelegramMessageID = ?
                    AND DiscordChatID = ?
                ORDER BY DiscordMessageID;
                """,
                [
                    telegram_chat_id,
                    telegram_message_id,
                    chat_id
                ]
            ).fetchall()
        ))
        for chat_id in [
            association[0] for association in cursor.execute(
                """
                SELECT DISTINCT DiscordChatID FROM MessageAssociations
                WHERE TelegramChatID = ? AND TelegramMessageID = ?;
                """,
                [
                    telegram_chat_id,
                    telegram_message_id
                ]
            ).fetchall()
        ]
    }


def lookup_telegram_chats(discord_chat_id: int) -> set[int]:
    """"""
    return set(chain(*cursor.execute(
        """
        SELECT TelegramChatID FROM Associations
        WHERE DiscordChatID = ?;
        """,
        [discord_chat_id]
    ).fetchall()))
    

def lookup_telegram_messages(
    discord_chat_id: int,
    discord_message_id: int
) -> dict[int, tuple[int, ...]]:
    return {
        chat_id: tuple(chain(*cursor.execute(
                """
                SELECT TelegramMessageID FROM MessageAssociations
                WHERE DiscordChatID = ?
                    AND DiscordMessageID = ?
                    AND TelegramChatID = ?
                ORDER BY TelegramMessageID;
                """,
                [
                    discord_chat_id,
                    discord_message_id,
                    chat_id
                ]
            ).fetchall()
        ))
        for chat_id in [
            association[0] for association in cursor.execute(
                """
                SELECT DISTINCT TelegramChatID FROM MessageAssociations
                WHERE DiscordChatID = ? AND DiscordMessageID = ?;
                """,
                [
                    discord_chat_id,
                    discord_message_id
                ]
            ).fetchall()
        ]
    }


# TODO: handle exceptions and integrity checks
def associate_chats(
    *,
    uuid: str,
    discord_chat_id: int,
    telegram_chat_id: int,
    owner_discord_id: int,
    owner_telegram_id: int
) -> None:
    cursor.execute(
        """
        INSERT INTO Associations VALUES (?, ?, ?, ?, ?);
        """,
        [
            uuid,
            discord_chat_id,
            telegram_chat_id,
            owner_discord_id,
            owner_telegram_id
        ]
    )
    connection.commit()
    
    
# TODO: handle exceptions and integrity checks
def associate_messages(
    *,
    discord_chat_id: int,
    discord_message_id: int,
    telegram_chat_id: int,
    telegram_message_id: int,
    forward_date_unix: int
) -> None:
    cursor.execute(
        """
        INSERT INTO MessageAssociations VALUES (?, ?, ?, ?, ?);
        """,
        [
            discord_chat_id,
            discord_message_id,
            telegram_chat_id,
            telegram_message_id,
            forward_date_unix
        ]
    )
    connection.commit()
    

# TODO: handle exceptions and integrity checks
def pend_association(
    *,
    uuid: str,
    discord_chat_id: Optional[int] = None,
    owner_discord_id: Optional[int] = None,
    telegram_chat_id: Optional[int] = None,
    owner_telegram_id: Optional[int] = None,
    chat_name: str,
    creation_date_unix: Optional[int]
) -> None:
    cursor.execute(
        """
        INSERT INTO PendingAssociations VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        [
            uuid,
            discord_chat_id,
            owner_discord_id,
            telegram_chat_id,
            owner_telegram_id,
            chat_name,
            creation_date_unix
        ]
    )
    connection.commit()
    

def accept_pending(
    uuid: str,
    discord_chat_id: Optional[int] = None,
    owner_discord_id: Optional[int] = None,
    telegram_chat_id: Optional[int] = None,
    owner_telegram_id: Optional[int] = None
) -> str:
    """
    Accept a pending association.
    Returns the ids and the name of the chat this happened in.
    """
    
    cursor.execute(
        """
        INSERT INTO Associations
        SELECT
            UUID,
            coalesce(DiscordChatID, ?),
            coalesce(TelegramChatID, ?),
            coalesce(OwnerDiscordID, ?), 
            coalesce(OwnerTelegramID, ?)
        FROM PendingAssociations
        WHERE UUID = ?;
        """,
        [
            discord_chat_id,
            telegram_chat_id,
            owner_discord_id,
            owner_telegram_id,
            uuid
        ]
    )
    connection.commit()
    
    chat_name: str = cursor.execute(
        """
        SELECT ChatName FROM PendingAssociations
        WHERE UUID = ?
        LIMIT 1;
        """,
        [uuid]
    ).fetchone()[0]
    
    delete_selected_pending_associations(uuid=uuid)
    
    return chat_name


def is_association_pending(uuid: str) -> bool:
    return bool(cursor.execute(
        """
        SELECT 1 FROM PendingAssociations
        WHERE UUID = ?
        LIMIT 1;
        """,
        [uuid]
    ).fetchone())


def delete_old_message_associations() -> None:
    """
    Delete 2 days (172800 seconds) old message associations.
    This is a static limitation, so it's not recommended
    to change this value any greater.
    """
    
    cursor.execute(
        """
        DELETE FROM MessageAssociations
        WHERE (unixepoch() - ForwardDateUnix) >= 172800;
        """
    )
    connection.commit()


def delete_selected_pending_associations(
    *,
    uuid: Optional[str] = None,
    unix: Optional[int] = None
) -> None:
    """
    Delete associations with the same UUID or older than a few minutes.
    """
    
    cursor.execute(
        """
        DELETE FROM PendingAssociations
        WHERE UUID = ?
        OR (unixepoch() - ?) >= ?
        """,
        [uuid, unix, PENDING_TIMEOUT]
    )
    connection.commit()
    
    
def get_chat_id(uuid: str) -> tuple[int, int]:
    """
    0 - Discord; 1 - Telegram
    """
    
    return cursor.execute(
        """
        SELECT DiscordChatID, TelegramChatID
        FROM Associations
        WHERE UUID = ?
        LIMIT 1;
        """,
        [uuid]
    ).fetchone()


def close() -> None:
    cursor.close()
    connection.close()
    
    print("Database closed successfully.")


def init() -> None:
    global connection, cursor
    
    this_path: Path = Path(__file__).parent.resolve()
    
    connection = sqlite3.connect(
        database=this_path / f"{DATABASE_NAME}.db",
        check_same_thread=False
    )
    cursor = connection.cursor()
    
    print("Connection with the database has been enstablished.")

    # Create the tables
    with open(this_path / f"create_tables.sql") as sql_script:
        cursor.executescript(sql_script.read())
        
        # Commit the changes (necessary)
        connection.commit()
    
    print("Database tables loaded/created succesfully.")
    
    # delete_old_message_associations()
