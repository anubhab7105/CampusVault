"""Periodic health task — re‑queue files stuck in ``pending`` or ``scanning``."""

from __future__ import annotations

from datetime import UTC

from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.extensions import db
from app.models import FileRecord
from app.tasks.scan import scan_file_task
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(bind=True, ignore_result=True)
def requeue_stuck_files(self):
    """Re‑queue files stuck in ``pending`` or ``scanning`` for > 30 minutes."""
    from datetime import datetime, timedelta

    stale_threshold = datetime.now(UTC) - timedelta(minutes=30)

    # Find files stuck in ``pending``.
    stmt = select(FileRecord).where(
        FileRecord.scan_status.in_(["pending", "scanning"]),
        FileRecord.created_at < stale_threshold,
    )
    stuck = db.session.scalars(stmt).all()

    for file_record in stuck:
        logger.info(f"Re‑queuing stuck scan for file {file_record.id} (status={file_record.scan_status})")
        # Re‑invoke the scan task; this will reset the status to ``pending``
        # so the scanner can have another go.
        scan_file_task.delay(str(file_record.id), storage_type="supabase", scanner_type="noop")

    if stuck:
        logger.info(f"Re‑queued {len(stuck)} file(s).")
