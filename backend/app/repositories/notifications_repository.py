"""
Notifications domain repository. Per 04_BACKEND_GUIDE.md: "Database access
goes through repositories." Covers notifications per API_SPEC_NOTIFICATIONS.md.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notifications import Notification


class NotificationsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, user_id: uuid.UUID, type_: str, title: str, body: str | None = None, data: dict[str, Any] | None = None
    ) -> Notification:
        notification = Notification(user_id=user_id, type=type_, title=title, body=body, data=data)
        self.db.add(notification)
        self.db.flush()
        return notification

    def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        return self.db.scalar(select(Notification).where(Notification.id == notification_id))

    def list_for_user(self, user_id: uuid.UUID, unread_only: bool, before_id: uuid.UUID | None, limit: int) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        if before_id is not None:
            before = self.get_by_id(before_id)
            if before is not None:
                from sqlalchemy import and_, or_
                stmt = stmt.where(
                    or_(
                        Notification.created_at < before.created_at,
                        and_(Notification.created_at == before.created_at, Notification.id < before.id),
                    )
                )
        return list(self.db.scalars(stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)))

    def count_unread(self, user_id: uuid.UUID) -> int:
        return self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.read_at.is_(None)
            )
        ) or 0

    def mark_read(self, notification: Notification) -> Notification:
        if notification.read_at is None:  # idempotent
            notification.read_at = datetime.now(timezone.utc)
            self.db.flush()
        return notification

    def mark_all_read(self, user_id: uuid.UUID) -> int:
        unread = list(self.db.scalars(
            select(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        ))
        now = datetime.now(timezone.utc)
        for n in unread:
            n.read_at = now
        self.db.flush()
        return len(unread)
