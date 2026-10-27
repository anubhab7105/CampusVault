"""Declarative base, UUID primary keys and shared mixins.

Standards (docs/03_DATABASE_GUIDE.md):
- UUID primary keys on every table
- created_at/updated_at on every table, timezone-aware UTC
- soft delete *where required* via ``SoftDeleteMixin``
- generic SQLAlchemy types that compile to PostgreSQL ``UUID``/``JSONB``
  (the Supabase target) while staying testable on SQLite
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.extensions import db

# JSONB in production/Supabase; plain JSON on other dialects (tests).
JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
UUIDType = sa.Uuid(as_uuid=True)


class UuidPk:
    """Mixin column: UUID primary key generated client-side."""

    id = sa.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    created_at = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.text("CURRENT_TIMESTAMP"),
    )


class SoftDeleteMixin:
    """Soft delete via ``deleted_at``; repository helpers filter it out."""

    deleted_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class BaseModel(db.Model, UuidPk, TimestampMixin):
    """Abstract base for every concrete model in this project."""

    __abstract__ = True

    def to_dict(self) -> dict:
        """Lightweight default serialization (extend in feature models)."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


__all__ = ["BaseModel", "JSONType", "SoftDeleteMixin", "TimestampMixin", "UUIDType"]
