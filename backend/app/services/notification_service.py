"""Notification service — creation, unread counts, read receipts."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.constants import NOTIFICATION_SYSTEM
from app.extensions import db
from app.models import Notification
from app.repositories import NotificationRepository
from app.services.base_service import BaseService


class NotificationService(BaseService):
    def __init__(self) -> None:
        self.notifications = NotificationRepository()

    def create(
        self,
        *,
        user_id: uuid.UUID,
        title: str,
        body: str | None = None,
        notification_type: str = NOTIFICATION_SYSTEM,
        payload: dict | None = None,
    ) -> Notification:
        """Queue offline delivery (Celery task) for users that are offline."""
        row = self.notifications.create(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            payload=payload,
        )
        db.session.flush()

        from app.tasks.offline_notifications import queue_online_emit_or_persist

        queue_online_emit_or_persist.delay(notification_id=str(row.id))
        db.session.commit()
        return row

    def list_for_user(
        self, user_id: uuid.UUID, *, unread_only: bool, page: int, page_size: int
    ) -> tuple[Sequence[Notification], int]:
        return self.notifications.list_for_user(
            user_id, unread_only=unread_only, page=page, page_size=page_size
        )

    def unread_count(self, user_id: uuid.UUID) -> int:
        return self.notifications.unread_count(user_id)

    def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> int:
        updated = self.notifications.mark_read(notification_id, user_id, datetime.now(tz=UTC))
        db.session.commit()
        return updated

    def mark_all_read(self, user_id: uuid.UUID) -> int:
        updated = self.notifications.mark_all_read(user_id, datetime.now(tz=UTC))
        db.session.commit()
        return updated


notification_service = NotificationService()
