"""
Audit domain model. Append-only per 06_SECURITY_GUIDE.md — logs login, logout,
uploads, downloads, and admin actions. Never soft-deleted, never mutated.
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtOnlyMixin, UUIDPKMixin


class AuditLog(Base, UUIDPKMixin, CreatedAtOnlyMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )  # null = unauthenticated / system event
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # "login", "upload", "role.assign"...
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
