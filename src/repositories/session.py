import json
import time

import aiosqlite

from src.schemas.session import Session, SessionOut
from src.schemas.turn import Turn, TurnItem


class SessionRepository:
    def __init__(self, database: aiosqlite.Connection):
        self.database = database

    async def create_session(self, user_id: int) -> SessionOut:
        created_at = time.time()
        cursor = await self.database.execute(
            "INSERT INTO sessions (user_id, created_at) VALUES (?, ?)",
            (user_id, created_at),
        )
        await self.database.commit()
        return SessionOut(id=cursor.lastrowid, user_id=user_id, created_at=created_at)

    async def append_turn(self, session_id: int, turn: Turn) -> None:
        cursor = await self.database.execute(
            "SELECT COALESCE(MAX(seq), 0) FROM messages WHERE session_id = ?",
            (session_id,),
        )
        (last_seq,) = await cursor.fetchone()
        await self.database.executemany(
            "INSERT INTO messages (session_id, seq, payload) VALUES (?, ?, ?)",
            [(session_id, last_seq + i, item.model_dump_json(exclude_unset=True))
             for i, item in enumerate(turn.items, start=1)],
        )
        await self.database.commit()

    async def get_session(self, session_id: int) -> Session | None:
        cursor = await self.database.execute(
            "SELECT id, user_id, created_at FROM sessions WHERE id = ?",
            (session_id,),
        )
        session = await cursor.fetchone()
        if session is None:
            return None
        cursor = await self.database.execute(
            "SELECT payload FROM messages WHERE session_id = ? ORDER BY seq",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return Session(
            id=session[0],
            user_id=session[1],
            created_at=session[2],
            history=[TurnItem.model_validate_json(row[0]) for row in rows],
        )
