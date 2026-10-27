"""teacher_allowlist — admin-managed allowlist of pre-approved teacher emails."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Boolean,
    ForeignKey,
    Index,
    func,
    Uuid as SqlAlchemyUuid,
)
from sqlalchemy.orm import relationship

from app.extensions import db
from app.models.base import BaseModel, UUIDType


class TeacherAllowlist(BaseModel):
    __tablename__ = "teacher_allowlist"

    id = Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    email = Column(
        String(255),
        nullable=False,
        unique=True,
    )
    is_approved = Column(
        Boolean,
        nullable=False,
        default=False,
    )
    approved_by = Column(
        SqlAlchemyUuid,
        ForeignKey("users.id"),
        nullable=True,
    )
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
    ),

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TeacherAllowlist id={self.id} email={self.email!r} approved={self.is_approved}>"