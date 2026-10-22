from array import array

import aiosqlite

from src.schemas.document import ChunkIn, DocumentIn, DocumentOut


class DocumentRepository:
    def __init__(self, database: aiosqlite.Connection):
        self.database = database

    async def create_document(self, document: DocumentIn) -> DocumentOut:
        cursor = await self.database.execute(
            "INSERT INTO documents (file, title, description) VALUES (?, ?, ?)",
            (document.file, document.title, document.description),
        )
        await self.database.commit()
        return DocumentOut(id=cursor.lastrowid, **document.model_dump())

    async def add_chunks(self, document_id: int, chunks: list[ChunkIn]) -> None:
        await self.database.executemany(
            "INSERT INTO chunks (document_id, page_start, page_end, text, vector) VALUES (?, ?, ?, ?, ?)",
            [(document_id, c.page_start, c.page_end, c.text, array("f", c.vector).tobytes())
             for c in chunks],
        )
        await self.database.commit()

    async def delete_all(self) -> None:
        await self.database.execute("DELETE FROM chunks")
        await self.database.execute("DELETE FROM documents")
        await self.database.commit()

    async def list_chunks(self) -> list[dict]:
        cursor = await self.database.execute(
            "SELECT d.file, d.title, c.page_start, c.page_end, c.text, c.vector "
            "FROM chunks c JOIN documents d ON d.id = c.document_id ORDER BY c.id"
        )
        return [
            {"file": f, "title": t, "page_start": s, "page_end": e, "text": x, "vector": list(array("f", v))}
            for f, t, s, e, x, v in await cursor.fetchall()
        ]
