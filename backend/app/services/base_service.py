"""Base service: composition of one-or-more repositories + audit.

Services:
- enforce business rules and emit domain exceptions (app.errors.exceptions)
- call repositories for persistence — never touch ORM sessions directly
- trigger side effects (audit entries, Celery tasks, socket emissions)
"""

from __future__ import annotations

from typing import Generic, TypeVar

from app.extensions import db

RepoT = TypeVar("RepoT")


class BaseService(Generic[RepoT]):
    """Common plumbing for feature services."""

    repository: RepoT

    # -- transaction helpers (thin wrappers; keep call sites readable) ------ #
    @staticmethod
    def commit() -> None:
        db.session.commit()

    @staticmethod
    def rollback() -> None:
        db.session.rollback()
