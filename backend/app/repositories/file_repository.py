"""File metadata persistence (Supabase Storage objects)."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from app.extensions import db
from app.models import FileRecord
from app.repositories.base_repository import BaseRepository


class FileRepository(BaseRepository[FileRecord]):
    model = FileRecord

    def get_by_storage_key(self, storage_key: str) -> FileRecord | None:
        stmt = sa.select(FileRecord).where(FileRecord.storage_key == storage_key)
        return db.session.scalar(stmt)

    def set_scan_result(
        self, file_id: uuid.UUID, status: str, scanned_at
    ) -> int:
        stmt = (
            sa.update(FileRecord)
            .where(FileRecord.id == file_id)
            .values(scan_status=status, scanned_at=scanned_at)
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)

    def pending_scans(self, limit: int = 100):
        stmt = (
            sa.select(FileRecord)
            .where(FileRecord.scan_status == "pending")
            .order_by(FileRecord.created_at.asc())
            .limit(limit)
        )
        return db.session.scalars(stmt).all()
