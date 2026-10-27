"""RBAC blueprint — browse roles/permissions; manage assignments (admin)."""

from __future__ import annotations

import uuid

from flask import Blueprint, request
from marshmallow import Schema, fields, validate

from app.extensions import db
from app.middleware.rbac import permission_required
from app.repositories import RoleRepository
from app.services.role_service import RoleService
from app.utils.responses import success_response
from app.utils.validation import get_json_body, load_schema

bp = Blueprint("rbac", __name__, url_prefix="/api/v1/rbac")

roles_repo = RoleRepository()
service = RoleService()


class GrantPermissionSchema(Schema):
    permission_codes = fields.List(
        fields.Str(validate=validate.Length(min=3, max=64)),
        required=True,
        validate=validate.Length(min=1, max=50),
    )


@bp.get("/roles")
@permission_required("admin:roles:manage")
def list_roles():
    roles = roles_repo.list_all()
    return success_response(
        data={
            "items": [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "description": role.description,
                    "is_system": role.is_system,
                    "permissions": [p.code for p in role.permissions],
                }
                for role in roles
            ]
        },
        message="Roles listed.",
    )


@bp.get("/permissions")
@permission_required("admin:roles:manage")
def list_permissions():
    permissions = service.permissions.list_all()
    return success_response(
        data={"items": [{"id": str(p.id), "code": p.code, "module": p.module} for p in permissions]},
        message="Permissions listed.",
    )


@bp.post("/roles/<uuid:role_id>/permissions")
@permission_required("admin:roles:manage")
def grant_permissions(role_id: uuid.UUID):
    """Grant (idempotent) permission codes to a role."""
    body = load_schema(GrantPermissionSchema(), get_json_body())
    role = roles_repo.get_by_id(role_id)
    if role is None:
        from app.errors.exceptions import NotFoundError

        raise NotFoundError("Role not found.")
    for code in body["permission_codes"]:
        permission = service.permissions.get_by_code(code)
        if permission is None:
            from app.errors.exceptions import ValidationError

            raise ValidationError(f"Unknown permission: {code}")
        service.permissions.grant_to_role(role.id, permission.id)
    db.session.commit()
    return success_response(message="Permissions granted.")


@bp.delete("/roles/<uuid:role_id>/permissions/<code>")
@permission_required("admin:roles:manage")
def revoke_permission(role_id: uuid.UUID, code: str):
    permission = service.permissions.get_by_code(code)
    if permission is None:
        from app.errors.exceptions import NotFoundError

        raise NotFoundError("Permission not found.")
    service.permissions.revoke_from_role(role_id, permission.id)
    db.session.commit()
    return success_response(message="Permission revoked.")


@bp.post("/users/<uuid:user_id>/roles")
@permission_required("admin:users:manage")
def assign_role(user_id: uuid.UUID):
    """Assign a role to a user (single primary role model)."""

    class AssignRoleSchema(Schema):
        role_name = fields.Str(required=True, validate=validate.Length(min=3, max=64))

    body = load_schema(AssignRoleSchema(), get_json_body())
    from app.services.admin_service import admin_service

    admin_service.assert_admin(True)
    role = roles_repo.get_by_name(body["role_name"])
    if role is None:
        from app.errors.exceptions import NotFoundError

        raise NotFoundError("Role not found.")
    if roles_repo.get_user_roles(user_id) and any(
        r.name == body["role_name"] for r in roles_repo.get_user_roles(user_id)
    ):
        return success_response(message="Role already assigned.")
    request.environ.get("REQUESTED_USER_ID")  # set by middleware
    roles_repo.assign_role(user_id, role.id, assigned_by=None)
    db.session.commit()
    return success_response(message="Role assigned.")
