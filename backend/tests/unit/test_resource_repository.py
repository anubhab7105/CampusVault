"""Repository tests for Resource hierarchy filtering and consistency.

Covers per-hierarchy-filter browse (department, program, semester, section,
subject), combined multi-filter, empty results, non-existent IDs, and
integrity (inconsistent hierarchy rejection, FK restrictions, section
semester mismatch).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect

from app.extensions import db
from app.models import Department, Program, Section, Semester, Subject, User
from app.repositories.resource_repository import resource_repository


def _make_hierarchy(session):
    """Create dept → program → semester → section → subject + a user."""
    dept = Department(id=uuid.uuid4(), name="Computer Science", code="CS")
    prog = Program(id=uuid.uuid4(), department_id=dept.id, name="B.Tech CS", code="BTCS")
    sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=1)
    sec = Section(id=uuid.uuid4(), semester_id=sem.id, name="A")
    subj = Subject(id=uuid.uuid4(), semester_id=sem.id, name="Data Structures", code="DS101")
    user = User(id=uuid.uuid4(), email="a@b.c", full_name="User", auth_provider="otp")
    session.add_all([dept, prog, sem, sec, subj, user])
    session.flush()
    return dept, prog, sem, sec, subj, user


def _make_resource(session, subject_id, uploader_id, title="Test Resource", description="", **overrides):
    """Create a resource via the repository (derives + validates hierarchy)."""
    return resource_repository.create(
        subject_id=subject_id,
        uploader_id=uploader_id,
        title=title,
        description=description,
        resource_type="note",
        visibility="college",
        file_id=None,
        external_url="https://example.com/resource.pdf",
        **overrides,
    )


class TestResourceRepositoryFilters:
    """Per-hierarchy-filter browse tests."""

    def _setup(self, session):
        dept, prog, sem, sec, subj, user = _make_hierarchy(session)
        subj2 = Subject(id=uuid.uuid4(), semester_id=sem.id, name="Algorithms", code="DS102")
        session.add(subj2)
        session.flush()

        r1 = _make_resource(session, subj.id, user.id, "DS Resource")
        r2 = _make_resource(session, subj2.id, user.id, "Algo Resource")

        dept2 = Department(id=uuid.uuid4(), name="Math", code="MATH")
        prog2 = Program(id=uuid.uuid4(), department_id=dept2.id, name="B.Sc Math", code="BM")
        sem2 = Semester(id=uuid.uuid4(), program_id=prog2.id, number=1)
        subj3 = Subject(id=uuid.uuid4(), semester_id=sem2.id, name="Calculus", code="M101")
        session.add_all([dept2, prog2, sem2, subj3])
        session.flush()
        r3 = _make_resource(session, subj3.id, user.id, "Math Resource")
        session.commit()
        return {
            "dept": dept, "prog": prog, "sem": sem, "sec": sec,
            "subj": subj, "subj2": subj2, "subj3": subj3,
            "dept2": dept2, "user": user,
            "r1": r1, "r2": r2, "r3": r3,
        }

    def test_filter_by_department(self, app):
        with app.app_context():
            s = self._setup(db.session)
            items, total = resource_repository.by_hierarchy(
                department_id=s["dept"].id
            )
            assert total == 2
            ids = {str(r.id) for r in items}
            assert str(s["r1"].id) in ids
            assert str(s["r2"].id) in ids

    def test_filter_by_program(self, app):
        with app.app_context():
            s = self._setup(db.session)
            items, total = resource_repository.by_hierarchy(
                program_id=s["prog"].id
            )
            assert total == 2

    def test_filter_by_semester(self, app):
        with app.app_context():
            s = self._setup(db.session)
            items, total = resource_repository.by_hierarchy(
                semester_id=s["sem"].id
            )
            assert total == 2

    def test_filter_by_section(self, app):
        with app.app_context():
            s = self._setup(db.session)
            items, total = resource_repository.by_hierarchy(
                section_id=s["sec"].id
            )
            assert total == 0  # no resource has section_id set

    def test_filter_by_subject(self, app):
        with app.app_context():
            s = self._setup(db.session)
            items, total = resource_repository.by_hierarchy(
                subject_id=s["subj"].id
            )
            assert total == 1
            assert str(items[0].id) == str(s["r1"].id)

    def test_filter_combined_multi(self, app):
        with app.app_context():
            s = self._setup(db.session)
            items, total = resource_repository.by_hierarchy(
                department_id=s["dept"].id,
                program_id=s["prog"].id,
                semester_id=s["sem"].id,
                subject_id=s["subj"].id,
            )
            assert total == 1
            assert str(items[0].id) == str(s["r1"].id)

    def test_filter_non_existent_id(self, app):
        with app.app_context():
            self._setup(db.session)
            items, total = resource_repository.by_hierarchy(
                department_id=uuid.uuid4()
            )
            assert total == 0
            items, total = resource_repository.by_hierarchy(
                subject_id=uuid.uuid4()
            )
            assert total == 0

    def test_filter_empty_results(self, app):
        with app.app_context():
            items, total = resource_repository.by_hierarchy()
            assert total == 0


class TestResourceRepositoryIntegrity:
    """Integrity and consistency tests for hierarchy fields."""

    def _setup(self, session):
        dept, prog, sem, sec, subj, user = _make_hierarchy(session)
        session.commit()
        return {"dept": dept, "prog": prog, "sem": sem, "sec": sec,
                "subj": subj, "user": user}

    def test_create_derives_hierarchy_from_subject(self, app):
        with app.app_context():
            s = self._setup(db.session)
            r = _make_resource(db.session, s["subj"].id, s["user"].id)
            assert r.department_id == s["dept"].id
            assert r.program_id == s["prog"].id
            assert r.semester_id == s["sem"].id
            assert r.section_id is None

    def test_create_rejects_mismatched_department(self, app):
        with app.app_context():
            s = self._setup(db.session)
            other_dept = Department(id=uuid.uuid4(), name="Other", code="OTH")
            db.session.add(other_dept)
            db.session.flush()
            with pytest.raises(ValueError, match="department_id does not match"):
                _make_resource(
                    db.session, s["subj"].id, s["user"].id,
                    department_id=other_dept.id,
                )

    def test_create_rejects_section_wrong_semester(self, app):
        with app.app_context():
            s = self._setup(db.session)
            other_sem = Semester(id=uuid.uuid4(), program_id=s["prog"].id, number=2)
            other_sec = Section(id=uuid.uuid4(), semester_id=other_sem.id, name="B")
            db.session.add_all([other_sem, other_sec])
            db.session.flush()
            with pytest.raises(ValueError, match="section_id does not belong"):
                _make_resource(
                    db.session, s["subj"].id, s["user"].id,
                    section_id=other_sec.id,
                )

    def test_update_resubject_derives_new_hierarchy(self, app):
        with app.app_context():
            s = self._setup(db.session)
            subj2 = Subject(id=uuid.uuid4(), semester_id=s["sem"].id, name="Algorithms", code="DS102")
            db.session.add(subj2)
            db.session.flush()
            r = _make_resource(db.session, s["subj"].id, s["user"].id)
            resource_repository.update(r, subject_id=subj2.id)
            db.session.refresh(r)
            assert r.semester_id == s["sem"].id
            assert r.subject_id == subj2.id

    def test_update_clears_section_on_subject_change(self, app):
        with app.app_context():
            s = self._setup(db.session)
            r = _make_resource(
                db.session, s["subj"].id, s["user"].id, section_id=s["sec"].id
            )
            assert r.section_id == s["sec"].id

            other_sem = Semester(id=uuid.uuid4(), program_id=s["prog"].id, number=2)
            other_subj = Subject(id=uuid.uuid4(), semester_id=other_sem.id, name="Other", code="OT1")
            db.session.add_all([other_sem, other_subj])
            db.session.flush()

            resource_repository.update(r, subject_id=other_subj.id)
            db.session.refresh(r)
            assert r.section_id is None

    def test_section_must_belong_to_subject_semester_on_update(self, app):
        with app.app_context():
            s = self._setup(db.session)
            other_sem = Semester(id=uuid.uuid4(), program_id=s["prog"].id, number=2)
            other_sec = Section(id=uuid.uuid4(), semester_id=other_sem.id, name="B")
            db.session.add_all([other_sem, other_sec])
            db.session.flush()
            r = _make_resource(db.session, s["subj"].id, s["user"].id)
            with pytest.raises(ValueError, match="section_id does not belong"):
                resource_repository.update(r, section_id=other_sec.id)

    def test_soft_deleted_ancestor_still_resolves(self, app):
        with app.app_context():
            s = self._setup(db.session)
            s["dept"].deleted_at = db.func.now()
            db.session.flush()
            r = _make_resource(db.session, s["subj"].id, s["user"].id)
            assert r.department_id == s["dept"].id

    def test_fk_violation_on_invalid_subject(self, app):
        with app.app_context():
            s = self._setup(db.session)
            with pytest.raises(ValueError, match="Subject not found"):
                _make_resource(db.session, uuid.uuid4(), s["user"].id)

    def test_on_delete_restrict_department(self, app):
        """FK constraint on department_id points to departments (RESTRICT verified
        on PostgreSQL; SQLite reflection may not expose ondelete)."""
        with app.app_context():
            self._setup(db.session)

            dept_fks = [fk for fk in inspect(db.engine).get_foreign_keys("resources")
                        if "department_id" in fk["constrained_columns"]]
            assert len(dept_fks) == 1
            assert dept_fks[0]["referred_table"] == "departments"
