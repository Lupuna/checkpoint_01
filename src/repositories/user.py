import aiosqlite

from src.schemas.user import UserOut


class UserRepository:
    def __init__(self, database: aiosqlite.Connection):
        self.database = database

    async def create_user(self, title: str) -> UserOut:
        cursor = await self.database.execute("INSERT INTO users (title) VALUES (?)", (title,))
        await self.database.commit()
        return UserOut(id=cursor.lastrowid, title=title)

    async def get_user(self, user_id: int) -> UserOut | None:
        cursor = await self.database.execute("SELECT id, title FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return UserOut(id=row[0], title=row[1])
