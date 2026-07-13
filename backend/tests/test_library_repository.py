"""
Direct integration tests for LibraryRepository — covers filter/update paths
not exercised through LibraryService's tests (which focus on business logic,
not every repository query variant).
"""
import uuid

from app.models.auth import UserType
from app.models.library import ScanStatus
from app.repositories.academic_repository import AcademicRepository
from app.repositories.auth_repository import AuthRepository
from app.repositories.library_repository import LibraryRepository


def _make_user(db):
    auth_repo = AuthRepository(db)
    suffix = uuid.uuid4().hex[:8]
    user = auth_repo.create_user(f"librepo_{suffix}@college.edu", "Repo User", UserType.STUDENT)
    db.commit()
    return user


def _make_clean_file_and_resource(db, repo, user, title, department_id=None, program_id=None, subject_id=None):
    file = repo.create_file(user.id, "notes.pdf", f"{uuid.uuid4().hex}.pdf", "application/pdf", 100, "/tmp/x")
    repo.update_scan_status(file, ScanStatus.CLEAN)
    resource = repo.create_resource(file.id, title, None, user.id, department_id, program_id, subject_id)
    db.flush()
    return file, resource


class TestUpdateResourceFields:
    def test_update_resource_all_fields(self, db):
        repo = LibraryRepository(db)
        academic_repo = AcademicRepository(db)
        user = _make_user(db)
        dept = academic_repo.create_department("Update Dept", "UD1")
        program = academic_repo.create_program(dept.id, "Update Program", "UP1", 4)
        db.flush()

        _file, resource = _make_clean_file_and_resource(db, repo, user, "Original Title")

        updated = repo.update_resource(
            resource, title="New Title", description="New Desc",
            department_id=dept.id, program_id=program.id, subject_id=None,
        )
        assert updated.title == "New Title"
        assert updated.description == "New Desc"
        assert updated.department_id == dept.id
        assert updated.program_id == program.id

    def test_update_resource_partial_leaves_other_fields_unchanged(self, db):
        repo = LibraryRepository(db)
        user = _make_user(db)
        _file, resource = _make_clean_file_and_resource(db, repo, user, "Keep This Title")

        updated = repo.update_resource(
            resource, title=None, description="Only description changes",
            department_id=None, program_id=None, subject_id=None,
        )
        assert updated.title == "Keep This Title"
        assert updated.description == "Only description changes"

    def test_soft_delete_resource(self, db):
        repo = LibraryRepository(db)
        user = _make_user(db)
        _file, resource = _make_clean_file_and_resource(db, repo, user, "To Delete")

        repo.soft_delete_resource(resource)
        assert repo.get_resource_by_id(resource.id) is None


class TestListResourcesFilters:
    def test_filter_by_program_id(self, db):
        repo = LibraryRepository(db)
        academic_repo = AcademicRepository(db)
        user = _make_user(db)
        dept = academic_repo.create_department("Filter Dept", "FD1")
        program_a = academic_repo.create_program(dept.id, "Program A", "PA1", 4)
        program_b = academic_repo.create_program(dept.id, "Program B", "PB1", 4)
        db.flush()

        _make_clean_file_and_resource(db, repo, user, "In Program A", program_id=program_a.id)
        _make_clean_file_and_resource(db, repo, user, "In Program B", program_id=program_b.id)

        results = repo.list_resources(None, program_a.id, None, None, only_clean=True, uploader_id=None)
        titles = [r.title for r in results]
        assert "In Program A" in titles
        assert "In Program B" not in titles

    def test_filter_by_subject_id(self, db):
        repo = LibraryRepository(db)
        academic_repo = AcademicRepository(db)
        user = _make_user(db)
        dept = academic_repo.create_department("Subj Dept", "SJ1")
        program = academic_repo.create_program(dept.id, "Subj Program", "SJP1", 4)
        subject = academic_repo.create_subject(program.id, 1, "Test Subject", "TS101")
        db.flush()

        _make_clean_file_and_resource(db, repo, user, "Subject Resource", subject_id=subject.id)
        _make_clean_file_and_resource(db, repo, user, "No Subject Resource")

        results = repo.list_resources(None, None, subject.id, None, only_clean=True, uploader_id=None)
        titles = [r.title for r in results]
        assert "Subject Resource" in titles
        assert "No Subject Resource" not in titles

    def test_search_query_matches_title_and_description(self, db):
        repo = LibraryRepository(db)
        user = _make_user(db)
        file = repo.create_file(user.id, "x.pdf", f"{uuid.uuid4().hex}.pdf", "application/pdf", 10, "/tmp/x")
        repo.update_scan_status(file, ScanStatus.CLEAN)
        repo.create_resource(file.id, "Database Systems Notes", "Covers SQL basics", user.id, None, None, None)
        db.flush()

        by_title = repo.list_resources(None, None, None, "Database", only_clean=True, uploader_id=None)
        assert any(r.title == "Database Systems Notes" for r in by_title)

        by_description = repo.list_resources(None, None, None, "SQL basics", only_clean=True, uploader_id=None)
        assert any(r.title == "Database Systems Notes" for r in by_description)

        no_match = repo.list_resources(None, None, None, "Completely Unrelated Term", only_clean=True, uploader_id=None)
        assert len(no_match) == 0

    def test_uploader_filter_ignores_clean_gate(self, db):
        repo = LibraryRepository(db)
        user = _make_user(db)
        file = repo.create_file(user.id, "pending.pdf", f"{uuid.uuid4().hex}.pdf", "application/pdf", 10, "/tmp/x")
        # Deliberately left as PENDING (default) — not marked clean.
        repo.create_resource(file.id, "Pending Resource", None, user.id, None, None, None)
        db.flush()

        mine = repo.list_resources(None, None, None, None, only_clean=False, uploader_id=user.id)
        assert any(r.title == "Pending Resource" for r in mine)


class TestFileRepository:
    def test_create_and_get_file(self, db):
        repo = LibraryRepository(db)
        user = _make_user(db)
        file = repo.create_file(user.id, "a.pdf", "random123.pdf", "application/pdf", 500, "/tmp/random123.pdf")

        fetched = repo.get_file_by_id(file.id)
        assert fetched is not None
        assert fetched.scan_status == ScanStatus.PENDING

    def test_update_scan_status_sets_scanned_at(self, db):
        repo = LibraryRepository(db)
        user = _make_user(db)
        file = repo.create_file(user.id, "a.pdf", "r1.pdf", "application/pdf", 500, "/tmp/r1.pdf")

        assert file.scanned_at is None
        repo.update_scan_status(file, ScanStatus.CLEAN)
        assert file.scanned_at is not None
        assert file.scan_status == ScanStatus.CLEAN
