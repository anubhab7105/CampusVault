"""Notifications domain request/response schemas (Pydantic v2)."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    data: dict[str, Any] | None
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountOut(BaseModel):
    unread_count: int


class MarkAllReadOut(BaseModel):
    updated_count: int


class NotificationCreateInternal(BaseModel):
    """
    NOT exposed via any REST route (see API_SPEC_NOTIFICATIONS.md: "No Public
    Create Endpoint"). Used only as the in-process service-layer contract
    other domains call into, e.g. from the Chat service on message.new.
    """
    user_id: uuid.UUID
    type: str
    title: str
    body: str | None = None
    data: dict[str, Any] | None = None
