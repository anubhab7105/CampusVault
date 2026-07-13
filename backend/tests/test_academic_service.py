"""
Integration tests for Academic domain — real Postgres. Includes tests that
actually prove the Section <-> Chat Group coupling works end-to-end, not
just that it's documented.
"""
from datetime import date

import pytest

from app.models.academic import SectionRoleContext
from app.models.auth import UserType
from app.models.chat import GroupType
from app.repositories.academic_repository import AcademicRepository
from app.repositories.auth_repository import AuthRepository
from app.repositories.chat_repository import ChatRepository
from app.services.academic_service import AcademicService
from app.utils.exceptions import ConflictError, NotFoundError


def _make_program(db):
    """Helper: builds a department + program for tests that need a program_id."""
    repo = AcademicRepository(db)
    dept = repo.create_department("Computer Science", "CS")
    program = repo.create_program(dept.id, "B.Tech CSE", "BTCSE", 4)
    db.flush()
    return dept, program


class TestDepartmentRepository:
    def test_create_and_list(self, db):
        repo = AcademicRepository(db)
        repo.create_department("Electronics", "ECE")
        db.flush()
        names = [d.name for d in repo.list_departments()]
        assert "Electronics" in names

    def test_soft_deleted_not_listed(self, db):
        repo = AcademicRepository(db)
        dept = repo.create_department("Mechanical", "ME")
        db.flush()
        repo.soft_delete_department(dept)
        db.flush()
        assert dept.id not in [d.id for d in repo.list_departments()]

    def test_department_in_use_detection(self, db):
        repo = AcademicRepository(db)
        dept, program = _make_program(db)
        assert repo.department_in_use(dept.id) is True

        empty_dept = repo.create_department("Unused Dept", "UD")
        db.flush()
        assert repo.department_in_use(empty_dept.id) is False


