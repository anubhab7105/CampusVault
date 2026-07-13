"""
Notifications blueprint. Per API_SPEC_NOTIFICATIONS.md's "No Public Create
Endpoint" section: there is intentionally no POST route here. Notifications
are only created via NotificationsService.create_for_user, called directly
by other domains' services (see ChatService._notify_offline_participants).
"""
import uuid

from flask import Blueprint, g, request

from app.middleware.auth_middleware import require_auth
from app.services.notifications_service import NotificationsService
from app.utils.responses import success

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


def _get_service() -> NotificationsService:
    from flask import current_app
    return NotificationsService(db=current_app.extensions["db_session"](), socketio=current_app.extensions.get("socketio"))


def _serialize(n) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "data": n.data,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat(),
    }


@notifications_bp.get("")
@require_auth
def list_notifications():
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    before = request.args.get("before")
    limit = int(request.args.get("limit", 20))

    service = _get_service()
    result = service.list_notifications(g.user_id, unread_only, uuid.UUID(before) if before else None, limit)
    return success({
        "items": [_serialize(n) for n in result["items"]],
        "has_more": result["has_more"],
        "next_cursor": str(result["next_cursor"]) if result["next_cursor"] else None,
        "unread_count": result["unread_count"],
    })


@notifications_bp.get("/unread-count")
@require_auth
def unread_count():
    service = _get_service()
    return success({"unread_count": service.get_unread_count(g.user_id)})


@notifications_bp.patch("/<uuid:notification_id>/read")
@require_auth
def mark_read(notification_id: uuid.UUID):
    service = _get_service()
    notification = service.mark_read(notification_id, g.user_id)
    return success(_serialize(notification))


@notifications_bp.post("/mark-all-read")
@require_auth
def mark_all_read():
    service = _get_service()
    updated_count = service.mark_all_read(g.user_id)
    return success({"updated_count": updated_count})
