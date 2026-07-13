"""
RBAC blueprint. Every endpoint here requires the admin-only
`require_permission("rbac:manage")` guard per API_SPEC_RBAC.md's scope note.
Controllers stay thin — validation + service call + response only.
"""
import uuid

from flask import Blueprint, g, request

from app.middleware.auth_middleware import require_permission
from app.schemas.rbac import (
    RoleCreateRequest,
    RoleOut,
    RolePermissionsReplaceRequest,
    RoleUpdateRequest,
    UserRolesReplaceRequest,
)
from app.services.rbac_service import RBACService
from app.utils.responses import success

rbac_bp = Blueprint("rbac", __name__, url_prefix="/api/v1/rbac")


def _get_service() -> RBACService:
    from flask import current_app
    return RBACService(db=current_app.extensions["db_session"]())


@rbac_bp.get("/roles")
@require_permission("rbac:manage")
def list_roles():
    service = _get_service()
    roles = service.list_roles()
    items = [RoleOut.model_validate(r).model_dump(mode="json") for r in roles]
    return success({"items": items})


@rbac_bp.post("/roles")
@require_permission("rbac:manage")
def create_role():
    payload = RoleCreateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    role = service.create_role(payload.name, payload.description)
    return success(RoleOut.model_validate(role).model_dump(mode="json"), status=201)


@rbac_bp.patch("/roles/<uuid:role_id>")
@require_permission("rbac:manage")
def update_role(role_id: uuid.UUID):
    payload = RoleUpdateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    role = service.update_role(role_id, payload.name, payload.description)
    return success(RoleOut.model_validate(role).model_dump(mode="json"))


@rbac_bp.delete("/roles/<uuid:role_id>")
@require_permission("rbac:manage")
def delete_role(role_id: uuid.UUID):
    service = _get_service()
    service.delete_role(role_id)
    return success({}, message="Role deleted.")


@rbac_bp.get("/permissions")
@require_permission("rbac:manage")
def list_permissions():
    service = _get_service()
    perms = service.list_permissions()
    return success({"items": perms})


@rbac_bp.put("/roles/<uuid:role_id>/permissions")
@require_permission("rbac:manage")
def replace_role_permissions(role_id: uuid.UUID):
    payload = RolePermissionsReplaceRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    role = service.replace_role_permissions(role_id, payload.permission_codes, actor_user_id=g.user_id)
    return success(RoleOut.model_validate(role).model_dump(mode="json"))


@rbac_bp.get("/users/<uuid:user_id>/roles")
@require_permission("rbac:manage")
def get_user_roles(user_id: uuid.UUID):
    service = _get_service()
    roles = service.get_user_roles(user_id)
    return success({"roles": roles})


@rbac_bp.put("/users/<uuid:user_id>/roles")
@require_permission("rbac:manage")
def replace_user_roles(user_id: uuid.UUID):
    payload = UserRolesReplaceRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    roles = service.replace_user_roles(user_id, payload.role_names, actor_user_id=g.user_id)
    return success({"roles": roles})
