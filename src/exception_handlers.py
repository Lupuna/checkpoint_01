import sqlite3

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.exceptions import SessionNotFoundError, UserNotFoundError


async def not_found(_: Request, exc: UserNotFoundError | SessionNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": f"{exc.object_name} not found"},
    )


async def integrity_error(request: Request, _: sqlite3.IntegrityError) -> JSONResponse:
    await request.app.state.database.rollback()
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Нарушено ограничение базы"},
    )


async def operational_error(request: Request, _: sqlite3.OperationalError) -> JSONResponse:
    await request.app.state.database.rollback()
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "База недоступна"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(UserNotFoundError, not_found)
    app.add_exception_handler(SessionNotFoundError, not_found)
    app.add_exception_handler(sqlite3.IntegrityError, integrity_error)
    app.add_exception_handler(sqlite3.OperationalError, operational_error)
