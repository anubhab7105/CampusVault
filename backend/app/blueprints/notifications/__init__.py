"""Notifications blueprint."""

from __future__ import annotations

import uuid

from flask import Blueprint, request

from app.middleware.auth import ensure_authenticated
from app.services.notification_service import notification_service
from app.utils.pagination import PagingMeta, parse_pagination_args
from app.utils.responses import success_response

bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


def _serialize(n) -> dict:
    return {
        "id": str(n.id),
        "notification_type": n.notification_type,
        "title": n.title,
        "body": n.body,
        "is_read": n.is_read,
        "payload": n.payload,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@bp.get("")
def list_notifications():
    user_id = uuid.UUID(ensure_authenticated())
    page, page_size, _ = parse_pagination_args(request.args.get("page"), request.args.get("page_size"))
    rows, total = notification_service.list_for_user(
        user_id,
        unread_only=request.args.get("unread") == "true",
        page=page,
        page_size=page_size,
    )
    meta = PagingMeta(page, page_size, total)
    return success_response(
        data={"items": [_serialize(n) for n in rows]},
        paging=meta.as_dict(),
        message="Notifications listed.",
    )


@bp.get("/unread-count")
def unread_count():
    user_id = uuid.UUID(ensure_authenticated())
    return success_response(
        data={"count": notification_service.unread_count(user_id)},
        message="Unread count loaded.",
    )


@bp.post("/<uuid:notification_id>/read")
def mark_read(notification_id: uuid.UUID):
    user_id = uuid.UUID(ensure_authenticated())
    updated = notification_service.mark_read(notification_id, user_id)
    if updated == 0:
        from app.errors.exceptions import NotFoundError

        raise NotFoundError("Notification not found.")
    return success_response(message="Marked read.")


@bp.post("/read-all")
def mark_all_read():
    user_id = uuid.UUID(ensure_authenticated())
    count = notification_service.mark_all_read(user_id)
    return success_response(data={"updated": count}, message="All notifications read.")
