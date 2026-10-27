"""Generic repository.

All DB access goes through repositories (docs/04_BACKEND_GUIDE.md). This base
class implements the reusable read/write/soft-delete primitives; concrete
repositories add the domain-specific queries. Business rules stay in
services — repositories return rows, never decide policy.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

import sqlalchemy as sa
from sqlalchemy import func

from app.extensions import db
from app.models.base import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    """CRUD + soft-delete + pagination for one model type."""

    model: type[ModelT]

    # --- Reads ------------------------------------------------------------- #

    def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        return db.session.get(self.model, entity_id)

    def get_active_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        """Fetch a non-soft-deleted row."""
        row = self.get_by_id(entity_id)
        if row is None:
            return None
        if hasattr(row, "deleted_at") and row.deleted_at is not None:
            return None
        return row

    def list_all(self, *, limit: int | None = None) -> Sequence[ModelT]:
        stmt = sa.select(self.model)
        self._apply_soft_delete_filter(stmt)
        if limit:
            stmt = stmt.limit(limit)
        return db.session.scalars(stmt).all()

    # --- Writes ------------------------------------------------------------ #

    def create(self, **values: Any) -> ModelT:
        row = self.model(**values)
        db.session.add(row)
        return row

    def update(self, row: ModelT, **values: Any) -> ModelT:
        for key, value in values.items():
            setattr(row, key, value)
        db.session.add(row)
        return row

    def delete(self, row: ModelT) -> None:
        """Hard delete — use only where soft delete is not applicable."""
        db.session.delete(row)

    def soft_delete(self, row: ModelT) -> ModelT:
        if not hasattr(row, "deleted_at"):
            raise NotImplementedError(f"{self.model.__name__} hard-deletes only")
        row.deleted_at = dt.datetime.now(tz=dt.timezone.utc)
        db.session.add(row)
        return row

    # --- Counting / pagination ------------------------------------------------ #

    def count(self, *conditions: sa.ColumnElement[bool]) -> int:
        stmt = sa.select(func.count()).select_from(self.model)
        for condition in conditions:
            stmt = stmt.where(condition)
        self._apply_soft_delete_filter(stmt)
        return int(db.session.scalar(stmt) or 0)

    def paginate(
        self,
        page: int,
        page_size: int,
        *conditions: sa.ColumnElement[bool],
        order_by: sa.ColumnElement | None = None,
    ) -> tuple[Sequence[ModelT], int]:
        """Return ``(rows, total)`` for a page-bound query."""
        stmt = sa.select(self.model).where(*conditions)
        self._apply_soft_delete_filter(stmt)
        total = int(db.session.scalar(sa.select(func.count()).select_from(stmt.subquery())) or 0)

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        return db.session.scalars(stmt).all(), total

    # --- Commit boundary -------------------------------------------------------- #

    @staticmethod
    def commit() -> None:
        db.session.commit()

    @staticmethod
    def flush() -> None:
        db.session.flush()

    # --- internals ------------------------------------------------------------ #

    def _apply_soft_delete_filter(self, stmt: sa.Select) -> sa.Select:
        """Exclude soft-deleted rows when the model supports them."""
        if hasattr(self.model, "deleted_at"):
            return stmt.where(self.model.deleted_at.is_(None))
        return stmt
