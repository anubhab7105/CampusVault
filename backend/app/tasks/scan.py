"""Celery task for malware scanning."""

from __future__ import annotations

import celery_task  # placeholder for Celery app instance
from uuid import UUID

from app.services.scanner import ClamAVScanner, NoOpScanner
from app.services.storage import LocalFileStorage, SupabaseStorage
from app.errors.exceptions import ServiceUnavailableError
from app.extensions import db

@celery_task.task(bind=True, max_retries=3, default_retry_delay=2)
def scan_file_task(self, file_id: str, storage_type: str = "supabase", scanner_type: str = "auto"):
    """Scan a file and update its ``scan_status`` in the database.

    Args:
        file_id: string UUID of the ``files`` row.
        storage_type: ``"supabase"`` or ``"local"`` — which storage back-end to use.
        scanner_type: ``"clamav"`` or ``"noop"`` — which scanner to use.
    """
    from app.models import FileRecord

    file_record = db.session.get(FileRecord, UUID(file_id))
    if file_record is None:
        raise self.retry(exc=ValueError(f"File record {file_id} not found"), countdown=60)

    # --- Choose scanner -------------------------------------------------------
    if scanner_type == "clamav":
        scanner = ClamAVScanner()
    else:
        scanner = NoOpScanner()

    # --- Choose storage -------------------------------------------------------
    if storage_type == "supabase":
        storage = SupabaseStorage()
    else:
        storage = LocalFileStorage()

    try:
        # --- Run the scan -------------------------------------------------------
        data = storage.download(file_record.storage_key)

        result = scanner.scan(data, file_record.mime_type)

        # --- Update the database -----------------------------------------------
        file_record.scan_status = result["status"]
        file_record.scan_confidence = result.get("confidence", 0.0)
        file_record.scan_error = None
        db.session.commit()

    except Exception as exc:
        # --- Transient failure: retry with exponential backoff ------------------
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)

        # --- Permanent failure -------------------------------------------------
        file_record.scan_status = "failed"
        file_record.scan_error = str(exc)
        db.session.commit()
