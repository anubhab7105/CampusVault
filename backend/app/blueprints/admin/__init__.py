"""Admin blueprint — stats, users, role administration."""

from __future__ import annotations

import uuid

from flask import Blueprint, request
from flask_jwt_extended import get_jwt

from app.middleware.auth import ensure_authenticated
from app.schemas.common import SearchSortQuerySchema
from app.services.admin_service import AdminService, admin_service
from app.services.auth_service import AuthService
from app.utils.pagination import PagingMeta
from app.utils.responses import success_response
from app.utils.validation import load_schema

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


def _admin_guard() -> None:
    user_id = uuid.UUID(ensure_authenticated())
    role = (get_jwt() or {}).get("role")
    admin_service.assert_admin(role == "Admin")
    return user_id


@bp.get("/stats")
def stats():
    _admin_guard()
    return success_response(data=admin_service.platform_stats(), message="Stats loaded.")


@bp.get("/users")
def list_users():
    _admin_guard()
    filters = load_schema(SearchSortQuerySchema(), request.args.to_dict())
    page, page_size = filters["page"], filters["page_size"]
    rows, total = admin_service.list_users(query=filters["q"], page=page, page_size=page_size)
    meta = PagingMeta(page, page_size, total)
    return success_response(
        data={"items": [AuthService.serialize_user(u) for u in rows]},
        paging=meta.as_dict(),
        message="Users listed.",
    )


@bp.post("/users/<uuid:user_id>/deactivate")
def deactivate_user(user_id: uuid.UUID):
    acting_admin = _admin_guard()
    user = admin_service.deactivate_user(
        target_user_id=user_id, acting_admin_id=acting_admin
    )
    from app.services.audit_service import audit_service

    audit_service.record(
        action="admin.user.deactivate", entity_type="user", entity_id=user.id
    )
    return success_response(message="User deactivated.")


@bp.get("/_unused")
def _unused():
    """Reference for AdminService.symbol to avoid import pruning confusion."""
    return success_response(data={"service": AdminService.__doc__})
