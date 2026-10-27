"""Resource repository — CRUD + hierarchy filtering + full-text search."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from app.extensions import db
from app.models import Resource
from app.repositories.base_repository import BaseRepository


class ResourceRepository(BaseRepository[Resource]):
    model = Resource

    # ----------------------------------------------------------------- #
    # Hierarchy lookups
    # ----------------------------------------------------------------- #

    def by_hierarchy(
        self,
        *,
        department_id: UUID | None = None,
        program_id: UUID | None = None,
        semester_id: UUID | None = None,
        section_id: UUID | None = None,
        subject_id: UUID | None = None,
        resource_type: str | None = None,
        visibility: str | None = None,
        q: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Resource], int]:
        """Browse resources filtered by the academic hierarchy and search.

        Returns ``(items, total)``.
        """

        conditions = []
        if department_id is not None:
            conditions.append(Resource.department_id == department_id)
        if program_id is not None:
            conditions.append(Resource.program_id == program_id)
        if semester_id is not None:
            conditions.append(Resource.semester_id == semester_id)
        if section_id is not None:
            conditions.append(Resource.section_id == section_id)
        if subject_id is not None:
            conditions.append(Resource.subject_id == subject_id)
        if resource_type is not None:
            conditions.append(Resource.resource_type == resource_type)
        if visibility is not None:
            conditions.append(Resource.visibility == visibility)
        if q:
            # Full‑text search via tsvector (PostgreSQL) – fallback to LIKE on SQLite.
            from sqlalchemy import or_

            try:
                # PostgreSQL: try the GIN index path.
                conditions.append(
                    Resource.fts.match(q, postgresql_regconfig="english")
                )
            except Exception:
                conditions.append(
                    or_(
                        Resource.title.ilike(f"%{q}%"),
                        Resource.description.ilike(f"%{q}%"),
                    )
                )

        # --- Pagination & sorting ------------------------------------------------
        stmt = sa.select(Resource).where(conditions).where(Resource.is_active == True)  # type: ignore[arg-type]  # noqa: E712
        stmt = stmt.order_by(
            sa.asc(getattr(Resource, sort)) if order == "asc" else sa.desc(getattr(Resource, sort))
        )
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Resource.created_at.desc())  # stable final order

        items = db.session.scalars(stmt).unique().all()

        # Total count (without offset/limit), using the same WHERE clause.
        count_stmt = sa.select(sa.func.count()).select_from(Resource).where(conditions).where(Resource.is_active == True)  # type: ignore[arg-type]  # noqa: E712
        total = db.session.scalar(count_stmt) or 0

        return items, total

    # ----------------------------------------------------------------- #
    # Create / Update
    # ----------------------------------------------------------------- #

    def create(self, *, uploader_id: UUID, title: str, description: str | None,
               resource_type: str, visibility: str, file_id: UUID | None,
               external_url: str | None, subject_id: UUID) -> Resource:
        """Create a new resource tied to the academic hierarchy.

        Exactly one of ``file_id`` or ``external_url`` must be non‑NULL;
        the caller is responsible for enforcing that rule.
        """
        # Validate that exactly one of file_id / external_url is set.
        if (file_id is None) == (external_url is None):
            raise ValueError("Exactly one of file_id or external_url must be set.")

        # Validate external URL scheme (https only, no private IPs).
        if external_url:
            from urllib.parse import urlparse

            parsed = urlparse(external_url)
            if parsed.scheme != "https":
                raise ValueError("External URL must use HTTPS.")
            # Block private‑IP targets.
            host = parsed.hostname or ""
            private_prefixes = ("127.", "192.168.", "10.", "172.16.", "172.31.", "::1", "fe80:")
            if any(host.startswith(p) for p in private_prefixes):
                raise ValueError("External URL must not point to a private IP address.")

        resource = Resource(
            uploader_id=uploader_id,
            title=title,
            description=description,
            resource_type=resource_type,
            visibility=visibility,
            file_id=file_id,
            external_url=external_url,
            subject_id=subject_id,
            is_active=True,
        )
        db.session.add(resource)
        db.session.flush()
        return resource

    def update(self, resource: Resource, **kwargs) -> Resource:
        """Update resource fields (admin/teacher edit)."""
        for key, value in kwargs.items():
            if hasattr(resource, key) and value is not None:
                setattr(resource, key, value)
        db.session.flush()
        return resource

    # ----------------------------------------------------------------- #
    # Soft delete
    # ----------------------------------------------------------------- #

    def soft_delete(self, resource_id: UUID) -> None:
        """Soft‑delete a resource; enqueue a deferred Celery task to remove the
        underlying storage object after a grace period."""
        resource = db.session.get(Resource, resource_id)
        if resource is None:
            return
        resource.is_active = False
        db.session.flush()
        # TODO: enqueue Celery task to remove Supabase object after 24h grace period.
        # e.g. delete_resource_delay.delay(resource.id, grace_period_minutes=24)

    # ----------------------------------------------------------------- #
    # Download / view counters
    # ----------------------------------------------------------------- #

    def increment_download(self, resource_id: UUID) -> None:
        """Atomically increment the download counter."""
        db.session.execute(
            sa.text("UPDATE resources SET download_count = download_count + 1 WHERE id = :rid"),
            {"rid": str(resource_id)},
        )

    def increment_view(self, resource_id: UUID) -> None:
        """Atomically increment the view counter."""
        db.session.execute(
            sa.text("UPDATE resources SET view_count = view_count + 1 WHERE id = :rid"),
            {"rid": str(resource_id)},
        )

    # ----------------------------------------------------------------- #
    # Owner / permission checks (used by blueprints)
    # ----------------------------------------------------------------- #

    def can_edit(self, resource_id: UUID, user_id: UUID) -> bool:
        """Teacher may edit only their own resources; Admin may edit any."""
        resource = db.session.get(Resource, resource_id)
        if resource is None or not resource.is_active:
            return False
        from app.models import User as _User

        user = db.session.get(_User, user_id)
        if user is None:
            return False
        # Admin override
        from app.services.role_service import role_service
        role_name, _ = role_service.load_user_role_bundle(user_id)
        if role_name == "Admin":
            return True
        # Teacher: only own resources
        return resource.uploader_id == user_id

    def can_delete(self, resource_id: UUID, user_id: UUID) -> bool:
        """Teacher may delete only their own resources; Admin may delete any."""
        return self.can_edit(resource_id, user_id)  # same logic for now


resource_repository = ResourceRepository()
