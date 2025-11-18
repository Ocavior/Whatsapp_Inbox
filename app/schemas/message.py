from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.message import MessageDirection, MessageStatus, MessageType


class MessageBase(BaseModel):
    user_id: str
    direction: MessageDirection
    message_type: MessageType
    body: str
    timestamp: datetime


class MessageCreate(MessageBase):
    message_id: Optional[str] = None
    status: MessageStatus = MessageStatus.RECEIVED
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    template_name: Optional[str] = None
    template_params: Optional[Dict[str, Any]] = None


class MessageUpdate(BaseModel):
    status: Optional[MessageStatus] = None
    error_reason: Optional[str] = None
    retry_count: Optional[int] = None


class MessageOut(MessageBase):
    id: str
    status: MessageStatus
    message_id: Optional[str]
    media_url: Optional[str]
    media_type: Optional[str]
    template_name: Optional[str]
    error_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    to: str
    message: str
    message_type: MessageType = MessageType.TEXT
    media_url: Optional[str] = None
    template_name: Optional[str] = None
    template_params: Optional[Dict[str, Any]] = None


class SendMessageResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[int] = None


class MessageListResponse(BaseModel):
    messages: List[MessageOut]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool