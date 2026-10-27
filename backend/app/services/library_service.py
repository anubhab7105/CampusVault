"""Library service — resource catalog rules (visibility, publication)."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from app.errors.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.extensions import db
from app.models import Resource
from app.repositories import ResourceRepository
from app.services.audit_service import audit_service
from app.services.base_service import BaseService


class LibraryService(BaseService):
    def __init__(self) -> None:
        self.resources = ResourceRepository()

    def create_resource(
        self,
        *,
        uploaded_by: uuid.UUID,
        subject_id: uuid.UUID,
        title: str,
        description: str = "",
        resource_type: str,
        visibility: str = "college",
        file_id: uuid.UUID | None = None,
        external_url: str | None = None,
    ) -> Resource:
        """Teachers/Admins create; ownership metadata is server-derived."""
        if file_id is None and not external_url:
            raise ValidationError("A file or an external URL is required.")
        resource = self.resources.create(
            subject_id=subject_id,
            file_id=file_id,
            uploaded_by=uploaded_by,
            title=title,
            description=description,
            resource_type=resource_type,
            visibility=visibility,
            external_url=external_url,
        )
        audit_service.record(
            action="library.resource.create",
            entity_type="resource",
            entity_id=resource.id,
        )
        db.session.commit()
        return resource

    def get_visible_resource(self, resource_id: uuid.UUID) -> Resource:
        resource = self.resources.get_active_by_id(resource_id)
        if resource is None or not resource.is_published:
            raise NotFoundError("Resource not found.")
        return resource

    def browse(self, *, filters: dict, page: int, page_size: int):
        conditions = self._filter_conditions(filters)
        q = filters.pop("q", None)
        order_map = {
            "created_at": Resource.created_at,
            "title": Resource.title,
            "download_count": Resource.download_count,
        }
        sort_column = order_map.get(filters.get("sort", "created_at"), Resource.created_at)
        rows, total = self.resources.browse(
            conditions=conditions,
            q=q,
            sort_column=sort_column,
            order=filters.get("order", "desc"),
            page=page,
            page_size=page_size,
        )
        return rows, total

    @staticmethod
    def _filter_conditions(filters: dict) -> list[sa.ColumnElement]:
        conditions: list[sa.ColumnElement] = [Resource.is_published.is_(True)]
        if filters.get("subject_id"):
            conditions.append(Resource.subject_id == filters["subject_id"])
        if filters.get("resource_type"):
            conditions.append(Resource.resource_type == filters["resource_type"])
        if filters.get("visibility"):
            conditions.append(Resource.visibility == filters["visibility"])
        return conditions

    def assert_can_manage(self, resource: Resource, user_id: uuid.UUID, is_admin: bool) -> None:
        if resource.uploaded_by != user_id and not is_admin:
            raise ForbiddenError("Only the uploader or an admin can manage this resource.")

    def increment_download(self, resource_id: uuid.UUID) -> None:
        self.resources.increment_download(resource_id)
        db.session.commit()

    def increment_view(self, resource_id: uuid.UUID) -> None:
        self.resources.increment_view(resource_id)
        db.session.commit()


library_service = LibraryService()
