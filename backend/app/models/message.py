"""messages.

Soft delete: yes — deletes are tombstones so moderators and audit retain the
trail; payloads of deleted messages are wiped by ChatService.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.constants import MESSAGE_TYPE_TEXT
from app.models.base import BaseModel, SoftDeleteMixin, UUIDType


class Message(BaseModel, SoftDeleteMixin):
    __tablename__ = "messages"

    conversation_id = sa.Column(
        UUIDType,
        sa.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    message_type = sa.Column(
        sa.String(16), nullable=False, default=MESSAGE_TYPE_TEXT
    )
    content = sa.Column(sa.Text, nullable=True)
    file_id = sa.Column(
        UUIDType,
        sa.ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    reply_to_id = sa.Column(
        UUIDType,
        sa.ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_edited = sa.Column(
        sa.Boolean, nullable=False, default=False, server_default=sa.text("false")
    )
    edited_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    # Delivery status: null=pending, set when all participants receive it.
    delivered_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Primary chat history index (newest first per room).
        sa.Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        sa.Index("ix_messages_sender_conversation", "sender_id", "conversation_id"),
    )

    def wipe_content(self) -> Message:
        """Tombstone the payload while keeping the audit trail."""
        from app.constants import MESSAGE_TYPE_SYSTEM

        self.content = None
        self.message_type = MESSAGE_TYPE_SYSTEM
        self.is_deleted = True
        return self
