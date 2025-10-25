from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: Optional[str] = None
    avatar_color: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str
    sender: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # optional: sender_email, is_system, etc.
