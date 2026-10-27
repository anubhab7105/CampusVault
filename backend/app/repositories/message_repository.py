"""Message persistence: history retrieval + counter updates."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from app.extensions import db
from app.models import Message
from app.repositories.base_repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    model = Message

    def history(
        self,
        conversation_id: uuid.UUID,
        *,
        before_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> Sequence[Message]:
        """Newest-first page; ``before_id`` is the cursor (keyset pagination)."""
        stmt = sa.select(Message).where(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
        )
        if before_id is not None:
            anchor = self.get_by_id(before_id)
            if anchor is not None:
                stmt = stmt.where(Message.created_at < anchor.created_at)
        stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
        return db.session.scalars(stmt).all()

    def last_for_conversation(self, conversation_id: uuid.UUID) -> Message | None:
        stmt = (
            sa.select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        return db.session.scalar(stmt)

    def mark_delivered(self, message_id: uuid.UUID, delivered_at) -> int:
        stmt = (
            sa.update(Message)
            .where(Message.id == message_id, Message.delivered_at.is_(None))
            .values(delivered_at=delivered_at)
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)
