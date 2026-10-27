"""Offline notification fan-out.

Contract: when a chat event or system event targets a user who is not
connected in Redis, the Celery task persists/queues the notification and (if
the user reconnects later) replays via the room join.
"""

from __future__ import annotations

import uuid

from celery import shared_task
from flask import current_app

from celery_app import flask_app


@shared_task(
    name="app.tasks.offline_notifications.queue_online_emit_or_persist",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
)
def queue_online_emit_or_persist(self, *, notification_id: str) -> str:
    """Emit `notification` over Socket.IO if online; else keep it unread."""
    with flask_app().app_context():
        from app.extensions import db
        from app.models import Notification
        from app.repositories import NotificationRepository

        row = NotificationRepository().get_by_id(uuid.UUID(notification_id))
        if row is None:
            return "missing"

        try:
            from app.sockets.handlers import emit_notification_or_persist

            emitted = emit_notification_or_persist(row)
            if not emitted:
                db.session.commit()
            return "emitted" if emitted else "persisted"
        except Exception:
            current_app.logger.exception("offline_notification_failed id=%s", notification_id)
            raise
