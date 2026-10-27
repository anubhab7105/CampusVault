"""Audit blueprint — admin-only audit trail access."""

from __future__ import annotations

import uuid

from flask import Blueprint, request
from flask_jwt_extended import get_jwt

from app.errors.exceptions import ForbiddenError
from app.middleware.auth import ensure_authenticated
from app.schemas.common import PaginationQuerySchema
from app.services.audit_service import audit_service
from app.utils.pagination import PagingMeta
from app.utils.responses import success_response
from app.utils.validation import load_schema

bp = Blueprint("audit", __name__, url_prefix="/api/v1/audit-logs")


@bp.get("")
def timeline():
    user_id = uuid.UUID(ensure_authenticated())
    if (get_jwt() or {}).get("role") != "Admin":
        raise ForbiddenError("Admin access required.")

    query = load_schema(PaginationQuerySchema(), request.args.to_dict())
    entity_type = request.args.get("entity_type") or None
    action = request.args.get("action") or None

    def _safe_uuid(value: str | None):
        if not value:
            return None
        try:
            return uuid.UUID(value)
        except ValueError:
            return None  # invalid filter values are ignored, never crashes

    rows, total = audit_service.timeline(
        actor_id=_safe_uuid(request.args.get("actor_id")),
        entity_type=entity_type,
        entity_id=_safe_uuid(request.args.get("entity_id")),
        action=action,
        page=query["page"],
        page_size=query["page_size"],
    )
    meta = PagingMeta(query["page"], query["page_size"], total)
    return success_response(
        data={
            "items": [
                {
                    "id": str(row.id),
                    "actor_id": str(row.actor_id) if row.actor_id else None,
                    "action": row.action,
                    "entity_type": row.entity_type,
                    "entity_id": str(row.entity_id) if row.entity_id else None,
                    "changes": row.changes,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]
        },
        paging=meta.as_dict(),
        message="Audit trail loaded.",
    )
