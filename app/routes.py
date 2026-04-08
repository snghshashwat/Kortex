from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from urllib.parse import quote_plus

from app.auth import require_user_id
from app.config import settings
from app.models import (
    GoogleCalendarConnectResponse,
    GoogleCalendarStatus,
    MessageIn,
    MessageOut,
    ReminderRecord,
    SearchResult,
)
from app.services.graph_service import build_context_graph
from app.services.google_oauth_service import (
    build_google_calendar_auth_url,
    complete_google_calendar_oauth,
    disconnect_google_calendar,
    get_google_calendar_status,
)
from app.services.messages_service import create_message_and_embedding, search_messages
from app.services.reminders_service import list_reminders

router = APIRouter()


@router.post("/message", response_model=MessageOut)
def post_message(payload: MessageIn, current_user_id: int = Depends(require_user_id)):
    """
    Manual message ingestion endpoint.
    Useful for testing without Telegram.
    """
    if payload.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Token does not match requested user")

    return create_message_and_embedding(
        user_id=current_user_id,
        chat_id=payload.chat_id,
        text=payload.text,
    )


@router.get("/search", response_model=list[SearchResult])
def get_search(
    q: str = Query(..., min_length=2, description="Natural language query"),
    limit: int = Query(5, ge=1, le=20),
    current_user_id: int = Depends(require_user_id),
):
    return search_messages(user_id=current_user_id, query=q, limit=limit)


@router.get("/reminders", response_model=list[ReminderRecord])
def get_reminders(current_user_id: int = Depends(require_user_id)):
    try:
        return list_reminders(user_id=current_user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/graph")
def get_context_graph(
    similarity_threshold: float = Query(0.7, ge=0, le=1, description="Min similarity to show edge"),
    limit: int = Query(20, ge=1, le=100, description="Max messages to include"),
    current_user_id: int = Depends(require_user_id),
):
    """
    Get a context graph of semantic relationships between user's notes.
    
    Returns nodes (messages) and edges (semantic connections).
    Useful for visualizing knowledge structure.
    """
    try:
        return build_context_graph(
            user_id=current_user_id,
            similarity_threshold=similarity_threshold,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/auth/me")
def get_current_user(current_user_id: int = Depends(require_user_id)):
    return {"telegram_user_id": current_user_id}


@router.get("/google/calendar/status", response_model=GoogleCalendarStatus)
def get_google_calendar_connection_status(current_user_id: int = Depends(require_user_id)):
    return get_google_calendar_status(current_user_id)


@router.post("/google/calendar/connect", response_model=GoogleCalendarConnectResponse)
def get_google_calendar_connect_url(current_user_id: int = Depends(require_user_id)):
    try:
        return {"authorization_url": build_google_calendar_auth_url(current_user_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/google/calendar/disconnect")
def disconnect_google_calendar_account(current_user_id: int = Depends(require_user_id)):
    disconnect_google_calendar(current_user_id)
    return {"ok": True}


@router.get("/google/calendar/callback")
def google_calendar_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    frontend_base_url = (settings.frontend_base_url or settings.public_base_url).rstrip("/")

    if error:
        return RedirectResponse(url=f"{frontend_base_url}/?google_calendar_error={quote_plus(error)}", status_code=302)

    if not code or not state:
        return RedirectResponse(
            url=f"{frontend_base_url}/?google_calendar_error=missing_code_or_state",
            status_code=302,
        )

    try:
        complete_google_calendar_oauth(code=code, state=state)
    except Exception as exc:
        return RedirectResponse(url=f"{frontend_base_url}/?google_calendar_error={quote_plus(str(exc))}", status_code=302)

    return RedirectResponse(url=f"{frontend_base_url}/?google_calendar=connected", status_code=302)
