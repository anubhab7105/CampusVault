"""
Library blueprint. Per API_SPEC_LIBRARY.md: two-step upload (raw file, then
resource metadata), download gated on scan_status=clean.
"""
import uuid

from flask import Blueprint, g, request

from app.middleware.auth_middleware import require_auth
from app.schemas.library import ResourceCreateRequest, ResourceUpdateRequest
from app.services.library_service import LibraryService
from app.utils.responses import success

library_bp = Blueprint("library", __name__, url_prefix="/api/v1")


def _get_service() -> LibraryService:
    from flask import current_app
    return LibraryService(
        db=current_app.extensions["db_session"](),
        storage=current_app.extensions["storage_provider"],
        socketio=current_app.extensions.get("socketio"),
    )


def _serialize_file(f) -> dict:
    return {
        "id": str(f.id),
        "original_filename": f.original_filename,
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "scan_status": f.scan_status.value,
    }


def _serialize_resource(r) -> dict:
    return {
        "id": str(r.id),
        "title": r.title,
        "description": r.description,
        "file_id": str(r.file_id),
        "department_id": str(r.department_id) if r.department_id else None,
        "program_id": str(r.program_id) if r.program_id else None,
        "subject_id": str(r.subject_id) if r.subject_id else None,
        "uploaded_by": str(r.uploaded_by),
        "created_at": r.created_at.isoformat(),
    }


# ---------- Files ----------

@library_bp.post("/files")
@require_auth
def upload_file():
    if "file" not in request.files:
        from app.utils.exceptions import ValidationError
        raise ValidationError("No file provided.", code="VALIDATION_ERROR")

    uploaded = request.files["file"]
    content = uploaded.read()

    service = _get_service()
    file = service.upload_file(
        uploader_id=g.user_id,
        original_filename=uploaded.filename or "unnamed",
        content=content,
        mime_type=uploaded.mimetype or "application/octet-stream",
    )
    return success(_serialize_file(file), message="File uploaded, scan in progress.", status=201)


@library_bp.get("/files/<uuid:file_id>")
@require_auth
def get_file(file_id: uuid.UUID):
    service = _get_service()
    file = service.get_file(file_id)
    return success(_serialize_file(file))


@library_bp.get("/files/<uuid:file_id>/download")
@require_auth
def download_file(file_id: uuid.UUID):
    service = _get_service()
    result = service.get_download_url(file_id)
    return success(result)


# ---------- Resources ----------

@library_bp.get("/library/resources")
@require_auth
def list_resources():
    department_id = request.args.get("department_id")
    program_id = request.args.get("program_id")
    subject_id = request.args.get("subject_id")
    query = request.args.get("q")
    mine = request.args.get("mine", "false").lower() == "true"

    service = _get_service()
    resources = service.list_resources(
        department_id=uuid.UUID(department_id) if department_id else None,
        program_id=uuid.UUID(program_id) if program_id else None,
        subject_id=uuid.UUID(subject_id) if subject_id else None,
        query=query,
        mine_user_id=g.user_id if mine else None,
    )
    return success({"items": [_serialize_resource(r) for r in resources]})


@library_bp.post("/library/resources")
@require_auth
def create_resource():
    payload = ResourceCreateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    resource = service.create_resource(
        file_id=payload.file_id, title=payload.title, description=payload.description,
        uploaded_by=g.user_id, department_id=payload.department_id,
        program_id=payload.program_id, subject_id=payload.subject_id,
    )
    return success(_serialize_resource(resource), status=201)


@library_bp.patch("/library/resources/<uuid:resource_id>")
@require_auth
def update_resource(resource_id: uuid.UUID):
    payload = ResourceUpdateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    resource = service.update_resource(
        resource_id, actor_id=g.user_id, title=payload.title, description=payload.description,
        department_id=payload.department_id, program_id=payload.program_id, subject_id=payload.subject_id,
    )
    return success(_serialize_resource(resource))


@library_bp.delete("/library/resources/<uuid:resource_id>")
@require_auth
def delete_resource(resource_id: uuid.UUID):
    service = _get_service()
    service.delete_resource(resource_id, actor_id=g.user_id)
    return success({}, message="Resource deleted.")
