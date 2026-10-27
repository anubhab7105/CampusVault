"""audit_logs — append-only, immutable, no soft delete.

Records login, logout, uploads, downloads and admin actions. Rows are written
in the same transaction as the business change where possible
(AuditService.record), and are never updated or deleted by application code.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models.base import BaseModel, JSONType, UUIDType


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    actor_id = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = sa.Column(sa.String(64), nullable=False)  # e.g. auth.login, admin.role.assign
    entity_type = sa.Column(sa.String(64), nullable=False, index=True)
    entity_id = sa.Column(UUIDType, nullable=True)

    request_context = sa.Column(JSONType, nullable=True)  # ip, user_agent, request_id
    changes = sa.Column(JSONType, nullable=True)  # before/after diff summary

    __table_args__ = (
        # Timeline per actor and per entity; both are common admin queries.
        sa.Index("ix_audit_logs_actor_created", "actor_id", "created_at"),
        sa.Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        sa.Index("ix_audit_logs_action_created", "action", "created_at"),
    )
