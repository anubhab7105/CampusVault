"""Resource persistence: hierarchical browsing + atomic counters."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from app.extensions import db
from app.models import Resource, Subject
from app.repositories.base_repository import BaseRepository


class ResourceRepository(BaseRepository[Resource]):
    model = Resource

    def browse(
        self,
        *,
        conditions: Sequence[sa.ColumnElement[bool]],
        q: str | None,
        sort_column: sa.ColumnElement,
        order: str,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[Resource], int]:
        """Filter + search + sort + paginate in one query path."""
        stmt = sa.select(Resource).where(*conditions, Resource.deleted_at.is_(None))
        if q:
            stmt = stmt.where(Resource.title.ilike(f"%{q}%"))
        direction = sort_column.desc() if order == "desc" else sort_column.asc()
        stmt = stmt.order_by(direction)
        count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        total = int(db.session.scalar(count_stmt) or 0)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return db.session.scalars(stmt).all(), total

    def subject_chain(self, subject_id: uuid.UUID):
        """Resolve Subject → Semester → Program for hierarchy-based filters."""
        stmt = sa.select(Subject).where(Subject.id == subject_id)
        return db.session.scalar(stmt)

    def increment_download(self, resource_id: uuid.UUID) -> int:
        stmt = (
            sa.update(Resource)
            .where(Resource.id == resource_id)
            .values(download_count=Resource.download_count + 1)
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)

    def increment_view(self, resource_id: uuid.UUID) -> int:
        stmt = (
            sa.update(Resource).where(Resource.id == resource_id).values(view_count=Resource.view_count + 1)
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)
