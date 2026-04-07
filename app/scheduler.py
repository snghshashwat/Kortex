import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.reminders_service import fetch_due_reminders, mark_reminder_sent
from app.telegram_api import send_message

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


async def process_due_reminders() -> None:
    due_items = fetch_due_reminders(limit=50)

    for item in due_items:
        try:
            await send_message(
                chat_id=item["chat_id"],
                text=f"Reminder about your note:\n\n{item['message_text']}",
            )
            mark_reminder_sent(str(item["id"]))
        except Exception as exc:
            logger.exception("Failed to send reminder %s: %s", item["id"], exc)


def run_due_reminders_job() -> None:
    asyncio.run(process_due_reminders())


def start_scheduler() -> None:
    scheduler.add_job(run_due_reminders_job, "interval", minutes=1, id="due_reminders")
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
