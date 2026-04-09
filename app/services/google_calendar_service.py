from __future__ import annotations

import logging
from datetime import timedelta, timezone

import httpx

from app.services.google_oauth_service import get_valid_google_access_token


logger = logging.getLogger(__name__)
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def sync_reminder_to_calendar(telegram_user_id: int, reminder: dict, message_text: str) -> dict:
    access_token = get_valid_google_access_token(telegram_user_id)
    if not access_token:
        return {
            "status": "not_connected",
            "event_id": None,
            "error": "Google Calendar is not connected for this user",
        }

    remind_at = reminder["remind_at"]
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=timezone.utc)

    end_at = remind_at + timedelta(minutes=15)
    summary_text = " ".join(message_text.split())[:80]
    summary = f"Kortex reminder: {summary_text}" if summary_text else f"Kortex reminder for note {reminder['message_id']}"
    event_body = {
        "summary": summary,
        "description": (
            "Reminder created from Kortex.\n\n"
            f"Telegram user ID: {telegram_user_id}\n"
            f"Reminder ID: {reminder['id']}\n"
            f"Note ID: {reminder['message_id']}\n\n"
            f"Note:\n{message_text}"
        ),
        "start": {"dateTime": remind_at.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_at.isoformat(), "timeZone": "UTC"},
        "extendedProperties": {
            "private": {
                "kortex_reminder_id": reminder["id"],
                "kortex_message_id": reminder["message_id"],
                "kortex_user_id": str(telegram_user_id),
            }
        },
    }

    try:
        response = httpx.post(
            GOOGLE_CALENDAR_EVENTS_URL,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=event_body,
            timeout=20,
        )
        if response.status_code in {401, 403}:
            refreshed_access_token = get_valid_google_access_token(telegram_user_id)
            if refreshed_access_token and refreshed_access_token != access_token:
                response = httpx.post(
                    GOOGLE_CALENDAR_EVENTS_URL,
                    headers={"Authorization": f"Bearer {refreshed_access_token}", "Content-Type": "application/json"},
                    json=event_body,
                    timeout=20,
                )
        response.raise_for_status()
        return {
            "status": "created",
            "event_id": response.json().get("id"),
            "error": None,
        }
    except Exception as exc:
        logger.warning("Failed to sync reminder %s to Google Calendar: %s", reminder["id"], exc)
        return {
            "status": "failed",
            "event_id": None,
            "error": str(exc),
        }