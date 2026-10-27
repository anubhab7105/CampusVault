"""Library blueprint — browse, create, download accounting."""

from __future__ import annotations

import uuid

from flask import Blueprint, request

from app.middleware.auth import ensure_authenticated
from app.middleware.rbac import permission_required
from app.schemas.resource_schema import (
    CreateResourceSchema,
    ListResourcesQuerySchema,
)
from app.services.audit_service import audit_service
from app.services.library_service import library_service
from app.utils.pagination import PagingMeta
from app.utils.responses import success_response
from app.utils.validation import get_json_body, load_schema

bp = Blueprint("library", __name__, url_prefix="/api/v1/library")


@bp.get("/resources")
def browse():
    ensure_authenticated()
    filters = load_schema(ListResourcesQuerySchema(), request.args.to_dict())
    page = filters.pop("page", 1)
    page_size = filters.pop("page_size", 20)
    rows, total = library_service.browse(filters=filters, page=page, page_size=page_size)
    meta = PagingMeta(page, page_size, total)
    return success_response(
        data={
            "items": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "resource_type": r.resource_type,
                    "visibility": r.visibility,
                    "subject_id": str(r.subject_id),
                    "file_id": str(r.file_id) if r.file_id else None,
                    "download_count": r.download_count,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        },
        paging=meta.as_dict(),
        message="Resources listed.",
    )


@bp.post("/resources")
@permission_required("library:resource:create")
def create():
    user_id = uuid.UUID(ensure_authenticated())
    body = load_schema(CreateResourceSchema(), get_json_body())
    resource = library_service.create_resource(
        uploaded_by=user_id,
        subject_id=body["subject_id"],
        file_id=body["file_id"],
        title=body["title"],
        description=body["description"],
        resource_type=body["resource_type"],
        visibility=body["visibility"],
        external_url=body["external_url"],
    )
    return success_response(data={"id": str(resource.id)}, status_code=201, message="Resource created.")


@bp.get("/resources/<uuid:resource_id>")
def get_resource(resource_id: uuid.UUID):
    ensure_authenticated()
    resource = library_service.get_visible_resource(resource_id)
    library_service.increment_view(resource_id)
    return success_response(
        data={
            "id": str(resource.id),
            "title": resource.title,
            "description": resource.description,
            "resource_type": resource.resource_type,
            "visibility": resource.visibility,
            "subject_id": str(resource.subject_id),
            "file_id": str(resource.file_id) if resource.file_id else None,
            "external_url": resource.external_url,
        },
        message="Resource loaded.",
    )


@bp.post("/resources/<uuid:resource_id>/download")
def download(resource_id: uuid.UUID):
    """Increment counter + audit, return the download reference."""
    ensure_authenticated()
    user_id = uuid.UUID(ensure_authenticated())
    resource = library_service.get_visible_resource(resource_id)
    library_service.increment_download(resource_id)
    audit_service.record(
        action="library.resource.download",
        entity_type="resource",
        entity_id=resource.id,
        actor_id=user_id,
    )
    from app.extensions import db

    db.session.commit()
    return success_response(
        data={
            "file_id": str(resource.file_id) if resource.file_id else None,
            "external_url": resource.external_url,
        },
        message="Download ready.",
    )


@bp.delete("/resources/<uuid:resource_id>")
@permission_required("library:resource:create")
def delete(resource_id: uuid.UUID):
    """Soft delete (uploader or admin only)."""
    user_id = uuid.UUID(ensure_authenticated())
    from flask_jwt_extended import get_jwt

    is_admin = get_jwt().get("role") == "Admin"
    resource = library_service.get_visible_resource(resource_id)
    library_service.assert_can_manage(resource, user_id, is_admin)
    from app.extensions import db

    library_service.resources.soft_delete(resource)
    audit_service.record(
        action="library.resource.delete",
        entity_type="resource",
        entity_id=resource.id,
    )
    db.session.commit()
    return success_response(message="Resource deleted.")
