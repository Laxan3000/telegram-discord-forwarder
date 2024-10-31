PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Associations (
    UUID TEXT PRIMARY KEY,
    DiscordChatID INTEGER NOT NULL,
    TelegramChatID INTEGER NOT NULL,
    OwnerDiscordID INTEGER NOT NULL,
    OwnerTelegramID INTEGER NOT NULL,
    
    UNIQUE(DiscordChatID, TelegramChatID)
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS MessageAssociations (
    DiscordChatID INTEGER NOT NULL,
    DiscordMessageID INTEGER NOT NULL,
    TelegramChatID INTEGER NOT NULL,
    TelegramMessageID INTEGER NOT NULL,
    ForwardDateUnix INTEGER NOT NULL,
    
    UNIQUE(DiscordChatID, DiscordMessageID, TelegramChatID, TelegramMessageID)
    FOREIGN KEY(DiscordChatID, TelegramChatID)
        REFERENCES Associations(DiscordChatID, TelegramChatID)
        ON DELETE CASCADE
) STRICT;

CREATE TEMPORARY TABLE PendingAssociations (
    UUID TEXT PRIMARY KEY,
    DiscordChatID INTEGER UNIQUE,
    OwnerDiscordID INTEGER UNIQUE,
    TelegramChatID INTEGER UNIQUE,
    OwnerTelegramID INTEGER UNIQUE,
    ChatName TEXT NOT NULL,
    CreationDateUnix INTEGER NOT NULL,
    
    CHECK((
            (DiscordChatID NOTNULL AND OwnerDiscordID NOTNULL)
            AND
            (TelegramChatID ISNULL AND OwnerTelegramID ISNULL)
        ) OR (
            (DiscordChatID ISNULL AND OwnerDiscordID ISNULL)
            AND
            (TelegramChatID NOTNULL AND OwnerTelegramID NOTNULL)
    ))
), STRICT, WITHOUT ROWID;

CREATE UNIQUE INDEX IF NOT EXISTS UUID ON Associations(UUID);
CREATE UNIQUE INDEX UUID ON PendingAssociations(UUID);
