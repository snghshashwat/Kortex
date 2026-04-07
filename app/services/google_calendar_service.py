"""Optional Google Calendar sync for reminder creation."""

from __future__ import annotations

import json
import logging
from datetime import timedelta, timezone
from pathlib import Path

from app.config import settings


logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def _is_enabled() -> bool:
    return bool(settings.google_calendar_sync_reminders and settings.google_calendar_id)


def _load_service_account_info() -> dict | None:
    try:
        if settings.google_service_account_json:
            return json.loads(settings.google_service_account_json)

        if settings.google_service_account_file:
            return json.loads(Path(settings.google_service_account_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Invalid Google service account credentials: %s", exc)
        return None

    return None


def _build_calendar_service():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        logger.warning("Google Calendar dependencies are not installed: %s", exc)
        return None

    info = _load_service_account_info()
    if not info:
        logger.warning("Google Calendar sync is enabled, but no service account credentials were provided.")
        return None

    credentials = service_account.Credentials.from_service_account_info(info, scopes=[GOOGLE_CALENDAR_SCOPE])
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def sync_reminder_to_calendar(reminder: dict, message_text: str, user_id: int) -> str | None:
    if not _is_enabled():
        return None

    service = _build_calendar_service()
    if service is None:
        return None

    remind_at = reminder["remind_at"]
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=timezone.utc)

    end_at = remind_at + timedelta(minutes=15)
    summary_text = " ".join(message_text.split())[:80]
    summary = f"Kortex reminder: {summary_text}" if summary_text else f"Kortex reminder for note {reminder['message_id']}"
    description = (
        "Reminder created from Kortex.\n\n"
        f"Telegram user ID: {user_id}\n"
        f"Reminder ID: {reminder['id']}\n"
        f"Note ID: {reminder['message_id']}\n\n"
        f"Note:\n{message_text}"
    )

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": remind_at.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_at.isoformat(), "timeZone": "UTC"},
        "extendedProperties": {
            "private": {
                "kortex_reminder_id": reminder["id"],
                "kortex_message_id": reminder["message_id"],
                "kortex_user_id": str(user_id),
            }
        },
    }

    try:
        event = service.events().insert(calendarId=settings.google_calendar_id, body=event_body).execute()
        return event.get("id")
    except Exception as exc:
        logger.warning("Failed to sync reminder %s to Google Calendar: %s", reminder["id"], exc)
        return None