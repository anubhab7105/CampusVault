"""Users blueprint — self-service profile + admin user listing."""

from __future__ import annotations

import uuid

from flask import Blueprint, request

from app.middleware.auth import ensure_authenticated
from app.middleware.rbac import permission_required
from app.repositories import UserRepository
from app.services.auth_service import AuthService
from app.utils.pagination import parse_pagination_args
from app.utils.responses import success_response
from app.utils.validation import ValidationError

bp = Blueprint("users", __name__, url_prefix="/api/v1/users")

users_repo = UserRepository()


@bp.get("/me")
def get_me():
    user_id = uuid.UUID(ensure_authenticated())
    user = users_repo.get_active_by_id(user_id)
    if user is None:
        raise ValidationError("Account not found.")
    return success_response(
        data=AuthService.serialize_user(user), message="Profile loaded."
    )


@bp.get("")
@permission_required("admin:users:manage")
def list_users():
    page, page_size, _ = parse_pagination_args(
        request.args.get("page"), request.args.get("page_size")
    )
    rows, total = users_repo.search(request.args.get("q"), page, page_size)
    from app.utils.pagination import PagingMeta

    meta = PagingMeta(page, page_size, total)
    return success_response(
        data={"items": [AuthService.serialize_user(u) for u in rows]},
        paging=meta.as_dict(),
        message="Users listed.",
    )
