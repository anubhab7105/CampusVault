"""Admin blueprint — stats, users, role administration, academic CRUD, groups, resources, moderation, allowlist, audit."""

from __future__ import annotations

import uuid

from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import Schema, fields, validate

from app.extensions import db
from app.middleware.auth import ensure_authenticated
from app.schemas.common import SearchSortQuerySchema, PaginationQuerySchema
from app.services.admin_service import admin_service
from app.services.auth_service import AuthService
from app.utils.pagination import PagingMeta
from app.utils.responses import success_response, error_response
from app.utils.validation import get_json_body, load_schema
import io
import csv

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


def _admin_guard() -> uuid.UUID:
    """Ensure the caller is admin; return the admin's user_id."""
    user_id = uuid.UUID(ensure_authenticated())
    role = (get_jwt() or {}).get("role")
    admin_service.assert_admin(role == "Admin")
    return user_id


# ---- Stats ------------------------------------------------------------ #

@bp.get("/stats")
def stats():
    _admin_guard()
    return success_response(data=admin_service.platform_stats(), message="Stats loaded.")


# ---- Users ------------------------------------------------------------ #

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
    try:
        user = admin_service.deactivate_user(target_user_id=user_id, acting_admin_id=acting_admin)
    except ConflictError as e:
        return error_response(str(e), error_code="CONFLICT"), 409
    from app.services.audit_service import audit_service
    audit_service.record(action="admin.user.deactivate", entity_type="user", entity_id=user.id)
    return success_response(message="User deactivated.")


@bp.post("/users/<uuid:user_id>/reactivate")
def reactivate_user(user_id: uuid.UUID):
    acting_admin = _admin_guard()
    try:
        user = admin_service.reactivate_user(target_user_id=user_id, acting_admin_id=acting_admin)
    except ConflictError as e:
        return error_response(str(e), error_code="CONFLICT"), 409
    from app.services.audit_service import audit_service
    audit_service.record(action="admin.user.reactivate", entity_type="user", entity_id=user.id)
    return success_response(message="User reactivated.")


@bp.post("/users/<uuid:user_id>/assign-role", schemas=["role"])
def assign_user_role(user_id: uuid.UUID):
    acting_admin = _admin_guard()
    body = load_schema(Schema({"role": fields.Str(validate=validate.OneOf(["Student", "Teacher", "Admin"]))}), get_json_body())
    role = body["role"]
    try:
        user = admin_service.assign_role(target_user_id=user_id, new_role=role, acting_admin_id=acting_admin)
    except Exception as e:
        return error_response(str(e), error_code="VALIDATION_ERROR"), 400
    from app.services.audit_service import audit_service
    audit_service.record(action="admin.user.role.assign", entity_type="user", entity_id=user.id, changes={"new_role": role})
    return success_response(data={"role": user.role}, message="Role assigned.")


@bp.post("/users/<uuid:user_id>/remove-role")
def remove_user_role(user_id: uuid.UUID):
    acting_admin = _admin_guard()
    try:
        user = admin_service.remove_role(target_user_id=user_id, acting_admin_id=acting_admin)
    except Exception as e:
        return error_response(str(e), error_code="VALIDATION_ERROR"), 400
    from app.services.audit_service import audit_service
    audit_service.record(action="admin.user.role.remove", entity_type="user", entity_id=user.id)
    return success_response(message="Role removed.")


# ---- Academic Structure ----------------------------------------------- #

# Departments

@bp.post("/academic/departments")
def department_create():
    acting_admin = _admin_guard()
    body = load_schema(Schema({
        "name": fields.Str(validate=validate.Length(min=3, max=120)),
        "code": fields.Str(validate=validate.Length(min=1, max=16)) | fields.Str(allow_none=True),
        "description": fields.Str(validate=validate.Length(max=1000)) | fields.Str(allow_none=True),
    }), get_json_body())
    dept = admin_service.department_create(
        name=body["name"], code=body.get("code"), description=body.get("description"), acting_admin_id=acting_admin
    )
    return success_response(data={"id": str(dept.id), "name": dept.name, "code": dept.code}, message="Department created.")


