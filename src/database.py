import aiosqlite

from .models.turn_item import CREATE_SQL as TURN_ITEMS_SQL
from .models.session import CREATE_SQL as SESSIONS_SQL
from .models.user import CREATE_SQL as USERS_SQL

SCHEMA = USERS_SQL + SESSIONS_SQL + TURN_ITEMS_SQL


async def open_db(database: aiosqlite.Connection) -> None:
    await database.execute("PRAGMA foreign_keys = ON")
    await database.executescript(SCHEMA)
    await database.commit()


async def close_db(database: aiosqlite.Connection) -> None:
    await database.close()
