"""Academic hierarchy: Department → Program → Semester → Section → Subject.

Every level supports soft delete; unique constraints prevent sibling
duplication (e.g. two "FY" sections in the same semester).
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models.base import BaseModel, SoftDeleteMixin, UUIDType


class Department(BaseModel, SoftDeleteMixin):
    __tablename__ = "departments"

    name = sa.Column(sa.String(120), nullable=False, unique=True)
    code = sa.Column(sa.String(16), nullable=False, unique=True, index=True)
    description = sa.Column(sa.String(255), nullable=True)

    programs = db.relationship("Program", backref="department", lazy="selectin", viewonly=True)


class Program(BaseModel, SoftDeleteMixin):
    __tablename__ = "programs"

    department_id = sa.Column(
        UUIDType,
        sa.ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = sa.Column(sa.String(160), nullable=False)
    # Unique per department: two programs may share a short code across departments.
    code = sa.Column(sa.String(24), nullable=False)
    description = sa.Column(sa.String(255), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("department_id", "code", name="uq_programs_dept_code"),
        sa.Index("ix_programs_dept_name", "department_id", "name"),
    )


class Semester(BaseModel, SoftDeleteMixin):
    __tablename__ = "semesters"

    program_id = sa.Column(
        UUIDType,
        sa.ForeignKey("programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    number = sa.Column(sa.SmallInteger, nullable=False)

    __table_args__ = (sa.UniqueConstraint("program_id", "number", name="uq_semesters_program_num"),)


class Section(BaseModel, SoftDeleteMixin):
    __tablename__ = "sections"

    semester_id = sa.Column(
        UUIDType,
        sa.ForeignKey("semesters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = sa.Column(sa.String(24), nullable=False)
    capacity = sa.Column(sa.Integer, nullable=True)

    __table_args__ = (sa.UniqueConstraint("semester_id", "name", name="uq_sections_semester_name"),)


class Subject(BaseModel, SoftDeleteMixin):
    __tablename__ = "subjects"

    # Subject belongs to a semester; the program/department chain is derived.
    semester_id = sa.Column(
        UUIDType,
        sa.ForeignKey("semesters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = sa.Column(sa.String(160), nullable=False)
    code = sa.Column(sa.String(24), nullable=False)
    credits = sa.Column(sa.SmallInteger, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("semester_id", "code", name="uq_subjects_semester_code"),
        sa.Index("ix_subjects_semester_name", "semester_id", "name"),
    )
