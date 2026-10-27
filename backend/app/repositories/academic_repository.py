"""Academic hierarchy persistence (Department→Program→Semester→Section→Subject)."""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models import Department, Program, Section, Semester, Subject
from app.repositories.base_repository import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    def list_active(self, page: int, page_size: int):
        stmt = sa.select(Department).where(Department.deleted_at.is_(None))
        stmt = stmt.order_by(Department.name).offset((page - 1) * page_size).limit(page_size)
        rows = db.session.scalars(stmt).all()
        total_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        total = int(db.session.scalar(total_stmt) or 0)
        return rows, total


class ProgramRepository(BaseRepository[Program]):
    model = Program

    def list_for_department(self, department_id, page: int, page_size: int):
        return self.paginate(
            page,
            page_size,
            Program.department_id == department_id,
            order_by=Program.code.asc(),
        )


class SemesterRepository(BaseRepository[Semester]):
    model = Semester

    def list_for_program(self, program_id, page: int, page_size: int):
        return self.paginate(
            page,
            page_size,
            Semester.program_id == program_id,
            order_by=Semester.number.asc(),
        )


class SectionRepository(BaseRepository[Section]):
    model = Section

    def list_for_semester(self, semester_id, page: int, page_size: int):
        return self.paginate(
            page,
            page_size,
            Section.semester_id == semester_id,
            order_by=Section.name.asc(),
        )


class SubjectRepository(BaseRepository[Subject]):
    model = Subject

    def list_for_semester(self, semester_id, page: int, page_size: int):
        return self.paginate(
            page,
            page_size,
            Subject.semester_id == semester_id,
            order_by=Subject.code.asc(),
        )
