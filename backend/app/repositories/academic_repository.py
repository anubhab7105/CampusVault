"""
Academic Structure domain repository. Per 04_BACKEND_GUIDE.md: "Database
access goes through repositories." Covers departments, programs, semesters,
sections, subjects, and user_sections per API_SPEC_ACADEMIC.md.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Department, Program, Section, SectionRoleContext, Semester, Subject, UserSection


class AcademicRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Departments ----------

    def list_departments(self) -> list[Department]:
        return list(self.db.scalars(
            select(Department).where(Department.deleted_at.is_(None)).order_by(Department.name)
        ))

    def get_department_by_id(self, department_id: uuid.UUID) -> Department | None:
        return self.db.scalar(
            select(Department).where(Department.id == department_id, Department.deleted_at.is_(None))
        )

    def get_department_by_code(self, code: str) -> Department | None:
        return self.db.scalar(
            select(Department).where(Department.code == code, Department.deleted_at.is_(None))
        )

    def create_department(self, name: str, code: str) -> Department:
        dept = Department(name=name, code=code)
        self.db.add(dept)
        self.db.flush()
        return dept

    def update_department(self, dept: Department, name: str | None, code: str | None) -> Department:
        if name is not None:
            dept.name = name
        if code is not None:
            dept.code = code
        self.db.flush()
        return dept

    def soft_delete_department(self, dept: Department) -> None:
        dept.deleted_at = datetime.now(timezone.utc)
        self.db.flush()

    def department_in_use(self, department_id: uuid.UUID) -> bool:
        return self.db.scalar(
            select(Program).where(Program.department_id == department_id, Program.deleted_at.is_(None))
        ) is not None

    # ---------- Programs ----------

    def list_programs(self, department_id: uuid.UUID | None = None) -> list[Program]:
        stmt = select(Program).where(Program.deleted_at.is_(None))
        if department_id is not None:
            stmt = stmt.where(Program.department_id == department_id)
        return list(self.db.scalars(stmt.order_by(Program.name)))

    def get_program_by_id(self, program_id: uuid.UUID) -> Program | None:
        return self.db.scalar(select(Program).where(Program.id == program_id, Program.deleted_at.is_(None)))

    def create_program(self, department_id: uuid.UUID, name: str, code: str, duration_years: int) -> Program:
        program = Program(department_id=department_id, name=name, code=code, duration_years=duration_years)
        self.db.add(program)
        self.db.flush()
        return program

    def program_in_use(self, program_id: uuid.UUID) -> bool:
        has_semesters = self.db.scalar(
            select(Semester).where(Semester.program_id == program_id)
        ) is not None
        has_subjects = self.db.scalar(
            select(Subject).where(Subject.program_id == program_id, Subject.deleted_at.is_(None))
        ) is not None
        return has_semesters or has_subjects

    def soft_delete_program(self, program: Program) -> None:
        program.deleted_at = datetime.now(timezone.utc)
        self.db.flush()

    # ---------- Semesters ----------

    def list_semesters(self, program_id: uuid.UUID) -> list[Semester]:
        return list(self.db.scalars(
            select(Semester).where(Semester.program_id == program_id).order_by(Semester.number)
        ))

    def get_semester_by_id(self, semester_id: uuid.UUID) -> Semester | None:
        return self.db.scalar(select(Semester).where(Semester.id == semester_id))

    def get_semester_by_program_and_number(self, program_id: uuid.UUID, number: int) -> Semester | None:
        return self.db.scalar(
            select(Semester).where(Semester.program_id == program_id, Semester.number == number)
        )

    def create_semester(
        self, program_id: uuid.UUID, number: int, name: str | None,
        start_date: date | None, end_date: date | None,
    ) -> Semester:
        semester = Semester(
            program_id=program_id, number=number, name=name, start_date=start_date, end_date=end_date
        )
        self.db.add(semester)
        self.db.flush()
        return semester

    # ---------- Sections ----------

    def list_sections(self, semester_id: uuid.UUID) -> list[Section]:
        return list(self.db.scalars(
            select(Section).where(Section.semester_id == semester_id, Section.deleted_at.is_(None)).order_by(Section.name)
        ))

    def get_section_by_id(self, section_id: uuid.UUID) -> Section | None:
        return self.db.scalar(select(Section).where(Section.id == section_id, Section.deleted_at.is_(None)))

    def create_section(self, semester_id: uuid.UUID, name: str) -> Section:
        section = Section(semester_id=semester_id, name=name)
        self.db.add(section)
        self.db.flush()
        return section

    def soft_delete_section(self, section: Section) -> None:
        section.deleted_at = datetime.now(timezone.utc)
        self.db.flush()

    def section_has_active_members(self, section_id: uuid.UUID) -> bool:
        return self.db.scalar(
            select(UserSection).where(UserSection.section_id == section_id)
        ) is not None

    # ---------- Subjects ----------

    def list_subjects(self, program_id: uuid.UUID, semester_number: int | None = None) -> list[Subject]:
        stmt = select(Subject).where(Subject.program_id == program_id, Subject.deleted_at.is_(None))
        if semester_number is not None:
            stmt = stmt.where(Subject.semester_number == semester_number)
        return list(self.db.scalars(stmt.order_by(Subject.name)))

    def get_subject_by_id(self, subject_id: uuid.UUID) -> Subject | None:
        return self.db.scalar(select(Subject).where(Subject.id == subject_id, Subject.deleted_at.is_(None)))

    def get_subject_by_program_semester_code(
        self, program_id: uuid.UUID, semester_number: int, code: str
    ) -> Subject | None:
        return self.db.scalar(
            select(Subject).where(
                Subject.program_id == program_id,
                Subject.semester_number == semester_number,
                Subject.code == code,
                Subject.deleted_at.is_(None),
            )
        )

    def create_subject(self, program_id: uuid.UUID, semester_number: int, name: str, code: str) -> Subject:
        subject = Subject(program_id=program_id, semester_number=semester_number, name=name, code=code)
        self.db.add(subject)
        self.db.flush()
        return subject

    # ---------- Enrollment (user_sections) ----------

    def get_membership(self, section_id: uuid.UUID, user_id: uuid.UUID) -> UserSection | None:
        return self.db.scalar(
            select(UserSection).where(UserSection.section_id == section_id, UserSection.user_id == user_id)
        )

    def list_members(self, section_id: uuid.UUID) -> list[tuple[UserSection, str]]:
        """Returns (membership, user_full_name) pairs in one joined query — avoids N+1."""
        from app.models.auth import User

        rows = self.db.execute(
            select(UserSection, User.full_name)
            .join(User, User.id == UserSection.user_id)
            .where(UserSection.section_id == section_id)
        )
        return list(rows)

    def add_member(self, section_id: uuid.UUID, user_id: uuid.UUID, role_context: SectionRoleContext) -> UserSection:
        member = UserSection(
            section_id=section_id, user_id=user_id, role_context=role_context,
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(member)
        self.db.flush()
        return member

    def remove_member(self, membership: UserSection) -> None:
        self.db.delete(membership)
        self.db.flush()
