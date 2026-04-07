from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_user_id
from app.models import MessageIn, MessageOut, ReminderRecord, SearchResult
from app.services.graph_service import build_context_graph
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
