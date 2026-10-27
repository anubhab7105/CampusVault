"""Notification persistence."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from app.extensions import db
from app.models import Notification
from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def list_for_user(
        self, user_id: uuid.UUID, *, unread_only: bool, page: int, page_size: int
    ) -> tuple[Sequence[Notification], int]:
        conditions = [Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))
        return self.paginate(
            page,
            page_size,
            *conditions,
            order_by=Notification.created_at.desc(),
        )

    def unread_count(self, user_id: uuid.UUID) -> int:
        stmt = (
            sa.select(sa.func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return int(db.session.scalar(stmt) or 0)

    def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID, read_at) -> int:
        """Ownership is enforced in the WHERE clause — never trust the client."""
        stmt = (
            sa.update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True, read_at=read_at)
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)

    def mark_all_read(self, user_id: uuid.UUID, read_at) -> int:
        stmt = (
            sa.update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=read_at)
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)
