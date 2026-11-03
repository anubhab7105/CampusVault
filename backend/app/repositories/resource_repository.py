"""Resource repository — CRUD + hierarchy filtering + full-text search."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from uuid import UUID

import sqlalchemy as sa

from app.extensions import db
from app.models import Department, Program, Resource, Section, Semester, Subject
from app.repositories.base_repository import BaseRepository


class _NotProvided(Enum):
    """Sentinel to distinguish \"not provided\" from \"explicitly None\" for
    nullable hierarchy fields."""

    value = object()


_NOT_PROVIDED = _NotProvided.value


class ResourceRepository(BaseRepository[Resource]):
    model = Resource

    # ----------------------------------------------------------------- #
    # Hierarchy resolution helpers
    # ----------------------------------------------------------------- #

    def _resolve_hierarchy(self, subject_id: UUID) -> tuple[UUID, UUID, UUID]:
        """Given a subject_id, return (department_id, program_id, semester_id).

        Walks subject -> semester -> program -> department. Does NOT filter on
        deleted_at so soft-deleted ancestors still resolve.
        """
        subject = db.session.get(Subject, subject_id)
        if subject is None:
            raise ValueError("Subject not found.")
        semester = db.session.get(Semester, subject.semester_id)
        if semester is None:
            raise ValueError("Semester not found for subject.")
        program = db.session.get(Program, semester.program_id)
        if program is None:
            raise ValueError("Program not found for semester.")
        department = db.session.get(Department, program.department_id)
        if department is None:
            raise ValueError("Department not found for program.")
        return department.id, program.id, semester.id

    def _validate_section(
        self, section_id: UUID | None, semester_id: UUID
    ) -> UUID | None:
        """Validate that section_id belongs to semester_id. Returns section_id.

        Raises ValueError if the section does not exist or belongs to a
        different semester. Returns None if section_id is None.
        """
        if section_id is None:
            return None
        section = db.session.get(Section, section_id)
        if section is None:
            raise ValueError("Section not found.")
        if section.semester_id != semester_id:
            raise ValueError("section_id does not belong to the subject's semester.")
        return section_id

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
        stmt = (
            sa.select(Resource)
            .where(*conditions)
            .where(Resource.deleted_at.is_(None))
        )
        stmt = stmt.order_by(
            sa.asc(getattr(Resource, sort)) if order == "asc" else sa.desc(getattr(Resource, sort))
        )
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Resource.created_at.desc())  # stable final order

        items = db.session.scalars(stmt).unique().all()

        # Total count (without offset/limit), using the same WHERE clause.
        count_stmt = (
            sa.select(sa.func.count())
            .select_from(Resource)
            .where(*conditions)
            .where(Resource.deleted_at.is_(None))
        )
        total = db.session.scalar(count_stmt) or 0

        return items, total

    # ----------------------------------------------------------------- #
    # Create / Update
    # ----------------------------------------------------------------- #

    def create(self, *, uploader_id: UUID, title: str, description: str | None,
               resource_type: str, visibility: str, file_id: UUID | None,
               external_url: str | None, subject_id: UUID,
               department_id: UUID | None | _NotProvided = _NOT_PROVIDED,
               program_id: UUID | None | _NotProvided = _NOT_PROVIDED,
               semester_id: UUID | None | _NotProvided = _NOT_PROVIDED,
               section_id: UUID | None | _NotProvided = _NOT_PROVIDED) -> Resource:
        """Create a new resource tied to the academic hierarchy.

        Exactly one of ``file_id`` or ``external_url`` must be non‑NULL;
        the caller is responsible for enforcing that rule.

        department_id / program_id / semester_id are derived from subject_id
        (subject -> semester -> program -> department). If the caller supplies
        any of these, they must match the derived values or a ValueError is
        raised. section_id is stored independently but must belong to the
        subject's semester.
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

        # --- Resolve hierarchy from subject_id (authoritative) ----------- #
        derived_department_id, derived_program_id, derived_semester_id = (
            self._resolve_hierarchy(subject_id)
        )

        # Validate caller-supplied hierarchy IDs against derived values.
        if department_id is not _NOT_PROVIDED and department_id is not None \
                and department_id != derived_department_id:
            raise ValueError("department_id does not match subject's department.")
        if program_id is not _NOT_PROVIDED and program_id is not None \
                and program_id != derived_program_id:
            raise ValueError("program_id does not match subject's program.")
        if semester_id is not _NOT_PROVIDED and semester_id is not None \
                and semester_id != derived_semester_id:
            raise ValueError("semester_id does not match subject's semester.")

        # Validate section belongs to the subject's semester.
        resolved_section_id = self._validate_section(
            section_id if section_id is not _NOT_PROVIDED else None,
            derived_semester_id,
        )

        resource = Resource(
            uploaded_by=uploader_id,
            title=title,
            description=description,
            resource_type=resource_type,
            visibility=visibility,
            file_id=file_id,
            external_url=external_url,
            subject_id=subject_id,
            department_id=derived_department_id,
            program_id=derived_program_id,
            semester_id=derived_semester_id,
            section_id=resolved_section_id,
        )
        db.session.add(resource)
        db.session.flush()
        return resource

    def update(self, resource: Resource, **kwargs) -> Resource:
        """Update resource fields (admin/teacher edit).

        Hierarchy fields are handled specially:
        - If subject_id changes, department_id/program_id/semester_id are
          re-derived from the new subject and section_id is re-validated
          (cleared if it no longer matches the new semester).
        - department_id/program_id/semester_id supplied directly must match
          the values derived from subject_id, otherwise ValueError is raised.
        - section_id supplied directly must belong to the subject's semester.
        """
        new_subject_id = kwargs.pop("subject_id", _NOT_PROVIDED)
        new_section_id = kwargs.pop("section_id", _NOT_PROVIDED)
        new_department_id = kwargs.pop("department_id", _NOT_PROVIDED)
        new_program_id = kwargs.pop("program_id", _NOT_PROVIDED)
        new_semester_id = kwargs.pop("semester_id", _NOT_PROVIDED)

        # Determine effective subject_id. Treat None as "not provided" so the
        # existing subject is preserved and _resolve_hierarchy is not called
        # with None.
        effective_subject_id = (
            new_subject_id
            if new_subject_id is not _NOT_PROVIDED and new_subject_id is not None
            else resource.subject_id
        )

        # Re-derive hierarchy from the effective subject.
        derived_department_id, derived_program_id, derived_semester_id = (
            self._resolve_hierarchy(effective_subject_id)
        )

        # Validate explicitly-supplied hierarchy IDs against derived values.
        if new_department_id is not _NOT_PROVIDED and new_department_id is not None \
                and new_department_id != derived_department_id:
            raise ValueError("department_id does not match subject's department.")
        if new_program_id is not _NOT_PROVIDED and new_program_id is not None \
                and new_program_id != derived_program_id:
            raise ValueError("program_id does not match subject's program.")
        if new_semester_id is not _NOT_PROVIDED and new_semester_id is not None \
                and new_semester_id != derived_semester_id:
            raise ValueError("semester_id does not match subject's semester.")

        # Handle section_id.
        if new_section_id is not _NOT_PROVIDED:
            resolved_section_id = self._validate_section(
                new_section_id, derived_semester_id
            )
        elif new_subject_id is not _NOT_PROVIDED and resource.section_id is not None:
            # Subject changed: clear section if it no longer matches the new semester.
            section = db.session.get(Section, resource.section_id)
            if section is None or section.semester_id != derived_semester_id:
                resolved_section_id = None
            else:
                resolved_section_id = resource.section_id
        else:
            resolved_section_id = resource.section_id

        # Always persist derived values (corrects any drift).
        kwargs["department_id"] = derived_department_id
        kwargs["program_id"] = derived_program_id
        kwargs["semester_id"] = derived_semester_id
        kwargs["section_id"] = resolved_section_id
        kwargs["subject_id"] = effective_subject_id

        for key, value in kwargs.items():
            if not hasattr(resource, key):
                continue
            # Skip None for ordinary fields, but allow section_id=None to
            # clear the section. Derived hierarchy fields are never None here.
            if value is None and key != "section_id":
                continue
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
