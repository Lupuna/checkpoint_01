import json

from openai import AsyncOpenAI

from src.schemas.message import MessageIn
from src.schemas.session import Session
from src.services.chat import ChatService
from src.services.document import DocumentService
from src.tools.order_tools import OrderTools


class RecordingTools(OrderTools):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls: list[dict] = []

    async def run(self, name: str, arguments_json: str) -> str:
        output = await super().run(name, arguments_json)
        try:
            args = json.loads(arguments_json)
        except json.JSONDecodeError:
            args = {"_raw": arguments_json}
        self.calls.append({"name": name, "args": args, "output": json.loads(output)})
        return output


class NullSessionService:
    async def append_turn(self, session_id, turn) -> None:
        pass


class CachedChunks:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks

    async def list_chunks(self) -> list[dict]:
        return [dict(chunk) for chunk in self.chunks]


async def run_turn(query: str, aclient: AsyncOpenAI, orders: dict, today, chunks: list[dict]) -> dict:
    documents = DocumentService(CachedChunks(chunks), aclient)
    tools = RecordingTools(orders, today, documents)
    chat = ChatService(NullSessionService(), aclient, tools)
    session = Session(id=0, user_id=0, created_at=0, history=[])

    answer, usage = [], {}
    async for kind, payload in chat.chat(session, MessageIn(text=query)):
        if kind == "text":
            answer.append(payload)
        elif kind == "usage":
            usage = payload
    return {"answer": "".join(answer), "calls": tools.calls, "orders": tools.orders, "refunds": tools.refunds,
            "usage": usage}
