"""Shared socket emit helpers + notification fan-out logic."""

from __future__ import annotations

from flask_socketio import emit

from app.models import Notification
from app.services.audit_service import audit_service


def emit_notification_to_user(user_id: str, payload: dict) -> bool:
    """Emit a `notification` event to every device of the user (if online)."""
    sent = False
    try:
        from app.services.connections import is_online

        if is_online(user_id):
            emit(
                "notification",
                {"success": True, "message": "New notification.", "data": payload},
                room=user_id,
            )
            sent = True
    except Exception:  # noqa: BLE001 — sockets are best-effort; persistence is the floor
        audit_service.record(action="socket.notification_failed", entity_type="notification")
    return sent


def emit_notification_or_persist(row: Notification) -> bool:
    """Called from the Celery task: emit if online, else row stays unread.

    Returns True when emitted live; False when the notification must remain
    unread in the database until the user next opens the bell.
    """
    user_id = str(row.user_id)
    session_ids = _sessions_of(user_id)
    if not session_ids:
        return False
    payload = {
        "id": str(row.id),
        "notification_type": row.notification_type,
        "title": row.title,
        "body": row.body,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    from app.extensions import socketio

    for sid in session_ids:
        socketio.emit("notification", {"success": True, "message": "New notification.", "data": payload}, to=sid)
    return True


def _sessions_of(user_id: str) -> list[str]:
    from app.utils.redis_utils import get_redis

    members = get_redis().smembers(f"presence:users:{user_id}")
    return [m.decode() if isinstance(m, bytes) else m for m in members]
