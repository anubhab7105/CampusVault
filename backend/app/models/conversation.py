"""conversations + conversation_participants.

A conversation is either a 1:1 mirror of a group (type=group, group_id set)
or a direct message pair (type=direct, exactly two participants enforced in
ChatService, not by ORM).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import func

from app.extensions import db
from app.models.base import BaseModel, UUIDType


class Conversation(BaseModel):
    __tablename__ = "conversations"

    conversation_type = sa.Column(sa.String(16), nullable=False, index=True)
    group_id = sa.Column(
        UUIDType,
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )
    created_by = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_message_at = sa.Column(sa.DateTime(timezone=True), nullable=True, index=True)
    is_active = sa.Column(
        sa.Boolean, nullable=False, default=True, server_default=sa.text("true")
    )

    __table_args__ = (
        sa.Index("ix_conversations_type_last_msg", "conversation_type", "last_message_at"),
    )


class ConversationParticipant(db.Model):
    __tablename__ = "conversation_participants"

    conversation_id = sa.Column(
        UUIDType,
        sa.ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    joined_at = sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_admin = sa.Column(
        sa.Boolean, nullable=False, default=False, server_default=sa.text("false")
    )
    # Read receipts + unread counts power the notification badge.
    last_read_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (sa.Index("ix_conv_participants_user", "user_id"),)
