from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.message import MessageDirection


class ConversationOut(BaseModel):
    user_id: str
    user_name: Optional[str]
    last_message: str
    last_message_timestamp: datetime
    last_message_direction: MessageDirection
    unread_count: int
    total_messages: int
    is_archived: bool
    labels: List[str]
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: List[ConversationOut]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


class ConversationUpdate(BaseModel):
    user_name: Optional[str] = None
    is_archived: Optional[bool] = None
    labels: Optional[List[str]] = None