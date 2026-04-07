from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    user_id: int
    chat_id: int
    text: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: str
    user_id: int
    chat_id: int
    text: str
    created_at: datetime


class SearchResult(BaseModel):
    message_id: str
    text: str
    created_at: datetime
    similarity: float


class ReminderRecord(BaseModel):
    id: str
    message_id: str
    remind_at: datetime
    status: Literal["pending", "sent", "cancelled"]


class TelegramWebhookUpdate(BaseModel):
    update_id: int
    message: dict | None = None
    callback_query: dict | None = None
