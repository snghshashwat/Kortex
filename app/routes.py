from fastapi import APIRouter, HTTPException, Query

from app.models import MessageIn, MessageOut, ReminderRecord, SearchResult
from app.services.messages_service import create_message_and_embedding, search_messages
from app.services.reminders_service import list_reminders

router = APIRouter()


@router.post("/message", response_model=MessageOut)
def post_message(payload: MessageIn):
    """
    Manual message ingestion endpoint.
    Useful for testing without Telegram.
    """
    return create_message_and_embedding(
        user_id=payload.user_id,
        chat_id=payload.chat_id,
        text=payload.text,
    )


@router.get("/search", response_model=list[SearchResult])
def get_search(
    user_id: int = Query(..., description="Telegram user ID"),
    q: str = Query(..., min_length=2, description="Natural language query"),
    limit: int = Query(5, ge=1, le=20),
):
    return search_messages(user_id=user_id, query=q, limit=limit)


@router.get("/reminders", response_model=list[ReminderRecord])
def get_reminders(user_id: int = Query(..., description="Telegram user ID")):
    try:
        return list_reminders(user_id=user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
