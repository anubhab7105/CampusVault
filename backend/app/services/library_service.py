"""
Library domain service. Implements API_SPEC_LIBRARY.md, including the
upload security pipeline from 06_SECURITY_GUIDE.md and the two Open Items
resolved during Backend Implementation: async scan-completion notification,
and the "my uploads" filter that bypasses the clean-only gate.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.library import ScanStatus
from app.repositories.academic_repository import AcademicRepository
from app.repositories.auth_repository import AuthRepository
from app.repositories.library_repository import LibraryRepository
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.utils.malware_scanner import ScannerProvider, ScanVerdict
from app.utils.storage import StorageProvider, generate_storage_key

# OPEN_DECISIONS.md defaults
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "image/png",
    "image/jpeg",
}
DOWNLOAD_URL_EXPIRES_IN = 300  # 5 minutes


class LibraryService:
    def __init__(self, db: Session, storage: StorageProvider, scanner: ScannerProvider | None = None, socketio=None):
        self.db = db
        self.repo = LibraryRepository(db)
        self.auth_repo = AuthRepository(db)
        self.academic_repo = AcademicRepository(db)
        self.storage = storage
        self.scanner = scanner  # None is valid: scan happens async via Celery, not inline
        self.socketio = socketio

    # ---------- Upload ----------

    def upload_file(self, uploader_id: uuid.UUID, original_filename: str, content: bytes, mime_type: str):
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise ValidationError("File exceeds the maximum allowed size.", code="FILE_TOO_LARGE", http_status=413)
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                "File type is not allowed.", code="MIME_TYPE_NOT_ALLOWED", http_status=415
            )

        storage_key = generate_storage_key(original_filename)
        storage_path = self.storage.upload(content, storage_key)

        file = self.repo.create_file(
            uploader_id=uploader_id, original_filename=original_filename, stored_filename=storage_key,
            mime_type=mime_type, size_bytes=len(content), storage_path=storage_path,
        )
        self.db.commit()

        # Real deployments enqueue a Celery task here (app/tasks/scan_tasks.py)
        # for async scanning. If a scanner was injected directly (e.g. for a
        # synchronous test or a small-scale sync deployment), scan inline too.
        if self.scanner is not None:
            self._run_scan_and_update(file.id, content)

        return file

    def _run_scan_and_update(self, file_id: uuid.UUID, content: bytes):
        """
        Shared by the inline path above and app/tasks/scan_tasks.py's async
        Celery task — both call this exact method so scan-result handling
        never diverges between the sync and async paths.
        """
        file = self.repo.get_file_by_id(file_id)
        if file is None:
            return

        result = self.scanner.scan_bytes(content)
        if result.verdict == ScanVerdict.CLEAN:
            self.repo.update_scan_status(file, ScanStatus.CLEAN)
        elif result.verdict == ScanVerdict.INFECTED:
            self.repo.update_scan_status(file, ScanStatus.INFECTED)
        else:
            # ERROR: leave as pending rather than falsely marking clean or
            # infected — a retry (re-enqueue) is the caller's responsibility.
            self.db.commit()
            return
        self.db.commit()

        self._notify_scan_complete(file)

    def _notify_scan_complete(self, file) -> None:
        """Open item resolved: notify the uploader when an async scan finishes."""
        from app.services.notifications_service import NotificationsService

        try:
            notifications_service = NotificationsService(self.db, socketio=self.socketio)
            status_label = "clean" if file.scan_status == ScanStatus.CLEAN else "flagged as unsafe"
            notifications_service.create_for_user(
                user_id=file.uploader_id,
                type_="file.scanned",
                title=f"Your upload finished scanning: {status_label}",
                body=file.original_filename,
                data={"file_id": str(file.id), "scan_status": file.scan_status.value},
            )
        except Exception:
            import logging
            logging.getLogger("campusvault.library").exception("Failed to send scan-complete notification")

    def get_file(self, file_id: uuid.UUID):
        file = self.repo.get_file_by_id(file_id)
        if file is None:
            raise NotFoundError("File not found.", code="FILE_NOT_FOUND")
        return file

    def get_download_url(self, file_id: uuid.UUID) -> dict:
        file = self.get_file(file_id)
        if file.scan_status == ScanStatus.INFECTED:
            raise ValidationError("File failed the malware scan.", code="FILE_INFECTED", http_status=410)
        if file.scan_status != ScanStatus.CLEAN:
            raise ValidationError("File has not finished scanning yet.", code="FILE_NOT_CLEAN", http_status=409)

        url = self.storage.get_signed_url(file.storage_path, DOWNLOAD_URL_EXPIRES_IN)
        return {"download_url": url, "expires_in": DOWNLOAD_URL_EXPIRES_IN}

    # ---------- Resources ----------

    def create_resource(
        self, file_id: uuid.UUID, title: str, description: str | None, uploaded_by: uuid.UUID,
        department_id: uuid.UUID | None, program_id: uuid.UUID | None, subject_id: uuid.UUID | None,
    ):
        file = self.get_file(file_id)
        if file.uploader_id != uploaded_by:
            raise ForbiddenError("You did not upload this file.", code="FILE_NOT_OWNED_BY_USER")

        if department_id is not None and self.academic_repo.get_department_by_id(department_id) is None:
            raise NotFoundError("Department not found.", code="DEPARTMENT_NOT_FOUND")
        if program_id is not None and self.academic_repo.get_program_by_id(program_id) is None:
            raise NotFoundError("Program not found.", code="PROGRAM_NOT_FOUND")
        if subject_id is not None and self.academic_repo.get_subject_by_id(subject_id) is None:
            raise NotFoundError("Subject not found.", code="SUBJECT_NOT_FOUND")

        resource = self.repo.create_resource(
            file_id, title, description, uploaded_by, department_id, program_id, subject_id
        )
        self.db.commit()
        return resource

    def update_resource(
        self, resource_id: uuid.UUID, actor_id: uuid.UUID, title: str | None, description: str | None,
        department_id: uuid.UUID | None, program_id: uuid.UUID | None, subject_id: uuid.UUID | None,
        actor_can_manage_any: bool = False,
    ):
        resource = self.repo.get_resource_by_id(resource_id)
        if resource is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        if resource.uploaded_by != actor_id and not actor_can_manage_any:
            raise ForbiddenError("Not the uploader of this resource.", code="FORBIDDEN")

        resource = self.repo.update_resource(resource, title, description, department_id, program_id, subject_id)
        self.db.commit()
        return resource

    def delete_resource(self, resource_id: uuid.UUID, actor_id: uuid.UUID, actor_can_manage_any: bool = False):
        resource = self.repo.get_resource_by_id(resource_id)
        if resource is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        if resource.uploaded_by != actor_id and not actor_can_manage_any:
            raise ForbiddenError("Not the uploader of this resource.", code="FORBIDDEN")
        self.repo.soft_delete_resource(resource)
        self.db.commit()

    def list_resources(
        self, department_id: uuid.UUID | None = None, program_id: uuid.UUID | None = None,
        subject_id: uuid.UUID | None = None, query: str | None = None,
        mine_user_id: uuid.UUID | None = None,
    ):
        """
        Per API_SPEC_LIBRARY.md's Open Items: `mine_user_id` set bypasses the
        clean-only gate so an uploader can see their own pending/infected
        files; normal listing only ever returns scan_status=clean resources.
        """
        only_clean = mine_user_id is None
        return self.repo.list_resources(
            department_id, program_id, subject_id, query, only_clean, uploader_id=mine_user_id
        )
