"""Audit log persistence (append-only)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.extensions import db
from app.models import AuditLog
from app.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def record(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        request_context: dict | None = None,
        changes: dict | None = None,
    ) -> AuditLog:
        row = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_context=request_context,
            changes=changes,
        )
        db.session.add(row)
        return row

    def timeline(
        self,
        *,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        action: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[AuditLog], int]:
        conditions = []
        if actor_id is not None:
            conditions.append(AuditLog.actor_id == actor_id)
        if entity_type is not None:
            conditions.append(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            conditions.append(AuditLog.entity_id == entity_id)
        if action is not None:
            conditions.append(AuditLog.action == action)
        return self.paginate(
            page,
            page_size,
            *conditions,
            order_by=AuditLog.created_at.desc(),
        )
