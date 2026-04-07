from contextlib import asynccontextmanager

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

from app.db import close_pool, open_pool
from app.routes import router as api_router
from app.scheduler import start_scheduler, stop_scheduler
from app.telegram_handlers import handle_callback, handle_message, verify_secret


@asynccontextmanager
async def lifespan(_: FastAPI):
    open_pool()
    start_scheduler()
    yield
    stop_scheduler()
    close_pool()


app = FastAPI(title="Telegram Second Brain MVP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"ok": True}


@app.post("/telegram/webhook")
async def telegram_webhook(
    update: dict,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    await verify_secret(x_telegram_bot_api_secret_token)

    if update.get("message"):
        await handle_message(update)
    elif update.get("callback_query"):
        await handle_callback(update)

    return {"ok": True}
