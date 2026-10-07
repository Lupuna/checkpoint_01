from pydantic import BaseModel

from .turn import TurnItem


class SessionIn(BaseModel):
    user_id: int


class SessionOut(BaseModel):
    id: int
    user_id: int
    created_at: float


class Session(SessionOut):
    history: list[TurnItem]
