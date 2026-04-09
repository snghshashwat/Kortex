from datetime import datetime, timedelta, timezone

from app.db import get_db
from app.services.google_calendar_service import sync_reminder_to_calendar


def create_reminder(message_id: str, user_id: int, chat_id: int, when: str, custom_time: datetime | None = None) -> dict:
    now = datetime.now(timezone.utc)

    if when == "tomorrow":
        remind_at = now + timedelta(days=1)
    elif when == "next_week":
        remind_at = now + timedelta(days=7)
    elif when == "custom":
        if not custom_time:
            raise ValueError("custom_time must be provided when when='custom'")
        remind_at = custom_time
    else:
        raise ValueError("Unsupported reminder option")

    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO reminders (message_id, telegram_user_id, chat_id, remind_at, status)
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING id, message_id, remind_at, status;
            """,
            (message_id, user_id, chat_id, remind_at),
        )
        reminder = cur.fetchone()
        cur.execute(
            """
            SELECT message_text
            FROM messages
            WHERE id = %s AND telegram_user_id = %s;
            """,
            (message_id, user_id),
        )
        message_row = cur.fetchone()
        conn.commit()

    message_text = message_row["message_text"] if message_row else ""
    sync_result = sync_reminder_to_calendar(user_id, reminder, message_text=message_text)

    with get_db() as (conn, cur):
        cur.execute(
            """
            UPDATE reminders
            SET google_event_id = %s,
                google_sync_status = %s,
                google_sync_error = %s,
                google_synced_at = NOW()
            WHERE id = %s;
            """,
            (
                sync_result.get("event_id"),
                sync_result.get("status"),
                sync_result.get("error"),
                reminder["id"],
            ),
        )
        conn.commit()

    return {
        "id": str(reminder["id"]),
        "message_id": str(reminder["message_id"]),
        "remind_at": reminder["remind_at"],
        "status": reminder["status"],
    }


def list_reminders(user_id: int) -> list[dict]:
    with get_db() as (_, cur):
        cur.execute(
            """
            SELECT id, message_id, remind_at, status
            FROM reminders
            WHERE telegram_user_id = %s
            ORDER BY remind_at ASC;
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    return [
        {
            "id": str(row["id"]),
            "message_id": str(row["message_id"]),
            "remind_at": row["remind_at"],
            "status": row["status"],
        }
        for row in rows
    ]


def fetch_due_reminders(limit: int = 50) -> list[dict]:
    with get_db() as (_, cur):
        cur.execute(
            """
            SELECT r.id, r.chat_id, r.message_id, m.message_text
            FROM reminders r
            JOIN messages m ON m.id = r.message_id
            WHERE r.status = 'pending' AND r.remind_at <= NOW()
            ORDER BY r.remind_at ASC
            LIMIT %s;
            """,
            (limit,),
        )
        return cur.fetchall()


def mark_reminder_sent(reminder_id: str) -> None:
    with get_db() as (conn, cur):
        cur.execute(
            """
            UPDATE reminders
            SET status = 'sent', sent_at = NOW()
            WHERE id = %s AND status = 'pending';
            """,
            (reminder_id,),
        )
        conn.commit()
