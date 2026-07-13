"""
Shared SQLAlchemy base and mixins for all CampusVault models.

Per 03_DATABASE_GUIDE.md:
- UUID primary keys
- created_at / updated_at on mutable records
- soft delete (deleted_at) where records are user-facing and recoverable
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all models."""
    pass


class UUIDPKMixin:
    """Adds a UUID primary key, matching the project-wide UUID PK standard."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Adds created_at / updated_at columns."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtOnlyMixin:
    """For append-only / log-style tables (audit_logs, receipts, otp_codes)."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """
    Adds deleted_at for soft delete.

    IMPORTANT: repositories must filter `deleted_at IS NULL` on all default
    reads. Never physically delete rows on tables using this mixin.
    """
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
