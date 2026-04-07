import httpx

from app.config import settings

BASE_URL = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


async def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"{BASE_URL}/sendMessage", json=payload)
        response.raise_for_status()


async def answer_callback_query(callback_query_id: str, text: str = "Saved") -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
        )
        response.raise_for_status()
