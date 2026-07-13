"""
Notifications domain service. Implements API_SPEC_NOTIFICATIONS.md.

Per that spec's "No Public Create Endpoint" section: `create_for_user` is
the in-process contract other domains' services call directly — it is
deliberately NOT exposed via any blueprint route. This is the resolution
of the Chat -> Notifications dependency flagged in API_SPEC_CHAT.md.
"""
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.auth_repository import AuthRepository
from app.repositories.notifications_repository import NotificationsRepository
from app.utils import presence
from app.utils.exceptions import ForbiddenError, NotFoundError

logger = logging.getLogger("campusvault.notifications")


class NotificationsService:
    def __init__(self, db: Session, socketio=None):
        self.db = db
        self.repo = NotificationsRepository(db)
        self.auth_repo = AuthRepository(db)
        # socketio is optional/injectable for testability — real callers pass
        # the app's socketio instance so live push actually reaches clients.
        self.socketio = socketio

    # ---------- Internal creation contract (NOT a REST endpoint) ----------

    def create_for_user(
        self, user_id: uuid.UUID, type_: str, title: str, body: str | None = None, data: dict[str, Any] | None = None
    ):
        """
        Called directly by other domains' services (e.g. ChatService on
        message.new for an offline recipient), never by a client request.
        Persists the notification, then — if the user has an active socket
        connection per presence tracking — emits it live. If offline, no
        push happens; the persisted row itself is the durable queue the
        client picks up via GET /notifications on next load, per
        API_SPEC_NOTIFICATIONS.md's "Real-Time Delivery" section.
        """
        notification = self.repo.create(user_id, type_, title, body, data)
        self.db.commit()

        if self.socketio is not None:
            try:
                if presence.is_online(user_id):
                    self.socketio.emit(
                        "notification",
                        self._serialize(notification),
                        room=f"user_{user_id}",
                    )
            except Exception:
                # Presence/emit failures must never block the notification
                # from being persisted — it already committed above; the
                # client will still see it via REST. Log and move on.
                logger.exception("Failed to emit live notification for user %s", user_id)

        return notification

    def _serialize(self, n) -> dict:
        return {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "data": n.data,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat(),
        }

    # ---------- Listing & reading (REST-facing) ----------

    def list_notifications(self, user_id: uuid.UUID, unread_only: bool, before: uuid.UUID | None, limit: int = 20) -> dict:
        items = self.repo.list_for_user(user_id, unread_only, before, limit + 1)
        has_more = len(items) > limit
        page = items[:limit]
        return {
            "items": page,
            "has_more": has_more,
            "next_cursor": page[-1].id if page and has_more else None,
            "unread_count": self.repo.count_unread(user_id),
        }

    def get_unread_count(self, user_id: uuid.UUID) -> int:
        return self.repo.count_unread(user_id)

    def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID):
        notification = self.repo.get_by_id(notification_id)
        if notification is None:
            raise NotFoundError("Notification not found.", code="NOTIFICATION_NOT_FOUND")
        if notification.user_id != user_id:
            raise ForbiddenError("Not the owner of this notification.", code="FORBIDDEN")
        notification = self.repo.mark_read(notification)
        self.db.commit()
        return notification

    def mark_all_read(self, user_id: uuid.UUID) -> int:
        count = self.repo.mark_all_read(user_id)
        self.db.commit()
        return count
