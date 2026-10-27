"""Audit service — single entry point for audit events (append-only)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from flask import has_request_context, request
from flask_jwt_extended import get_jwt_identity

from app.models import AuditLog
from app.repositories import AuditLogRepository


class AuditService:
    def __init__(self) -> None:
        self.repository = AuditLogRepository()

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        changes: dict | None = None,
    ) -> AuditLog:
        """Record one event; committed with the caller's transaction."""
        if actor_id is None:
            identity = get_jwt_identity() if has_request_context() else None
            actor_id = uuid.UUID(str(identity)) if identity else None
        return self.repository.record(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_context=self._request_context(),
            changes=changes,
        )

    @staticmethod
    def _request_context() -> dict | None:
        if not has_request_context():
            return None
        request_id = getattr(request, "environ", {}).get("campusvault.request_id")
        return {
            "route": request.path,
            "method": request.method,
            "ip": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "")[:256],
            "request_id": request_id,
        }

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
        return self.repository.timeline(
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            page=page,
            page_size=page_size,
        )


audit_service = AuditService()
