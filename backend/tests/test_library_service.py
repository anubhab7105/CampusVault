"""
Integration tests for LibraryService — real Postgres, real
LocalFilesystemStorageProvider (actual disk I/O, not mocked), and a
FakeScanner implementing the same ScannerProvider interface ClamAVScanner
does. This is the correct testing boundary: production code shouldn't
depend on a specific virus signature to pass its own tests, and this
sandbox can't reach ClamAV's definition CDN anyway (see
app/utils/malware_scanner.py's module docstring).
"""
import shutil
import tempfile
import uuid

import pytest

from app.models.auth import UserType
from app.models.library import ScanStatus
from app.repositories.auth_repository import AuthRepository
from app.services.library_service import ALLOWED_MIME_TYPES, MAX_FILE_SIZE_BYTES, LibraryService
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.utils.malware_scanner import ScannerProvider, ScanResult, ScanVerdict
from app.utils.storage import LocalFilesystemStorageProvider


class FakeScanner(ScannerProvider):
    """Controllable test double — returns whatever verdict the test configures."""

    def __init__(self, verdict: ScanVerdict = ScanVerdict.CLEAN, detail: str | None = None):
        self.verdict = verdict
        self.detail = detail
        self.calls = 0

    def scan_bytes(self, content: bytes) -> ScanResult:
        self.calls += 1
        return ScanResult(self.verdict, self.detail)


@pytest.fixture()
def storage():
    tmp_dir = tempfile.mkdtemp(prefix="campusvault_test_storage_")
    provider = LocalFilesystemStorageProvider(base_dir=tmp_dir)
    yield provider
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _make_user(db):
    auth_repo = AuthRepository(db)
    suffix = uuid.uuid4().hex[:8]
    user = auth_repo.create_user(f"libuser_{suffix}@college.edu", "Lib User", UserType.STUDENT)
    db.commit()
    return user


class TestUploadValidation:
    def test_upload_rejects_oversized_file(self, db, storage):
        service = LibraryService(db, storage=storage, scanner=FakeScanner())
        user = _make_user(db)
        oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)

        with pytest.raises(ValidationError) as exc_info:
            service.upload_file(user.id, "big.pdf", oversized, "application/pdf")
        assert exc_info.value.code == "FILE_TOO_LARGE"

    def test_upload_rejects_disallowed_mime_type(self, db, storage):
        service = LibraryService(db, storage=storage, scanner=FakeScanner())
        user = _make_user(db)

        with pytest.raises(ValidationError) as exc_info:
            service.upload_file(user.id, "virus.exe", b"content", "application/x-msdownload")
        assert exc_info.value.code == "MIME_TYPE_NOT_ALLOWED"

    def test_upload_accepts_all_whitelisted_types(self, db, storage):
        service = LibraryService(db, storage=storage, scanner=FakeScanner())
        user = _make_user(db)
        for mime in ALLOWED_MIME_TYPES:
            file = service.upload_file(user.id, "doc", b"content", mime)
            assert file.mime_type == mime


class TestUploadAndScanFlow:
    def test_upload_creates_file_with_random_stored_filename(self, db, storage):
        service = LibraryService(db, storage=storage, scanner=FakeScanner())
        user = _make_user(db)

        file = service.upload_file(user.id, "notes.pdf", b"pdf content", "application/pdf")
        assert file.original_filename == "notes.pdf"
        assert file.stored_filename != "notes.pdf"  # never reuse the client filename for storage
        assert file.stored_filename.endswith(".pdf")

    def test_upload_actually_writes_bytes_to_storage(self, db, storage):
        """Confirms real disk I/O happened, not just a DB row."""
        service = LibraryService(db, storage=storage, scanner=FakeScanner())
        user = _make_user(db)

        file = service.upload_file(user.id, "notes.pdf", b"exact bytes here", "application/pdf")
        from pathlib import Path
        assert Path(file.storage_path).read_bytes() == b"exact bytes here"

    def test_clean_scan_result_updates_status(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.CLEAN)
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)

        file = service.upload_file(user.id, "notes.pdf", b"content", "application/pdf")
        assert file.scan_status == ScanStatus.CLEAN
        assert scanner.calls == 1

    def test_infected_scan_result_updates_status(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.INFECTED, detail="Eicar-Test-Signature")
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)

        file = service.upload_file(user.id, "notes.pdf", b"content", "application/pdf")
        assert file.scan_status == ScanStatus.INFECTED

    def test_scan_error_leaves_status_pending_not_falsely_clean(self, db, storage):
        """Critical safety property: a scanner error must never be treated as 'clean'."""
        scanner = FakeScanner(verdict=ScanVerdict.ERROR, detail="clamd unreachable")
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)

        file = service.upload_file(user.id, "notes.pdf", b"content", "application/pdf")
        assert file.scan_status == ScanStatus.PENDING

    def test_scan_completion_notifies_uploader(self, db, storage):
        from app.services.notifications_service import NotificationsService

        scanner = FakeScanner(verdict=ScanVerdict.CLEAN)
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)

        service.upload_file(user.id, "notes.pdf", b"content", "application/pdf")

        notifications_service = NotificationsService(db)
        result = notifications_service.list_notifications(user.id, unread_only=False, before=None)
        assert len(result["items"]) == 1
        assert result["items"][0].type == "file.scanned"


