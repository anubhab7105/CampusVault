"""Celery task for malware scanning."""

from __future__ import annotations

import celery_task  # placeholder for Celery app instance
from app.services.scanner import Scanner, ClamAVScanner, NoOpScanner
from app.services.storage import SupabaseStorage, LocalFileStorage


@celery_task.task(bind=True, max_retries=3, default_retry_delay=2)
def scan_file_task(self, file_id: str, storage_type: str = "supabase", scanner_type: str = "auto"):
    """Scan a file and update its ``scan_status`` in the database.

    Args:
        file_id: string UUID of the ``files`` row.
        storage_type: ``"supabase"`` or ``"local"`` — which storage back-end to use.
        scanner_type: ``"clamav"`` or ``"noop"`` — which scanner to use.
    """
    from app.extensions import db
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
        data = storage.download(file_record.storage_key)
    except Exception as exc:  # noqa: broad – network / permission issues
        raise self.retry(exc=exc, countdown=60)

    result = scanner.scan(data, file_record.mime_type)

    # Update the DB
    file_record.scan_status = result["status"]
    db.session.commit()

    # --- Notify on infected -------------------------------------------------
    if result["status"] == "infected":
        # TODO: emit notification via the Phase 1 notification service.
        # e.g. notify_scan_infected.delay(uploader_id, file_id)
        pass

    # Retry policy: if status is ``"failed"`` and we have retries left, retry;
    # otherwise stop.
    if result["status"] == "failed" and self.request.retries < self.max_retries:
        raise self.retry(exc=ServiceUnavailableError("Transient scan failure"), countdown=2 ** self.request.retries)