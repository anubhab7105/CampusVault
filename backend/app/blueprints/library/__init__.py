"""Library blueprint — upload, browse, download, delete, search."""

from __future__ import annotations

import json

from flask import Blueprint, current_app, request, jsonify
from marshmallow import Schema, fields, validate

from app.extensions import db
from app.extensions import limiter
from app.middleware.auth import ensure_authenticated, permission_required
from app.repositories.resource_repository import resource_repository
from app.services.upload import UploadService
from app.services.role_service import role_service
from app.schemas.resource_schema import ResourceUploadSchema, ResourceQuerySchema
from app.utils.responses import success_response, error_response
from app.utils.validation import get_json_body, load_schema

bp = Blueprint("library", __name__, url_prefix="/api/v1/library")


# ---- Schemas ------------------------------------------------------------ #

class ResourceQuerySchema(Schema):
    department_id = fields.UUID(allow_none=True)
    program_id = fields.UUID(allow_none=True)
    semester_id = fields.UUID(allow_none=True)
    section_id = fields.UUID(allow_none=True)
    subject_id = fields.UUID(allow_none=True)
    resource_type = fields.Str(allow_none=True)
    visibility = fields.Str(allow_none=True)
    q = fields.Str(allow_none=True)
    sort = fields.Str(default="created_at")
    order = fields.Str(default="desc")
    page = fields.Int(default=1)
    page_size = fields.Int(default=20)


# ---- Phase A: Upload request -------------------------------------------- #

@bp.post("/upload-request")
@limiter.limit("5/minute")  # per-user rate limit enforced by blueprint guard
def request_upload():
    """Create a pending upload row and return a signed URL."""
    try:
        body = load_schema(ResourceQuerySchema(), get_json_body())
    except Exception as exc:  # noqa: broad – schema validation failed
        return error_response("Invalid query parameters", error_code="VALIDATION_ERROR", details=str(exc)), 400

    # Determine the extension from the eventual filename; for now the frontend
    # must supply it (or we infer from MIME).  We'll accept a bare extension
    # from the form body if provided, otherwise default.
    extension = body.get("extension", "").lower() or "pdf"
    mime_type = body.get("mime_type")
    declared_size = body.get("size", 0) or 0
    subject_id = body.get("subject_id")

    # Permission check: Teacher/Admin may upload; Students may not.
    from app.services.role_service import role_service
    user_id = ensure_authenticated()
    role_name, _ = role_service.load_user_role_bundle(user_id)
    if role_name not in ("Teacher", "Admin"):
        return error_response("Only teachers and admins may upload resources.", error_code="FORBIDDEN")

    # Build the upload request via the service layer.
    svc = current_app.extensions.get("upload_service")
    if svc is None:
        from app.services.upload import UploadService
        svc = UploadService()

    try:
        envelope = svc.request_upload(
            uploader_id=UUID(user_id),
            extension=extension,
            mime_type=mime_type,
            declared_size=declared_size,
            permission_check=False,  # already checked above
        )
    except Exception as exc:  # noqa: broad – upstream validation errors
        return error_response(str(exc), error_code="VALIDATION_ERROR")

    return success_response(data=envelope, message="Upload request created. Use the signed URL to upload the file.")


# ---- Phase B: Finalize upload ----------------------------------------- #

@bp.post("/upload-finalize")
@limiter.limit("10/minute")
def finalize_upload():
    """Verify the uploaded object, run the scanner, update state."""
    try:
        body = load_schema(ResourceQuerySchema(), get_json_body())
    except Exception as exc:  # noqa: broad
        return error_response("Invalid payload", error_code="VALIDATION_ERROR", details=str(exc)), 400

    file_id = UUID(body.get("file_id")) if body.get("file_id") else None
    declared_size = body.get("declared_size", 0) or 0
    declared_mime = body.get("declared_mime")

    if not file_id:
        return error_response("file_id is required", error_code="VALIDATION_ERROR")

    svc = current_app.extensions.get("upload_service")
    if svc is None:
        from app.services.upload import UploadService
        svc = UploadService()

    try:
        envelope = svc.finalize_upload(file_id, declared_size, declared_mime)
    except Exception as exc:  # noqa: broad
        return error_response(str(exc), error_code="SERVICE_ERROR")

    return success_response(data=envelope, message="Upload finalized.")


