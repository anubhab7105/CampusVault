"""notifications.

Read receipts live on conversation_participants; this table is the cross-cutting
notification stream (shared resource, group mention, moderation, system).
"""

from __future__ import annotations

import sqlalchemy as sa

from app.constants import NOTIFICATION_SYSTEM
from app.models.base import BaseModel, JSONType, UUIDType


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type = sa.Column(
        sa.String(64),
        nullable=False,
        default=NOTIFICATION_SYSTEM,
        server_default=sa.text("'system'"),
    )
    title = sa.Column(sa.String(160), nullable=False)
    body = sa.Column(sa.String(500), nullable=True)
    payload = sa.Column(JSONType, nullable=True)

    is_read = sa.Column(sa.Boolean, nullable=False, default=False, server_default=sa.text("false"))
    read_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    delivered_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Unread badge query shape.
        sa.Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
        sa.Index("ix_notifications_user_created", "user_id", "created_at"),
    )