@bp.put("/academic/departments/<uuid:dept_id>")
def department_update(dept_id: uuid.UUID):
    acting_admin = _admin_guard()
    body = load_schema(Schema({
        "name": fields.Str(validate=validate.Length(min=3, max=120)) | fields.Str(allow_none=True),
        "code": fields.Str(validate=validate.Length(min=1, max=16)) | fields.Str(allow_none=True),
        "description": fields.Str(validate=validate.Length(max=1000)) | fields.Str(allow_none=True),
    }), get_json_body())
    dept = admin_service.department_update(
        dept_id=dept_id, name=body.get("name"), code=body.get("code"), description=body.get("description"), acting_admin_id=acting_admin
    )
    return success_response(data={"id": str(dept.id), "name": dept.name}, message="Department updated.")


@bp.delete("/academic/departments/<uuid:dept_id>")
def department_delete(dept_id: uuid.UUID):
    acting_admin = _admin_guard()
    try:
        admin_service.department_delete(dept_id=dept_id, acting_admin_id=acting_admin)
    except ValidationError as e:
        return error_response(str(e), error_code="VALIDATION_ERROR"), 400
    return success_response(message="Department archived.")


# Programs

@bp.post("/academic/programs")
def program_create():
    acting_admin = _admin_guard()
    body = load_schema(Schema({
        "name": fields.Str(validate=validate.Length(min=3, max=160)),
        "department_id": fields.UUID(validate=validate.UUID),
        "code": fields.Str(validate=validate.Length(min=1, max=24)) | fields.Str(allow_none=True),
        "description": fields.Str(validate=validate.Length(max=1000)) | fields.Str(allow_none=True),
    }), get_json_body())
    prog = admin_service.program_create(
        name=body["name"], department_id=body["department_id"], code=body.get("code"), description=body.get("description"), acting_admin_id=acting_admin
    )
    return success_response(data={"id": str(prog.id), "name": prog.name}, message="Program created.")


@bp.put("/academic/programs/<uuid:prog_id>")
def program_update(prog_id: uuid.UUID):
    acting_admin = _admin_guard()
    body = load_schema(Schema({
        "name": fields.Str(validate=validate.Length(min=3, max=160)) | fields.Str(allow_none=True),
        "code": fields.Str(validate=validate.Length(min=1, max=24)) | fields.Str(allow_none=True),
        "description": fields.Str(validate=validate.Length(max=1000)) | fields.Str(allow_none=True),
    }), get_json_body())
    prog = admin_service.program_update(
        prog_id=prog_id, name=body.get("name"), code=body.get("code"), description=body.get("description"), acting_admin_id=acting_admin
    )
    return success_response(data={"id": str(prog.id), "name": prog.name}, message="Program updated.")


# Sections

@bp.post("/academic/sections")
def section_create():
    acting_admin = _admin_guard()
    body = load_schema(Schema({
        "name": fields.Str(validate=validate.Length(min=3, max=24)),
        "program_id": fields.UUID(validate=validate.UUID),
        "capacity": fields.Int(validate=validate.Range(min=1)) | fields.Int(allow_none=True),
    }), get_json_body())
    sec = admin_service.section_create(
        name=body["name"], program_id=body["program_id"], capacity=body.get("capacity"), acting_admin_id=acting_admin
    )
    return success_response(data={"id": str(sec.id), "name": sec.name, "capacity": sec.capacity}, message="Section created.")


# ---- Groups ----------------------------------------------------------- #