class TestAcademicServiceDepartments:
    def test_create_department_duplicate_code_rejected(self, db):
        service = AcademicService(db)
        service.create_department("Physics", "PHY")
        with pytest.raises(ConflictError) as exc_info:
            service.create_department("Physics 2", "PHY")
        assert exc_info.value.code == "DEPARTMENT_CODE_TAKEN"

    def test_delete_department_in_use_blocked(self, db):
        service = AcademicService(db)
        dept = service.create_department("Chemistry", "CHEM")
        service.create_program(dept.id, "B.Sc Chem", "BSCCHEM", 3)

        with pytest.raises(ConflictError) as exc_info:
            service.delete_department(dept.id)
        assert exc_info.value.code == "DEPARTMENT_IN_USE"

    def test_update_department_name_and_code(self, db):
        service = AcademicService(db)
        dept = service.create_department("Old Name", "OLD1")
        updated = service.update_department(dept.id, name="New Name", code=None)
        assert updated.name == "New Name"
        assert updated.code == "OLD1"

    def test_update_unknown_department_raises(self, db):
        import uuid
        service = AcademicService(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.update_department(uuid.uuid4(), "X", None)
        assert exc_info.value.code == "DEPARTMENT_NOT_FOUND"

    def test_delete_unknown_department_raises(self, db):
        import uuid
        service = AcademicService(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.delete_department(uuid.uuid4())
        assert exc_info.value.code == "DEPARTMENT_NOT_FOUND"

    def test_create_program_unknown_department_raises(self, db):
        import uuid
        service = AcademicService(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.create_program(uuid.uuid4(), "X", "X1", 4)
        assert exc_info.value.code == "DEPARTMENT_NOT_FOUND"

    def test_delete_program_in_use_blocked(self, db):
        service = AcademicService(db)
        _, program = _make_program(db)
        service.create_semester(program.id, 1, None, None, None)

        with pytest.raises(ConflictError) as exc_info:
            service.delete_program(program.id)
        assert exc_info.value.code == "PROGRAM_IN_USE"

    def test_delete_unused_program_succeeds(self, db):
        service = AcademicService(db)
        dept = service.create_department("Standalone Dept", "SD1")
        program = service.create_program(dept.id, "Unused Program", "UP1", 3)
        service.delete_program(program.id)  # should not raise

    def test_delete_unknown_program_raises(self, db):
        import uuid
        service = AcademicService(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.delete_program(uuid.uuid4())
        assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    def test_list_departments_and_programs(self, db):
        service = AcademicService(db)
        dept, program = _make_program(db)

        depts = service.list_departments()
        assert dept.id in [d.id for d in depts]

        programs = service.list_programs(dept.id)
        assert program.id in [p.id for p in programs]

        all_programs = service.list_programs(None)
        assert program.id in [p.id for p in all_programs]


class TestAcademicServiceHierarchy:
    def test_create_semester_duplicate_number_rejected(self, db):
        service = AcademicService(db)
        _, program = _make_program(db)
        service.create_semester(program.id, 1, "Sem 1", None, None)

        with pytest.raises(ConflictError) as exc_info:
            service.create_semester(program.id, 1, "Sem 1 dup", None, None)
        assert exc_info.value.code == "DUPLICATE_SEMESTER_NUMBER"

    def test_create_subject_duplicate_code_rejected(self, db):
        service = AcademicService(db)
        _, program = _make_program(db)
        service.create_subject(program.id, 3, "Data Structures", "CS301")

        with pytest.raises(ConflictError) as exc_info:
            service.create_subject(program.id, 3, "Data Structures Dup", "CS301")
        assert exc_info.value.code == "DUPLICATE_SUBJECT_CODE"

    def test_create_subject_unknown_program_rejected(self, db):
        import uuid
        service = AcademicService(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.create_subject(uuid.uuid4(), 1, "X", "X101")
        assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    def test_list_semesters_and_subjects(self, db):
        service = AcademicService(db)
        _, program = _make_program(db)
        semester = service.create_semester(program.id, 2, "Sem 2", None, None)
        subject = service.create_subject(program.id, 2, "Algorithms", "CS201")

        semesters = service.list_semesters(program.id)
        assert semester.id in [s.id for s in semesters]

        subjects_all = service.list_subjects(program.id)
        assert subject.id in [s.id for s in subjects_all]

        subjects_filtered = service.list_subjects(program.id, semester_number=2)
        assert subject.id in [s.id for s in subjects_filtered]

        subjects_wrong_sem = service.list_subjects(program.id, semester_number=5)
        assert subject.id not in [s.id for s in subjects_wrong_sem]


class TestSectionChatCoupling:
    """The core cross-domain behavior: creating a Section must also create
    its chat Group + Conversation, in the same transaction."""

    def test_create_section_creates_group_and_conversation(self, db):
        service = AcademicService(db)
        auth_repo = AuthRepository(db)
        chat_repo = ChatRepository(db)

        admin = auth_repo.create_user("admin1@college.edu", "Admin", UserType.ADMIN)
        db.commit()
        _, program = _make_program(db)
        semester = service.create_semester(program.id, 1, None, None, None)

        section = service.create_section(semester.id, "Section A", created_by=admin.id)

        group = chat_repo.get_group_by_section_id(section.id)
        assert group is not None
        assert group.type == GroupType.SECTION
        assert group.name == "Section A"

        conversation = chat_repo.get_conversation_by_group_id(group.id)
        assert conversation is not None

    def test_create_section_unknown_semester_rejected(self, db):
        import uuid
        service = AcademicService(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.create_section(uuid.uuid4(), "X", created_by=uuid.uuid4())
        assert exc_info.value.code == "SEMESTER_NOT_FOUND"

    def test_list_sections(self, db):
        service = AcademicService(db)
        auth_repo = AuthRepository(db)
        admin = auth_repo.create_user("admin_list@college.edu", "Admin", UserType.ADMIN)
        db.commit()
        _, program = _make_program(db)
        semester = service.create_semester(program.id, 1, None, None, None)
        section = service.create_section(semester.id, "Section List Test", created_by=admin.id)

        sections = service.list_sections(semester.id)
        assert section.id in [s.id for s in sections]


class TestSectionMembershipChatSync:
    """Enrolling/removing a section member must mirror into group_members
    and conversation_participants."""

    def test_add_member_mirrors_into_group_and_conversation(self, db):
        from sqlalchemy import select

        from app.models.chat import ConversationParticipant, GroupMember

        service = AcademicService(db)
        auth_repo = AuthRepository(db)
        chat_repo = ChatRepository(db)

        admin = auth_repo.create_user("admin2@college.edu", "Admin", UserType.ADMIN)
        student = auth_repo.create_user("student1@college.edu", "Student", UserType.STUDENT)
        db.commit()
        _, program = _make_program(db)
        semester = service.create_semester(program.id, 1, None, None, None)
        section = service.create_section(semester.id, "Section B", created_by=admin.id)

        service.add_section_member(section.id, student.id, SectionRoleContext.ENROLLED)

        group = chat_repo.get_group_by_section_id(section.id)
        group_member_ids = set(db.scalars(
            select(GroupMember.user_id).where(GroupMember.group_id == group.id)
        ))
        assert student.id in group_member_ids

        conversation = chat_repo.get_conversation_by_group_id(group.id)
        participant_ids = set(db.scalars(
            select(ConversationParticipant.user_id).where(ConversationParticipant.conversation_id == conversation.id)
        ))
        assert student.id in participant_ids

    def test_add_member_duplicate_rejected(self, db):
        service = AcademicService(db)
        auth_repo = AuthRepository(db)

        admin = auth_repo.create_user("admin3@college.edu", "Admin", UserType.ADMIN)
        student = auth_repo.create_user("student2@college.edu", "Student", UserType.STUDENT)
        db.commit()
        _, program = _make_program(db)
        semester = service.create_semester(program.id, 1, None, None, None)
        section = service.create_section(semester.id, "Section C", created_by=admin.id)

        service.add_section_member(section.id, student.id, SectionRoleContext.ENROLLED)
        with pytest.raises(ConflictError) as exc_info:
            service.add_section_member(section.id, student.id, SectionRoleContext.ENROLLED)
        assert exc_info.value.code == "ALREADY_MEMBER"

    def test_list_section_members_returns_full_name_without_n_plus_1(self, db):
        """Confirms the join-based fix — full_name is populated, not blank."""
        service = AcademicService(db)
        auth_repo = AuthRepository(db)

        admin = auth_repo.create_user("admin4@college.edu", "Admin", UserType.ADMIN)
        student = auth_repo.create_user("student3@college.edu", "Named Student", UserType.STUDENT)
        db.commit()
        _, program = _make_program(db)
        semester = service.create_semester(program.id, 1, None, None, None)
        section = service.create_section(semester.id, "Section D", created_by=admin.id)
        service.add_section_member(section.id, student.id, SectionRoleContext.ENROLLED)

        result = service.list_section_members(section.id)
        assert len(result["enrolled"]) == 1
        membership, full_name = result["enrolled"][0]
        assert full_name == "Named Student"

    def test_delete_section_with_members_blocked(self, db):
        service = AcademicService(db)
        auth_repo = AuthRepository(db)

        admin = auth_repo.create_user("admin5@college.edu", "Admin", UserType.ADMIN)
        student = auth_repo.create_user("student4@college.edu", "Student", UserType.STUDENT)
        db.commit()
        _, program = _make_program(db)
        semester = service.create_semester(program.id, 1, None, None, None)
        section = service.create_section(semester.id, "Section E", created_by=admin.id)
        service.add_section_member(section.id, student.id, SectionRoleContext.ENROLLED)

        with pytest.raises(ConflictError) as exc_info:
            service.delete_section(section.id)
        assert exc_info.value.code == "SECTION_IN_USE"

    def test_remove_member_mirrors_removal_from_group(self, db):
        service = AcademicService(db)
        auth_repo = AuthRepository(db)
        chat_repo = ChatRepository(db)

        admin = auth_repo.create_user("admin6@college.edu", "Admin", UserType.ADMIN)
        student = auth_repo.create_user("student5@college.edu", "Student", UserType.STUDENT)
        db.commit()
        _, program = _make_program(db)
        semester = service.create_semester(program.id, 1, None, None, None)
        section = service.create_section(semester.id, "Section F", created_by=admin.id)
        service.add_section_member(section.id, student.id, SectionRoleContext.ENROLLED)

        service.remove_section_member(section.id, student.id)

        group = chat_repo.get_group_by_section_id(section.id)
        from app.models.chat import GroupMember
        from sqlalchemy import select
        remaining = db.scalar(
            select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == student.id)
        )
        assert remaining is None
