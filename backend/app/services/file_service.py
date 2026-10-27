"""File service — upload policy enforcement + Supabase Storage placement.

Policy (docs/06_SECURITY_GUIDE.md):
- MIME validation + extension whitelist + size cap happen *before* storage
- stored filename is random (never derived from the user's filename)
- the row lands with scan_status=pending; the Celery malware pipeline moves it
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from flask import current_app

from app.constants import SCAN_STATUS_PENDING
from app.errors.exceptions import ValidationError
from app.extensions import db
from app.models import FileRecord
from app.repositories import FileRepository
from app.services.audit_service import audit_service
from app.services.base_service import BaseService


class FileService(BaseService):
    def __init__(self) -> None:
        self.files = FileRepository()

    @staticmethod
    def validate_upload(filename: str, content_type: str, size_bytes: int) -> None:
        cfg = current_app.config
        allowed: frozenset[str] = frozenset(cfg["UPLOAD_ALLOWED_EXTENSIONS"])
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in allowed:
            raise ValidationError(f"File type .{extension or 'unknown'} is not allowed.")
        if int(size_bytes) > cfg["UPLOAD_MAX_SIZE_BYTES"]:
            max_mb = cfg["UPLOAD_MAX_SIZE_BYTES"] // (1024 * 1024)
            raise ValidationError(f"File exceeds the {max_mb}MB upload limit.")
        if content_type and content_type.startswith("application/x-executable"):
            raise ValidationError("Executable uploads are rejected.")

    @staticmethod
    def build_storage_key(uploader_id: uuid.UUID, filename: str) -> str:
        """Random storage name; extension survives, the identity does not."""
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        return f"uploads/{uploader_id}/{secrets.token_hex(12)}.{extension}"

    def create(
        self,
        *,
        uploader_id: uuid.UUID,
        original_filename: str,
        content_type: str,
        size_bytes: int,
        subject_id: uuid.UUID | None = None,
        checksum_hex: str | None = None,
    ) -> FileRecord:
        """Register the metadata row (the caller uploads bytes to Storage)."""
        cfg = current_app.config
        row = self.files.create(
            uploader_id=uploader_id,
            subject_id=subject_id,
            original_filename=original_filename[:255],
            storage_key=self.build_storage_key(uploader_id, original_filename),
            bucket=cfg["SUPABASE_STORAGE_BUCKET"],
            mime_type=content_type[:127],
            file_size=int(size_bytes),
            sha256_checksum=checksum_hex,
            scan_status=SCAN_STATUS_PENDING,
        )
        audit_service.record(
            action="file.upload",
            entity_type="file",
            entity_id=row.id,
        )
        db.session.commit()
        return row

    def register_scan_result(self, file_id: uuid.UUID, status: str) -> None:
        self.files.set_scan_result(file_id, status, datetime.now(tz=UTC))
        db.session.commit()


file_service = FileService()
