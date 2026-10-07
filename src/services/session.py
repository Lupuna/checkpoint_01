from src.exceptions import SessionNotFoundError
from src.repositories.session import SessionRepository
from src.schemas.session import Session, SessionOut
from src.schemas.turn import Turn
from src.services.user import UserService


class SessionService:
    def __init__(self, session_repository: SessionRepository, user_service: UserService):
        self.session_repository = session_repository
        self.user_service = user_service

    async def create(self, user_id: int) -> SessionOut:
        await self.user_service.get(user_id)
        return await self.session_repository.create_session(user_id)

    async def get(self, session_id: int) -> Session:
        session = await self.session_repository.get_session(session_id)
        if session is None:
            raise SessionNotFoundError("session")
        return session

    async def append_turn(self, session_id: int, turn: Turn) -> None:
        await self.session_repository.append_turn(session_id, turn)
