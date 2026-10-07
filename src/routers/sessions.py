import json
from collections.abc import AsyncIterator

import openai
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from src.deps import get_chat_service, get_session_service
from src.schemas.message import MessageIn
from src.schemas.session import Session, SessionIn, SessionOut
from src.services.chat import ChatService
from src.services.session import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionIn,
    service: SessionService = Depends(get_session_service),
) -> SessionOut:
    return await service.create(payload.user_id)


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    service: SessionService = Depends(get_session_service),
) -> Session:
    return await service.get(session_id)


@router.post("/{session_id}/messages")
async def send_message(
    session_id: int,
    message: MessageIn,
    session_service: SessionService = Depends(get_session_service),
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    session = await session_service.get(session_id)

    async def events() -> AsyncIterator[str]:
        try:
            async for kind, data in chat_service.chat(session, message):
                yield sse(kind, data)
        except openai.APIError as e:
            yield sse("error", {"detail": f"{type(e).__name__}: {e}"})
            return
        yield sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream")
