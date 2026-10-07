import aiosqlite
from fastapi import Depends, Request
from openai import AsyncOpenAI

from src.repositories.session import SessionRepository
from src.repositories.user import UserRepository
from src.services.chat import ChatService
from src.services.session import SessionService
from src.services.user import UserService
from src.tools.order_tools import OrderTools


def get_db(request: Request) -> aiosqlite.Connection:
    return request.app.state.database


def get_aclient(request: Request) -> AsyncOpenAI:
    return request.app.state.aclient


def get_order_tools(request: Request) -> OrderTools:
    return request.app.state.order_tools


def get_user_repository(database: aiosqlite.Connection = Depends(get_db)) -> UserRepository:
    return UserRepository(database)


def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)


def get_session_repository(database: aiosqlite.Connection = Depends(get_db)) -> SessionRepository:
    return SessionRepository(database)


def get_session_service(
    repo: SessionRepository = Depends(get_session_repository),
    user_service: UserService = Depends(get_user_service),
) -> SessionService:
    return SessionService(repo, user_service)


def get_chat_service(
    session_service: SessionService = Depends(get_session_service),
    aclient: AsyncOpenAI = Depends(get_aclient),
    order_tools: OrderTools = Depends(get_order_tools),
) -> ChatService:
    return ChatService(session_service, aclient, order_tools)
