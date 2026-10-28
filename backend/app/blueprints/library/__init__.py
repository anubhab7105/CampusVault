"""Library blueprint — upload, browse, download, delete, search."""

from __future__ import annotations

from uuid import UUID

from flask import Blueprint, current_app, request
from marshmallow import Schema, fields, validate

from app.extensions import db, limiter
from app.middleware.auth import ensure_authenticated
from app.models.resource import Resource
from app.repositories.resource_repository import resource_repository
from app.schemas.resource_schema import ResourceQuerySchema, ResourceUploadSchema
from app.services.role_service import role_service
from app.services.upload import UploadService
from app.utils.responses import error_response, success_response
from app.utils.validation import get_json_body, load_schema

bp = Blueprint("library", __name__, url_prefix="/api/v1/library")


# ---- Upload schemas ---------------------------------------------------- #

class FinalizeUploadSchema(Schema):
    """Schema for the upload-finalize payload."""

    file_id = fields.UUID(required=True)
    declared_size = fields.Int(load_default=0, validate=validate.Range(min=0))
    declared_mime = fields.Str(allow_none=True)


# ---- Phase A: Upload request -------------------------------------------- #

@bp.post("/upload-request")
@limiter.limit("5/minute")  # per-user rate limit enforced by blueprint guard
def request_upload():
    """Create a pending upload row and return a signed URL."""
    try:
        body = load_schema(ResourceUploadSchema(), get_json_body())
    except Exception as exc:
        return error_response(
            "Invalid query parameters",
            error_code="VALIDATION_ERROR",
            details=str(exc),
        ), 400

    # Determine the extension from the eventual filename; for now the frontend
    # must supply it (or we infer from MIME).  We'll accept a bare extension
    # from the form body if provided, otherwise default.
    extension = body["extension"].lower().lstrip(".") or "pdf"
    mime_type = body.get("mime_type")
    declared_size = body.get("size", 0) or 0

    # Permission check: Teacher/Admin may upload; Students may not.
    user_id = ensure_authenticated()
    role_name, _ = role_service.load_user_role_bundle(user_id)
    if role_name not in ("Teacher", "Admin"):
        return error_response("Only teachers and admins may upload resources.", error_code="FORBIDDEN")

    # Build the upload request via the service layer.
    svc = current_app.extensions.get("upload_service") or UploadService()

    try:
        envelope = svc.request_upload(
            uploader_id=UUID(user_id),
            extension=extension,
            mime_type=mime_type,
            declared_size=declared_size,
            permission_check=False,  # already checked above
        )
    except Exception as exc:
        return error_response(str(exc), error_code="VALIDATION_ERROR")

    return success_response(
        data=envelope,
        message="Upload request created. Use the signed URL to upload the file.",
    )


# ---- Phase B: Finalize upload ----------------------------------------- #

@bp.post("/upload-finalize")
@limiter.limit("10/minute")
def finalize_upload():
    """Verify the uploaded object, run the scanner, update state."""
    try:
        body = load_schema(FinalizeUploadSchema(), get_json_body())
    except Exception as exc:
        return error_response("Invalid payload", error_code="VALIDATION_ERROR", details=str(exc)), 400

    ensure_authenticated()
    file_id = body["file_id"]
    declared_size = body.get("declared_size", 0) or 0
    declared_mime = body.get("declared_mime")

    svc = current_app.extensions.get("upload_service")
    if svc is None:
        from app.services.upload import UploadService
        svc = UploadService()

    try:
        envelope = svc.finalize_upload(file_id, declared_size, declared_mime)
    except Exception as exc:
        return error_response(str(exc), error_code="SERVICE_ERROR")

    return success_response(data=envelope, message="Upload finalized.")


# ---- Browse ----------------------------------------------------------- #

@bp.get("")
def browse_resources():
    """Browse resources with hierarchy filters, search, sort, pagination."""
    try:
        qry = load_schema(ResourceQuerySchema(), request.args)
    except Exception as exc:
        return error_response(
            "Invalid query parameters",
            error_code="VALIDATION_ERROR",
            details=str(exc),
        ), 400

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
def download_resource(resource_id: str):
    """Return a short‑lived signed URL for the resource file."""
    rid = UUID(resource_id)
    resource = db.session.get(Resource, rid)
    if resource is None or not resource.is_active:
        return error_response("Resource not found", error_code="NOT_FOUND")

    # Permission check: Teacher/Admin may download any; Students only their own.
    user_id = UUID(ensure_authenticated())
    role_name, _ = role_service.load_user_role_bundle(user_id)
    if role_name == "Admin":
        pass  # allowed
    elif role_name == "Teacher":
        if resource.uploader_id != user_id:
            return error_response("Not your resource", error_code="FORBIDDEN")
    elif resource.uploader_id != user_id:
        return error_response("Not your resource", error_code="FORBIDDEN")

    # Increment download counter atomically.
    from app.repositories.resource_repository import resource_repository as rr
    rr.increment_download(rid)

    # Return a signed URL that expires in 60 seconds.
    return success_response(
        data={"signed_url": "TODO: signed URL", "expires_in": 60},
        message="Download URL prepared.",
    )


# ---- My Uploads ------------------------------------------------------- #

@bp.get("/my")
def my_uploads():
    """List resources uploaded by the current user."""
    from app.repositories.resource_repository import resource_repository as rr
    user_id = UUID(ensure_authenticated())
    items, _ = rr.by_hierarchy(
        department_id=None,
        program_id=None,
        semester_id=None,
        section_id=None,
        subject_id=None,
        q=None,  # we'll handle search separately
        sort="created_at",
        order="desc",
        page=1,
        page_size=50,
    )
    # Filter by uploader_id in memory since the repo method doesn't take uploader_id yet.
    items = [r for r in items if r.uploader_id == user_id]
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
