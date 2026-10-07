from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from openai import AsyncOpenAI

from src.config import DB_PATH, OPENAI_API_KEY, ORDERS, TODAY
from src.database import close_db, open_db
from src.exception_handlers import register_exception_handlers
from src.routers.sessions import router as sessions_router
from src.routers.users import router as users_router
from src.tools.order_tools import OrderTools


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.database = await aiosqlite.connect(DB_PATH)
    await open_db(app.state.database)
    app.state.aclient = AsyncOpenAI(api_key=OPENAI_API_KEY, max_retries=5, timeout=120)
    app.state.order_tools = OrderTools(ORDERS, TODAY)
    yield
    await app.state.aclient.close()
    await close_db(app.state.database)


app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)
app.include_router(users_router)
app.include_router(sessions_router)
