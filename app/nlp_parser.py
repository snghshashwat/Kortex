from datetime import datetime, timezone

try:
    from dateparser.search import search_dates
except ImportError:
    search_dates = None


def parse_reminder_time(text: str) -> datetime | None:
    """
    Try to parse a natural language time expression.
    Returns a datetime in UTC if successful, None otherwise.
    
    Examples:
    - "tomorrow 12pm"
    - "next friday 3pm"
    - "in 2 hours"
    - "next week"
    """
    if not search_dates:
        return None
    
    try:
        # search_dates returns a list of (text_match, datetime) tuples.
        results = search_dates(text, languages=["en"])
        if results:
            # Take the first matched datetime.
            _, dt = results[0]
            # Ensure it's timezone-aware in UTC.
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
    except Exception:
        pass
    
    return None