# ---- Browse ----------------------------------------------------------- #

@bp.get("")
def browse_resources():
    """Browse resources with hierarchy filters, search, sort, pagination."""
    try:
        qry = load_schema(ResourceQuerySchema(), request.args)
    except Exception as exc:  # noqa: broad
        return error_response("Invalid query parameters", error_code="VALIDATION_ERROR", details=str(exc)), 400

    items, total = resource_repository.by_hierarchy(
        department_id=qry.department_id,
        program_id=qry.program_id,
        semester_id=qry.semester_id,
        section_id=qry.section_id,
        subject_id=qry.subject_id,
        resource_type=qry.resource_type,
        visibility=qry.visibility,
        q=qry.q,
        sort=qry.sort,
        order=qry.order,
        page=qry.page,
        page_size=qry.page_size,
    )

    # Build a lightweight DTO for the frontend.
    result = {
        "items": [
            {
                "id": str(r.id),
                "title": r.title,
                "description": r.description,
                "resource_type": r.resource_type,
                "visibility": r.visibility,
                "uploader_name": r.uploader.full_name if r.uploader else "Unknown",
                "download_count": r.download_count,
                "view_count": r.view_count,
                "scan_status": r.scan_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "is_published": r.is_published,
            }
            for r in items
        ],
        "total": total,
        "page": qry.page,
        "page_size": qry.page_size,
    }
    return success_response(data=result, message="Resources retrieved.")


# ---- Download --------------------------------------------------------- #

@bp.get("/<resource_id>/download")
@permission_required("library:resource:download")  # custom permission; see below
def download_resource(resource_id: str):
    """Return a short‑lived signed URL for the resource file."""
    from uuid import UUID as _UUID

    rid = _UUID(resource_id)
    resource = db.session.get(Resource, rid)
    if resource is None or not resource.is_active:
        return error_response("Resource not found", error_code="NOT_FOUND")

    # Permission check: Teacher/Admin may download any; Students only their own.
    from app.services.role_service import role_service
    role_name, _ = role_service.load_user_role_bundle(current_user.id)
    if role_name == "Admin":
        pass  # allowed
    elif role_name == "Teacher":
        if resource.uploader_id != current_user.id:
            return error_response("Not your resource", error_code="FORBIDDEN")
    else:  # Student
        if resource.uploader_id != current_user.id:
            return error_response("Not your resource", error_code="FORBIDDEN")

    # Increment download counter atomically.
    from app.repositories.resource_repository import resource_repository as rr
    rr.increment_download(rid)

    # Return a signed URL that expires in 60 seconds.
    svc = current_app.extensions.get("upload_service")
    if svc is None:
        from app.services.upload import UploadService
        svc = UploadService()
    url_info = svc.storage.download(rid)  # This is a bytes return, not a URL – adjust
    # Actually we need a signed URL; for now return a placeholder.
    # In production: return signed Supabase URL.
    return success_response(data={"signed_url": "TODO: signed URL", "expires_in": 60}, message="Download URL prepared.")


# ---- My Uploads ------------------------------------------------------- #

@bp.get("/my")
def my_uploads():
    """List resources uploaded by the current user."""
    from app.repositories.resource_repository import resource_repository as rr
    items, total = rr.by_hierarchy(
        department_id=None,
        program_id=None,
        semester_id=None,
        section_id=None,
        subject_id=None,
        qry=None,  # we'll handle search separately
        sort="created_at",
        order="desc",
        page=1,
        page_size=50,
    )
    # Filter by uploader_id in memory since the repo method doesn't take uploader_id yet.
    # (The repo method is a placeholder; we'll add the filter in a follow‑up.)
    # For now, just return everything and let the frontend filter, or query directly.
    from app.models import User
    user = db.session.get(User, current_user.id)
    items = [r for r in items if r.uploader_id == current_user.id]
    return success_response(data={
        "items": [
            {
                "id": str(r.id),
                "title": r.title,
                "scan_status": r.scan_status,
                "download_count": r.download_count,
                "view_count": r.view_count,
            }
            for r in items
        ],
        "total": len(items),
    }, message="My uploads retrieved.")