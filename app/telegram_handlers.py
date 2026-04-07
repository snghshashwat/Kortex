import logging

from fastapi import Header, HTTPException

from app.config import settings
from app.services.messages_service import create_message_and_embedding
from app.services.reminders_service import create_reminder
from app.telegram_api import answer_callback_query, send_message


logger = logging.getLogger(__name__)


def reminder_buttons(message_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "Tomorrow", "callback_data": f"remind:tomorrow:{message_id}"},
                {"text": "Next week", "callback_data": f"remind:next_week:{message_id}"},
            ],
            [
                {"text": "No", "callback_data": f"remind:no:{message_id}"},
            ],
        ]
    }


async def verify_secret(secret: str | None) -> None:
    if secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")


async def handle_message(update: dict) -> None:
    message = update["message"]
    text = (message.get("text") or "").strip()

    if not text:
        await send_message(chat_id=message["chat"]["id"], text="Please send text only for now.")
        return

    try:
        created = create_message_and_embedding(
            user_id=message["from"]["id"],
            chat_id=message["chat"]["id"],
            text=text,
        )

        await send_message(
            chat_id=created["chat_id"],
            text="Do you want to be reminded about this?",
            reply_markup=reminder_buttons(created["id"]),
        )
    except Exception as exc:
        logger.exception("Failed to process Telegram message: %s", exc)
        await send_message(
            chat_id=message["chat"]["id"],
            text=(
                "I received your message, but I could not save it right now. "
                "Please check the backend configuration and try again."
            ),
        )


async def handle_callback(update: dict) -> None:
    callback = update["callback_query"]
    data = callback.get("data", "")
    parts = data.split(":")

    if len(parts) != 3 or parts[0] != "remind":
        await answer_callback_query(callback["id"], text="Unknown action")
        return

    when = parts[1]
    message_id = parts[2]

    if when == "no":
        await answer_callback_query(callback["id"], text="No reminder set")
        await send_message(chat_id=callback["message"]["chat"]["id"], text="Okay, no reminder set.")
        return

    try:
        reminder = create_reminder(
            message_id=message_id,
            user_id=callback["from"]["id"],
            chat_id=callback["message"]["chat"]["id"],
            when=when,
        )

        await answer_callback_query(callback["id"], text="Reminder set")
        await send_message(
            chat_id=callback["message"]["chat"]["id"],
            text=f"Reminder saved for {reminder['remind_at'].isoformat()} UTC",
        )
    except Exception as exc:
        logger.exception("Failed to create reminder: %s", exc)
        await answer_callback_query(callback["id"], text="Could not save reminder")
        await send_message(
            chat_id=callback["message"]["chat"]["id"],
            text="I could not save that reminder. Please try again after checking the backend.",
        )