class TestDownloadGating:
    def test_download_blocked_while_pending(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.ERROR)  # forces PENDING, never resolves
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)
        file = service.upload_file(user.id, "notes.pdf", b"content", "application/pdf")

        with pytest.raises(ValidationError) as exc_info:
            service.get_download_url(file.id)
        assert exc_info.value.code == "FILE_NOT_CLEAN"

    def test_download_blocked_when_infected(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.INFECTED)
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)
        file = service.upload_file(user.id, "notes.pdf", b"content", "application/pdf")

        with pytest.raises(ValidationError) as exc_info:
            service.get_download_url(file.id)
        assert exc_info.value.code == "FILE_INFECTED"

    def test_download_succeeds_when_clean(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.CLEAN)
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)
        file = service.upload_file(user.id, "notes.pdf", b"content", "application/pdf")

        result = service.get_download_url(file.id)
        assert "download_url" in result
        assert result["expires_in"] == 300


class TestResources:
    def test_create_resource_by_uploader_succeeds(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.CLEAN)
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)
        file = service.upload_file(user.id, "notes.pdf", b"content", "application/pdf")

        resource = service.create_resource(
            file.id, "My Notes", "desc", uploaded_by=user.id,
            department_id=None, program_id=None, subject_id=None,
        )
        assert resource.title == "My Notes"

    def test_create_resource_by_non_uploader_rejected(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.CLEAN)
        service = LibraryService(db, storage=storage, scanner=scanner)
        owner = _make_user(db)
        other = _make_user(db)
        file = service.upload_file(owner.id, "notes.pdf", b"content", "application/pdf")

        with pytest.raises(ForbiddenError) as exc_info:
            service.create_resource(
                file.id, "Stolen Notes", None, uploaded_by=other.id,
                department_id=None, program_id=None, subject_id=None,
            )
        assert exc_info.value.code == "FILE_NOT_OWNED_BY_USER"

    def test_create_resource_unknown_file_raises(self, db, storage):
        service = LibraryService(db, storage=storage, scanner=FakeScanner())
        user = _make_user(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.create_resource(
                uuid.uuid4(), "X", None, uploaded_by=user.id,
                department_id=None, program_id=None, subject_id=None,
            )
        assert exc_info.value.code == "FILE_NOT_FOUND"

    def test_list_resources_excludes_non_clean_by_default(self, db, storage):
        clean_scanner = FakeScanner(verdict=ScanVerdict.CLEAN)
        infected_scanner = FakeScanner(verdict=ScanVerdict.INFECTED)
        user = _make_user(db)

        clean_service = LibraryService(db, storage=storage, scanner=clean_scanner)
        clean_file = clean_service.upload_file(user.id, "clean.pdf", b"c", "application/pdf")
        clean_service.create_resource(
            clean_file.id, "Clean Resource", None, uploaded_by=user.id,
            department_id=None, program_id=None, subject_id=None,
        )

        infected_service = LibraryService(db, storage=storage, scanner=infected_scanner)
        infected_file = infected_service.upload_file(user.id, "bad.pdf", b"b", "application/pdf")
        infected_service.create_resource(
            infected_file.id, "Infected Resource", None, uploaded_by=user.id,
            department_id=None, program_id=None, subject_id=None,
        )

        results = clean_service.list_resources()
        titles = [r.title for r in results]
        assert "Clean Resource" in titles
        assert "Infected Resource" not in titles

    def test_mine_filter_bypasses_clean_gate(self, db, storage):
        """Open item resolved: uploaders can see their own pending/infected resources."""
        scanner = FakeScanner(verdict=ScanVerdict.INFECTED)
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)
        file = service.upload_file(user.id, "bad.pdf", b"b", "application/pdf")
        service.create_resource(
            file.id, "My Infected Upload", None, uploaded_by=user.id,
            department_id=None, program_id=None, subject_id=None,
        )

        normal_results = service.list_resources()
        assert "My Infected Upload" not in [r.title for r in normal_results]

        mine_results = service.list_resources(mine_user_id=user.id)
        assert "My Infected Upload" in [r.title for r in mine_results]

    def test_update_resource_by_non_owner_without_manage_any_rejected(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.CLEAN)
        service = LibraryService(db, storage=storage, scanner=scanner)
        owner = _make_user(db)
        other = _make_user(db)
        file = service.upload_file(owner.id, "notes.pdf", b"c", "application/pdf")
        resource = service.create_resource(
            file.id, "Title", None, uploaded_by=owner.id,
            department_id=None, program_id=None, subject_id=None,
        )

        with pytest.raises(ForbiddenError):
            service.update_resource(
                resource.id, actor_id=other.id, title="Hijacked", description=None,
                department_id=None, program_id=None, subject_id=None,
            )

    def test_delete_resource_soft_deletes(self, db, storage):
        scanner = FakeScanner(verdict=ScanVerdict.CLEAN)
        service = LibraryService(db, storage=storage, scanner=scanner)
        user = _make_user(db)
        file = service.upload_file(user.id, "notes.pdf", b"c", "application/pdf")
        resource = service.create_resource(
            file.id, "To Delete", None, uploaded_by=user.id,
            department_id=None, program_id=None, subject_id=None,
        )

        service.delete_resource(resource.id, actor_id=user.id)

        with pytest.raises(NotFoundError):
            service.update_resource(
                resource.id, actor_id=user.id, title="x", description=None,
                department_id=None, program_id=None, subject_id=None,
            )
