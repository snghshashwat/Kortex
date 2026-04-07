import logging

from fastapi import Header, HTTPException

from app.auth import create_access_token
from app.config import settings
from app.nlp_parser import parse_reminder_time
from app.reminder_state import clear_pending_reminder, get_pending_reminder, set_pending_reminder
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
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]

    if text.startswith("/link") or text.startswith("/auth"):
        token = create_access_token(user_id, chat_id)
        await send_message(
            chat_id=chat_id,
            text=(
                "Your Kortex access token:\n\n"
                f"{token}\n\n"
                "Paste this into the dashboard to access your notes and graph. "
                "Keep it private."
            ),
        )
        return

    if text.startswith("/start") or text.startswith("/help"):
        await send_message(
            chat_id=chat_id,
            text=(
                "Send me notes normally. To open your dashboard, type /link and copy the access token. "
                "The same token is required for your graph, search, and reminders."
            ),
        )
        return

    if not text:
        await send_message(chat_id=chat_id, text="Please send text only for now.")
        return

    # Check if user is replying with a time to a pending reminder prompt.
    pending_message_id = get_pending_reminder(user_id)
    if pending_message_id:
        parsed_time = parse_reminder_time(text)
        if parsed_time:
            # User is providing a time for the pending message.
            try:
                reminder = create_reminder(
                    message_id=pending_message_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    when="custom",  # New field to handle custom times.
                    custom_time=parsed_time,
                )
                clear_pending_reminder(user_id)
                await send_message(
                    chat_id=chat_id,
                    text=f"Reminder set for {parsed_time.isoformat()} UTC",
                )
                return
            except Exception as exc:
                logger.exception("Failed to create NLP reminder: %s", exc)
                await send_message(
                    chat_id=chat_id,
                    text="I could not save that reminder. Please try again.",
                )
                return
        # If no time was parsed, treat this as a new message (fall through).
        clear_pending_reminder(user_id)

    # Normal message flow: save and ask for reminder.
    try:
        created = create_message_and_embedding(
            user_id=user_id,
            chat_id=chat_id,
            text=text,
        )

        # Store that this user now has a pending reminder for this message.
        set_pending_reminder(user_id, created["id"])

        await send_message(
            chat_id=created["chat_id"],
            text=(
                "Do you want to be reminded about this? "
                "You can:\n"
                "1. Click the buttons below\n"
                "2. Reply with a time like 'tomorrow 12pm' or 'next friday 3pm'"
            ),
            reply_markup=reminder_buttons(created["id"]),
        )
    except Exception as exc:
        logger.exception("Failed to process Telegram message: %s", exc)
        await send_message(
            chat_id=chat_id,
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
    user_id = callback["from"]["id"]

    if when == "no":
        await answer_callback_query(callback["id"], text="No reminder set")
        await send_message(chat_id=callback["message"]["chat"]["id"], text="Okay, no reminder set.")
        clear_pending_reminder(user_id)
        return

    try:
        reminder = create_reminder(
            message_id=message_id,
            user_id=user_id,
            chat_id=callback["message"]["chat"]["id"],
            when=when,
        )

        await answer_callback_query(callback["id"], text="Reminder set")
        await send_message(
            chat_id=callback["message"]["chat"]["id"],
            text=f"Reminder saved for {reminder['remind_at'].isoformat()} UTC",
        )
        clear_pending_reminder(user_id)
    except Exception as exc:
        logger.exception("Failed to create reminder: %s", exc)
        await answer_callback_query(callback["id"], text="Could not save reminder")
        await send_message(
            chat_id=callback["message"]["chat"]["id"],
            text="I could not save that reminder. Please try again after checking the backend.",
        )