@bp.post("/groups/<uuid:group_id>/archive")
def group_archive(group_id: uuid.UUID):
    acting_admin = _admin_guard()
    try:
        group = admin_service.group_archive(group_id=group_id, acting_admin_id=acting_admin)
    except ValidationError as e:
        return error_response(str(e), error_code="VALIDATION_ERROR"), 400
    return success_response(data={"id": str(group.id), "name": group.name}, message="Group archived.")


@bp.post("/groups/<uuid:group_id>/reassign-owner")
def group_reassign_owner(group_id: uuid.UUID):
    acting_admin = _admin_guard()
    body = load_schema(Schema({"new_owner_id": fields.UUID(validate=validate.UUID)}), get_json_body())
    new_owner_id = body["new_owner_id"]
    try:
        group = admin_service.group_reassign_owner(group_id=group_id, new_owner_id=new_owner_id, acting_admin_id=acting_admin)
    except Exception as e:
        return error_response(str(e), error_code="VALIDATION_ERROR"), 400
    return success_response(data={"id": str(group.id), "name": group.name, "owner_id": str(group.owner_id)}, message="Owner reassigned.")


# ---- Resources -------------------------------------------------------- #

@bp.put("/resources/<uuid:resource_id>/unpublish")
def resource_unpublish(resource_id: uuid.UUID):
    acting_admin = _admin_guard()
    res = admin_service.resource_unpublish(resource_id=resource_id, acting_admin_id=acting_admin)
    return success_response(data={"id": str(res.id), "title": res.title, "is_published": res.is_published}, message="Resource unpublished.")


@bp.put("/resources/<uuid:resource_id>/soft-delete")
def resource_soft_delete(resource_id: uuid.UUID):
    acting_admin = _admin_guard()
    try:
        res = admin_service.resource_soft_delete(resource_id=resource_id, acting_admin_id=acting_admin)
    except Exception as e:
        return error_response(str(e), error_code="SERVICE_ERROR"), 500
    return success_response(data={"id": str(res.id), "title": res.title, "is_active": res.is_active}, message="Resource soft-deleted.")


@bp.get("/resources/<uuid:resource_id>/scan-status")
def resource_scan_status(resource_id: uuid.UUID):
    acting_admin = _admin_guard()
    status = admin_service.resource_scan_status(resource_id=resource_id)
    return success_response(data=status, message="Scan status retrieved.")


# ---- Teacher Allowlist ------------------------------------------------ #

@bp.post("/allowlist")
def allowlist_add():
    acting_admin = _admin_guard()
    body = load_schema(Schema({"email": fields.Str(validate=validate.Email())}), get_json_body())
    entry = admin_service.allowlist_add(email=body["email"], acting_admin_id=acting_admin)
    return success_response(data={"email": entry.email, "is_approved": entry.is_approved, "added_at": entry.added_at}, message="Allowlist entry added.")


@bp.delete("/allowlist/<email>")
def allowlist_remove(email: str):
    acting_admin = _admin_guard()
    try:
        admin_service.allowlist_remove(email=email, acting_admin_id=acting_admin)
    except NotFoundError as e:
        return error_response(str(e), error_code="NOT_FOUND"), 404
    return success_response(message="Allowlist entry removed.")


@bp.post("/allowlist/<email>/approve")
def allowlist_approve(email: str):
    acting_admin = _admin_guard()
    try:
        entry = admin_service.allowlist_approve(email=email, acting_admin_id=acting_admin)
    except NotFoundError as e:
        return error_response(str(e), error_code="NOT_FOUND"), 404
    return success_response(data={"email": entry.email, "is_approved": entry.is_approved, "approved_at": entry.approved_at}, message="Allowlist entry approved.")


@bp.get("/allowlist")
def allowlist_list():
    acting_admin = _admin_guard()
    entries = admin_service.allowlist_list(acting_admin_id=acting_admin)
    return success_response(data=[{"email": e.email, "is_approved": e.is_approved, "added_at": str(e.added_at)} for e in entries], message="Allowlist listed.")


