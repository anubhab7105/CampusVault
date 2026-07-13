"""
Chat domain request/response schemas (Pydantic v2).

Shared between REST endpoints and Socket.IO handlers per API_SPEC_CHAT.md's
rule: "no event trusts input just because it's a socket" — the same schemas
validate both surfaces.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.chat import ContentType, GroupType


# ---------- REST: Conversations ----------

class StartDMRequest(BaseModel):
    user_id: uuid.UUID


class LastMessagePreview(BaseModel):
    content: str | None
    sender_id: uuid.UUID
    created_at: datetime


class ConversationOut(BaseModel):
    id: uuid.UUID
    type: str
    last_message: LastMessagePreview | None = None
    unread_count: int = 0

    model_config = {"from_attributes": True}


# ---------- REST: Message history ----------

class ReceiptSummary(BaseModel):
    delivered_count: int
    read_count: int


class MessageOut(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    content: str | None
    content_type: ContentType
    edited_at: datetime | None
    deleted: bool = False
    created_at: datetime
    receipt_summary: ReceiptSummary | None = None

    model_config = {"from_attributes": True}


# ---------- REST: Groups ----------

class GroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = None


class GroupUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = None


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    type: GroupType
    conversation_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class GroupMemberAddRequest(BaseModel):
    user_id: uuid.UUID


# ---------- Socket.IO event payloads ----------

class JoinGroupEvent(BaseModel):
    conversation_id: uuid.UUID


class SendMessageEvent(BaseModel):
    conversation_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=10_000)
    content_type: ContentType = ContentType.TEXT


class EditMessageEvent(BaseModel):
    message_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=10_000)


class DeleteMessageEvent(BaseModel):
    message_id: uuid.UUID


class TypingEvent(BaseModel):
    conversation_id: uuid.UUID
    is_typing: bool


class ReadReceiptEvent(BaseModel):
    message_id: uuid.UUID
