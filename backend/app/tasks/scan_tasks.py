"""
Async malware scan task. Per 06_SECURITY_GUIDE.md's upload pipeline and
API_SPEC_LIBRARY.md step 7: uploads enqueue this rather than blocking the
request on scan completion.

Deliberately thin — all real logic lives in
LibraryService._run_scan_and_update, which this task and the service's
inline-scan path both call, so scan-result handling never diverges between
sync and async execution.
"""
import logging
import uuid

from app.celery_app import celery_app

logger = logging.getLogger("campusvault.tasks.scan")


@celery_app.task(name="library.scan_file", max_retries=3, default_retry_delay=60)
def scan_file_task(file_id_str: str, storage_path: str) -> None:
    """
    Runs in a worker process, so it builds its own DB session and storage
    provider rather than receiving them from the request that enqueued it.
    Uses ClamAVScanner/SupabaseStorageProvider — the real production
    implementations — even though neither can be live-tested in this
    sandbox (see their module docstrings for why).
    """
    from app.services.library_service import LibraryService
    from app.utils.malware_scanner import ClamAVScanner
    from app.utils.storage import SupabaseStorageProvider

    file_id = uuid.UUID(file_id_str)
    storage = SupabaseStorageProvider()
    scanner = ClamAVScanner()

    try:
        content = storage.download(storage_path)
    except Exception:
        logger.exception("Failed to download file_id=%s from storage for scanning", file_id)
        raise  # lets Celery's retry policy (max_retries=3) kick in

    # DEPENDENCY NOT YET BUILT: this needs a worker-scoped DB session
    # factory from the app factory (app/__init__.py), which is still on the
    # project's Pending list (see PROJECT_MEMORY.md) — Celery workers need
    # their own SQLAlchemy session, separate from Flask's request-scoped
    # one used elsewhere via current_app.extensions["db_session"]. Wiring
    # this is part of the App Factory step, not invented here as a guess.
    from app.db import get_worker_session  # will exist once the app factory step is done

    db = get_worker_session()
    try:
        service = LibraryService(db, storage=storage, scanner=scanner)
        service._run_scan_and_update(file_id, content)
    finally:
        db.close()