# ---- Moderation Queue ------------------------------------------------- #

@bp.get("/moderation/quarantine")
def moderation_quarantine_list():
    acting_admin = _admin_guard()
    items = admin_service.moderation_quarantine_list()
    return success_response(data=items, message="Quarantine list retrieved.")


@bp.post("/moderation/confirm-delete")
def moderation_confirm_delete():
    acting_admin = _admin_guard()
    body = load_schema(Schema({"file_id": fields.UUID(validate=validate.UUID), "justification": fields.Str(validate=validate.Length(min=1, max=500))}), get_json_body())
    try:
        result = admin_service.moderation_confirm_delete(file_id=body["file_id"], justification=body["justification"], acting_admin_id=acting_admin)
    except NotFoundError as e:
        return error_response(str(e), error_code="NOT_FOUND"), 404
    return success_response(data=result, message="Confirmed deletion processed.")


# ---- Audit Log Viewer ------------------------------------------------- #

class AuditLogFilterSchema(Schema):
    actor_id = fields.UUID(allow_none=True)
    action = fields.Str(allow_none=True, validate=validate.Length(max=64))
    entity_type = fields.Str(allow_none=True, validate=validate.Length(max=64))
    entity_id = fields.UUID(allow_none=True)
    request_id = fields.Str(allow_none=True, validate=validate.Length(max=128))
    date_from = fields.DateTime(allow_none=True)
    date_to = fields.DateTime(allow_none=True)
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Int(load_default=50, validate=validate.Range(min=1, max=500))


@bp.get("/audit-logs")
def audit_logs_list():
    acting_admin = _admin_guard()
    filters = load_schema(AuditLogFilterSchema(), request.args.to_dict())
    page, page_size = filters["page"], filters["page_size"]
    rows, total = admin_service.audit_logs_filter(
        actor_id=filters.get("actor_id"),
        action=filters.get("action"),
        entity_type=filters.get("entity_type"),
        entity_id=filters.get("entity_id"),
        request_id=filters.get("request_id"),
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        page=page,
        page_size=page_size,
    )
    # Build CSV-ready rows in memory for potential export
    meta = PagingMeta(page, page_size, total)
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)
    # Header
    writer.writerow(["id", "actor_id", "action", "entity_type", "entity_id", "request_id", "created_at", "changes"])
    for row in rows:
        writer.writerow([
            row.id,
            str(row.actor_id) if row.actor_id else "",
            row.action or "",
            row.entity_type or "",
            str(row.entity_id) if row.entity_id else "",
            row.request_id or "",
            row.created_at.isoformat() if row.created_at else "",
            row.changes or "",
        ])
    csv_string = csv_data.getvalue()

    return success_response(
        data={"items": [{"id": str(r.id), "action": r.action, "entity_type": r.entity_type, "entity_id": str(r.entity_id) if r.entity_id else None, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]},
        paging=meta.as_dict(),
        message="Audit logs listed.",
        # Include CSV as a downloadable field; the export itself is audited separately
        csv_export=csv_string[:10000] if csv_string else "",  # truncate preview, full export via dedicated endpoint if needed
    )


# ---- System Settings (read-only env overview) ----------------------- #

@bp.get("/settings")
def settings_overview():
    """Read-only overview of configured system settings (no writes)."""
    from app.config import DevelopmentConfig
    cfg = DevelopmentConfig()
    return success_response(data={
        "upload_max_size_bytes": cfg.UPLOAD_MAX_SIZE_BYTES,
        "upload_allowed_extensions": list(cfg.UPLOAD_ALLOWED_EXTENSIONS),
        "rate_limit_default": cfg.RATELIMIT_DEFAULT,
        "rate_limit_auth": cfg.RATELIMIT_AUTH,
        "jwt_access_minutes": cfg.JWT_ACCESS_TOKEN_MINUTES,
        "env": cfg.ENV,
    }, message="System settings overview.")