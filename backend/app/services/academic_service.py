"""
Academic Structure domain service. Implements the service logic specified
in API_SPEC_ACADEMIC.md, including the Section <-> Chat Group coupling
resolved as "automatic, same transaction" per OPEN_DECISIONS.md.
"""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.academic import SectionRoleContext
from app.repositories.academic_repository import AcademicRepository
from app.repositories.auth_repository import AuthRepository
from app.repositories.chat_repository import ChatRepository
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError


class AcademicService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AcademicRepository(db)
        self.chat_repo = ChatRepository(db)
        self.auth_repo = AuthRepository(db)

    # ---------- Departments ----------

    def list_departments(self):
        return self.repo.list_departments()

    def create_department(self, name: str, code: str):
        if self.repo.get_department_by_code(code) is not None:
            raise ConflictError("Department code already in use.", code="DEPARTMENT_CODE_TAKEN")
        dept = self.repo.create_department(name, code)
        self.db.commit()
        return dept

    def update_department(self, department_id: uuid.UUID, name: str | None, code: str | None):
        dept = self.repo.get_department_by_id(department_id)
        if dept is None:
            raise NotFoundError("Department not found.", code="DEPARTMENT_NOT_FOUND")
        dept = self.repo.update_department(dept, name, code)
        self.db.commit()
        return dept

    def delete_department(self, department_id: uuid.UUID):
        dept = self.repo.get_department_by_id(department_id)
        if dept is None:
            raise NotFoundError("Department not found.", code="DEPARTMENT_NOT_FOUND")
        if self.repo.department_in_use(department_id):
            raise ConflictError("Department has active programs.", code="DEPARTMENT_IN_USE")
        self.repo.soft_delete_department(dept)
        self.db.commit()

    # ---------- Programs ----------

    def list_programs(self, department_id: uuid.UUID | None = None):
        return self.repo.list_programs(department_id)

    def create_program(self, department_id: uuid.UUID, name: str, code: str, duration_years: int):
        if self.repo.get_department_by_id(department_id) is None:
            raise NotFoundError("Department not found.", code="DEPARTMENT_NOT_FOUND")
        program = self.repo.create_program(department_id, name, code, duration_years)
        self.db.commit()
        return program

    def delete_program(self, program_id: uuid.UUID):
        program = self.repo.get_program_by_id(program_id)
        if program is None:
            raise NotFoundError("Program not found.", code="PROGRAM_NOT_FOUND")
        if self.repo.program_in_use(program_id):
            raise ConflictError("Program has active semesters or subjects.", code="PROGRAM_IN_USE")
        self.repo.soft_delete_program(program)
        self.db.commit()

    # ---------- Semesters ----------

    def list_semesters(self, program_id: uuid.UUID):
        return self.repo.list_semesters(program_id)

    def create_semester(
        self, program_id: uuid.UUID, number: int, name: str | None,
        start_date: date | None, end_date: date | None,
    ):
        if self.repo.get_program_by_id(program_id) is None:
            raise NotFoundError("Program not found.", code="PROGRAM_NOT_FOUND")
        if self.repo.get_semester_by_program_and_number(program_id, number) is not None:
            raise ConflictError("Semester number already exists for this program.", code="DUPLICATE_SEMESTER_NUMBER")
        semester = self.repo.create_semester(program_id, number, name, start_date, end_date)
        self.db.commit()
        return semester

    # ---------- Sections (coupled to Chat Group creation) ----------

    def list_sections(self, semester_id: uuid.UUID):
        return self.repo.list_sections(semester_id)

    def create_section(self, semester_id: uuid.UUID, name: str, created_by: uuid.UUID):
        """
        Per OPEN_DECISIONS.md: section creation auto-creates its chat Group +
        Conversation in the same transaction. If this coupling is ever made
        optional, this is the single place to change.
        """
        semester = self.repo.get_semester_by_id(semester_id)
        if semester is None:
            raise NotFoundError("Semester not found.", code="SEMESTER_NOT_FOUND")

        section = self.repo.create_section(semester_id, name)
        self.chat_repo.create_section_group_with_conversation(
            section_id=section.id, name=name, created_by=created_by
        )
        self.db.commit()
        return section

    def delete_section(self, section_id: uuid.UUID):
        section = self.repo.get_section_by_id(section_id)
        if section is None:
            raise NotFoundError("Section not found.", code="SECTION_NOT_FOUND")
        if self.repo.section_has_active_members(section_id):
            raise ConflictError("Section has active members.", code="SECTION_IN_USE")
        self.repo.soft_delete_section(section)
        self.db.commit()

    # ---------- Subjects ----------

    def list_subjects(self, program_id: uuid.UUID, semester_number: int | None = None):
        return self.repo.list_subjects(program_id, semester_number)

    def create_subject(self, program_id: uuid.UUID, semester_number: int, name: str, code: str):
        if self.repo.get_program_by_id(program_id) is None:
            raise NotFoundError("Program not found.", code="PROGRAM_NOT_FOUND")
        if self.repo.get_subject_by_program_semester_code(program_id, semester_number, code) is not None:
            raise ConflictError("Subject code already exists for this program/semester.", code="DUPLICATE_SUBJECT_CODE")
        subject = self.repo.create_subject(program_id, semester_number, name, code)
        self.db.commit()
        return subject

    # ---------- Enrollment (coupled to Chat group_members / conversation_participants) ----------

    def list_section_members(self, section_id: uuid.UUID) -> dict:
        if self.repo.get_section_by_id(section_id) is None:
            raise NotFoundError("Section not found.", code="SECTION_NOT_FOUND")
        rows = self.repo.list_members(section_id)
        enrolled = [(m, name) for m, name in rows if m.role_context == SectionRoleContext.ENROLLED]
        teaching = [(m, name) for m, name in rows if m.role_context == SectionRoleContext.TEACHING]
        return {"enrolled": enrolled, "teaching": teaching}

    def add_section_member(self, section_id: uuid.UUID, user_id: uuid.UUID, role_context: SectionRoleContext):
        section = self.repo.get_section_by_id(section_id)
        if section is None:
            raise NotFoundError("Section not found.", code="SECTION_NOT_FOUND")
        if self.auth_repo.get_user_by_id(user_id) is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        if self.repo.get_membership(section_id, user_id) is not None:
            raise ConflictError("User is already a member of this section.", code="ALREADY_MEMBER")

        membership = self.repo.add_member(section_id, user_id, role_context)

        # Mirror into the section's chat group, per the documented coupling.
        group = self.chat_repo.get_group_by_section_id(section_id)
        if group is not None:
            self.chat_repo.add_group_member(group.id, user_id)
            conversation = self.chat_repo.get_conversation_by_group_id(group.id)
            if conversation is not None:
                self.chat_repo.add_conversation_participant(conversation.id, user_id)

        self.db.commit()
        return membership

    def remove_section_member(self, section_id: uuid.UUID, user_id: uuid.UUID):
        membership = self.repo.get_membership(section_id, user_id)
        if membership is None:
            raise NotFoundError("Membership not found.", code="MEMBERSHIP_NOT_FOUND")

        self.repo.remove_member(membership)

        group = self.chat_repo.get_group_by_section_id(section_id)
        if group is not None:
            self.chat_repo.remove_group_member(group.id, user_id)
            conversation = self.chat_repo.get_conversation_by_group_id(group.id)
            if conversation is not None:
                self.chat_repo.remove_conversation_participant(conversation.id, user_id)

        self.db.commit()
