import asyncio
from collections import Counter
from pathlib import Path

import numpy as np
import pymupdf
from openai import AsyncOpenAI

from src.config import EMBED_DIMENSIONS, EMBED_MODEL, INCOMING_DIR
from src.repositories.document import DocumentRepository
from src.schemas.document import ChunkIn, DocumentIn, DocumentOut
from src.services.bm25 import BM25


DOCUMENTS = {
    "reglament-garantii.pdf": (
        "Регламент гарантийного обслуживания",
        "Гарантийные сроки, порядок обращения, диагностика и ремонт, подменный фонд, негарантийные случаи.",
    ),
    "pravila-loyalnosti.pdf": (
        "Правила программы лояльности",
        "Участие, начисление и списание бонусов, уровни, срок жизни бонусов, возврат заказа с бонусами.",
    ),
    "spravochnik-pokupatelya.pdf": (
        "Справочник покупателя",
        "Руководства к робот-пылесосу AquaVac R7 и смарт-часам PulseOne S3, правила лояльности, гарантии, "
        "возврата и доставки.",
    ),
}


class DocumentService:
    def __init__(self, document_repository: DocumentRepository, aclient: AsyncOpenAI):
        self.document_repository = document_repository
        self.aclient = aclient
        self.size = 150
        self.overlap = 25
        self.embed_batch = 64

    async def index(self) -> list[DocumentOut]:
        await self.document_repository.delete_all()
        documents = []
        for file, (title, description) in DOCUMENTS.items():
            pages = await asyncio.to_thread(self.parse_pdf, INCOMING_DIR / file)
            chunks = self.chunk_document(pages)
            await self.embed_chunks(chunks)
            document = await self.document_repository.create_document(
                DocumentIn(file=file, title=title, description=description)
            )
            await self.document_repository.add_chunks(document.id, [ChunkIn(**chunk) for chunk in chunks])
            documents.append(document)
        return documents

    def parse_pdf(self, path: Path) -> list[dict]:
        pages = []
        with pymupdf.open(path) as doc:
            for number, page in enumerate(doc, start=1):
                paragraphs = [" ".join(block[4].split()) for block in page.get_text("blocks") if block[6] == 0]
                pages.append({"page": number, "text": "###".join(p for p in paragraphs if p)})
        return pages

    def chunk_document(self, pages: list[dict]) -> list[dict]:
        paragraphs = [(page["page"], p) for page in pages for p in page["text"].split("###")]
        chunks, carry, current = [], "", []

        for page, paragraph in paragraphs:
            words = sum(len(p.split()) for _, p in current) + len(paragraph.split())
            if current and words > self.size:
                carry, current = self.generate_chunk(chunks, current, carry), []
            current.append((page, paragraph))

        if current:
            self.generate_chunk(chunks, current, carry)
        return chunks

    def generate_chunk(self, chunks: list[dict], current: list, carry: str) -> str:
        text = "###".join(p for _, p in current)
        chunks.append({
            "page_start": current[0][0],
            "page_end": current[-1][0],
            "text": f"{carry}###{text}" if carry else text,
            "vector": None,
        })
        return " ".join(text.split()[-self.overlap:])

    async def embed_chunks(self, chunks: list[dict]) -> None:
        for i in range(0, len(chunks), self.embed_batch):
            batch = chunks[i:i + self.embed_batch]
            vectors = await self.embed([c["text"].replace("###", "\n\n") for c in batch])
            for chunk, vector in zip(batch, vectors):
                chunk["vector"] = vector

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.aclient.embeddings.create(model=EMBED_MODEL, input=texts, dimensions=EMBED_DIMENSIONS)
        return [data.embedding for data in response.data]

    async def vector_scores(self, chunks: list[dict], query: str) -> np.ndarray:
        matrix = np.array([c.pop("vector") for c in chunks], dtype=np.float32)
        query_vector = np.array((await self.embed([query]))[0], dtype=np.float32)
        return matrix @ query_vector

    async def vector_search(self, query: str, k: int = 10) -> list[dict]:
        chunks = await self.document_repository.list_chunks()
        scores = await self.vector_scores(chunks, query)
        return [{**chunks[i], "score": float(scores[i])} for i in np.argsort(-scores)[:k]]

    def rrf(self, *rankings: list[int], k: int = 60) -> list[int]:
        score = Counter()
        for ranking in rankings:
            for position, index in enumerate(ranking, 1):
                score[index] += 1 / (k + position)
        return [i for i, _ in score.most_common()]

    async def hybrid_search(self, query: str, k: int = 5, top: int = 20) -> list[dict]:
        chunks = await self.document_repository.list_chunks()
        scores = await self.vector_scores(chunks, query)
        vector_top = [int(i) for i in np.argsort(-scores)[:top]]
        bm25 = BM25([f"{c['title']}\n{c['text'].replace('###', ' ')}" for c in chunks])
        bm25_top = bm25.top(query, top)
        return [chunks[i] for i in self.rrf(vector_top, bm25_top)[:k]]
