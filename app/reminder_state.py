"""
Simple in-memory state for tracking pending reminder prompts.
In production, you'd use Redis or a database for this.
"""
from datetime import datetime, timedelta, timezone

# Store (user_id, message_id, timestamp) for messages waiting for reminder times.
# We clean up entries older than 10 minutes.
pending_reminders: dict[int, tuple[str, datetime]] = {}


def set_pending_reminder(user_id: int, message_id: str) -> None:
    """Track that a user is being asked for a reminder time for a message."""
    pending_reminders[user_id] = (message_id, datetime.now(timezone.utc))


def get_pending_reminder(user_id: int) -> str | None:
    """Get the pending message_id for a user, if still valid (< 10 min old)."""
    if user_id not in pending_reminders:
        return None
    
    message_id, timestamp = pending_reminders[user_id]
    now = datetime.now(timezone.utc)
    
    # Expire if older than 10 minutes.
    if now - timestamp > timedelta(minutes=10):
        del pending_reminders[user_id]
        return None
    
    return message_id


def clear_pending_reminder(user_id: int) -> None:
    """Clear the pending reminder for a user."""
    if user_id in pending_reminders:
        del pending_reminders[user_id]
