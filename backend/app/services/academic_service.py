"""Academic hierarchy service — creates and lookups with referential rules."""

from __future__ import annotations

import uuid

from app.constants import MAX_SEMESTER_COUNT
from app.errors.exceptions import ConflictError, NotFoundError, ValidationError
from app.extensions import db
from app.models import (
    Department,
    Program,
    Section,
    Semester,
    Subject,
)
from app.repositories import (
    DepartmentRepository,
    ProgramRepository,
    SectionRepository,
    SemesterRepository,
    SubjectRepository,
)
from app.services.base_service import BaseService


class AcademicService(BaseService):
    def __init__(self) -> None:
        self.departments = DepartmentRepository()
        self.programs = ProgramRepository()
        self.semesters = SemesterRepository()
        self.sections = SectionRepository()
        self.subjects = SubjectRepository()

    # --- Department ---------------------------------------------------------- #

    def create_department(self, *, name: str, code: str, description: str = "") -> Department:
        if self.departments.count() and self._exists_by_code(Department, code):
            raise ConflictError("A department with this code already exists.")
        row = self.departments.create(name=name, code=code, description=description)
        db.session.commit()
        return row

    def list_departments(self, page: int, page_size: int):
        return self.departments.list_active(page, page_size)

    # --- Program ---------------------------------------------------------------- #

    def create_program(
        self, *, department_id: uuid.UUID, name: str, code: str, description: str = ""
    ) -> Program:
        dept = self.departments.get_active_by_id(department_id)
        if dept is None:
            raise NotFoundError("Department not found.")
        program = self.programs.create(
            department_id=department_id, name=name, code=code, description=description
        )
        db.session.flush()  # surface uq_programs_dept_code as a clean 409
        db.session.commit()
        return program

    # --- Semester ------------------------------------------------------------------ #

    def create_semester(self, *, program_id: uuid.UUID, number: int) -> Semester:
        if not 1 <= number <= MAX_SEMESTER_COUNT:
            raise ValidationError(f"Semester number must be 1..{MAX_SEMESTER_COUNT}.")
        program = self.programs.get_active_by_id(program_id)
        if program is None:
            raise NotFoundError("Program not found.")
        semester = self.semesters.create(program_id=program_id, number=number)
        db.session.flush()
        db.session.commit()
        return semester

    # --- Section ------------------------------------------------------------------------ #

    def create_section(self, *, semester_id: uuid.UUID, name: str, capacity: int | None = None) -> Section:
        semester = self.semesters.get_active_by_id(semester_id)
        if semester is None:
            raise NotFoundError("Semester not found.")
        section = self.sections.create(semester_id=semester_id, name=name, capacity=capacity)
        db.session.flush()
        db.session.commit()
        return section

    # --- Subject ---------------------------------------------------------------------------- #

    def create_subject(
        self, *, semester_id: uuid.UUID, name: str, code: str, credits: int | None = None
    ) -> Subject:
        semester = self.semesters.get_active_by_id(semester_id)
        if semester is None:
            raise NotFoundError("Semester not found.")
        subject = self.subjects.create(semester_id=semester_id, name=name, code=code, credits=credits)
        db.session.flush()
        db.session.commit()
        return subject

    # --- internals ------------------------------------------------------------------------------- #

    @staticmethod
    def _exists_by_code(model, code: str) -> bool:
        from app.extensions import db

        stmt = db.select(model.id).where(model.code == code).limit(1)
        return db.session.scalar(stmt) is not None


academic_service = AcademicService()
