"""Academic blueprint — the Department→Program→Semester→Section→Subject chain.

Creation endpoints are admin-gated (`admin:academic:manage`); read endpoints
require authentication and are open to every signed-in user.
"""

from __future__ import annotations

import uuid

from flask import Blueprint, request
from marshmallow import Schema, fields, validate

from app.middleware.rbac import permission_required
from app.services.academic_service import academic_service
from app.utils.pagination import PagingMeta, parse_pagination_args
from app.utils.responses import success_response
from app.utils.validation import get_json_body, load_schema

bp = Blueprint("academic", __name__, url_prefix="/api/v1/academic")


class DepartmentSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=3, max=120))
    code = fields.Str(required=True, validate=validate.Length(min=2, max=16))
    description = fields.Str(load_default="", validate=validate.Length(max=255))


class ProgramSchema(Schema):
    department_id = fields.UUID(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=3, max=160))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=24))
    description = fields.Str(load_default="", validate=validate.Length(max=255))


class SemesterSchema(Schema):
    program_id = fields.UUID(required=True)
    number = fields.Int(required=True, strict=True, validate=validate.Range(min=1, max=12))


class SectionSchema(Schema):
    semester_id = fields.UUID(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=24))
    capacity = fields.Int(load_default=None, allow_none=True, validate=validate.Range(min=1))


class SubjectSchema(Schema):
    semester_id = fields.UUID(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=160))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=24))
    credits = fields.Int(load_default=None, allow_none=True, validate=validate.Range(min=0, max=20))


def _page_args():
    return parse_pagination_args(request.args.get("page"), request.args.get("page_size"))


# --- Departments ------------------------------------------------------------ #


@bp.post("/departments")
@permission_required("admin:academic:manage")
def create_department():
    body = load_schema(DepartmentSchema(), get_json_body())
    dept = academic_service.create_department(
        name=body["name"], code=body["code"], description=body["description"]
    )
    return success_response(
        data={"id": str(dept.id)}, status_code=201, message="Department created."
    )


@bp.get("/departments")
def list_departments():
    page, page_size, _ = _page_args()
    rows, total = academic_service.list_departments(page, page_size)
    meta = PagingMeta(page, page_size, total)
    return success_response(
        data={"items": [{"id": str(d.id), "name": d.name, "code": d.code} for d in rows]},
        paging=meta.as_dict(),
        message="Departments listed.",
    )


# --- Programs ----------------------------------------------------------------- #


@bp.post("/programs")
@permission_required("admin:academic:manage")
def create_program():
    body = load_schema(ProgramSchema(), get_json_body())
    program = academic_service.create_program(
        department_id=body["department_id"],
        name=body["name"],
        code=body["code"],
        description=body["description"],
    )
    return success_response(data={"id": str(program.id)}, status_code=201, message="Program created.")


@bp.get("/programs/<uuid:department_id>")
def list_programs(department_id: uuid.UUID):
    page, page_size, _ = _page_args()
    rows, total = academic_service.programs.list_for_department(department_id, page, page_size)
    meta = PagingMeta(page, page_size, total)
    return success_response(
        data={"items": [{"id": str(p.id), "name": p.name, "code": p.code} for p in rows]},
        paging=meta.as_dict(),
        message="Programs listed.",
    )


# --- Semesters -------------------------------------------------------------------- #


@bp.post("/semesters")
@permission_required("admin:academic:manage")
def create_semester():
    body = load_schema(SemesterSchema(), get_json_body())
    semester = academic_service.create_semester(
        program_id=body["program_id"], number=body["number"]
    )
    return success_response(
        data={"id": str(semester.id)}, status_code=201, message="Semester created."
    )


@bp.get("/semesters/<uuid:program_id>")
def list_semesters(program_id: uuid.UUID):
    rows = academic_service.semesters.list_for_program(program_id, page=1, page_size=50)[0]
    return success_response(
        data={"items": [{"id": str(s.id), "number": s.number} for s in rows]},
        message="Semesters listed.",
    )


# --- Sections ------------------------------------------------------------------------- #


@bp.post("/sections")
@permission_required("admin:academic:manage")
def create_section():
    body = load_schema(SectionSchema(), get_json_body())
    section = academic_service.create_section(
        semester_id=body["semester_id"], name=body["name"], capacity=body["capacity"]
    )
    return success_response(data={"id": str(section.id)}, status_code=201, message="Section created.")


@bp.get("/sections/<uuid:semester_id>")
def list_sections(semester_id: uuid.UUID):
    rows = academic_service.sections.list_for_semester(semester_id, page=1, page_size=50)[0]
    return success_response(
        data={"items": [{"id": str(s.id), "name": s.name} for s in rows]},
        message="Sections listed.",
    )


# --- Subjects ---------------------------------------------------------------------------- #
@bp.post("/subjects")
@permission_required("admin:academic:manage")
def create_subject():
    body = load_schema(SubjectSchema(), get_json_body())
    subject = academic_service.create_subject(
        semester_id=body["semester_id"],
        name=body["name"],
        code=body["code"],
        credits=body["credits"],
    )
    return success_response(data={"id": str(subject.id)}, status_code=201, message="Subject created.")


@bp.get("/subjects/<uuid:semester_id>")
def list_subjects(semester_id: uuid.UUID):
    rows = academic_service.subjects.list_for_semester(semester_id, page=1, page_size=100)[0]
    return success_response(
        data={
            "items": [
                {"id": str(s.id), "name": s.name, "code": s.code, "credits": s.credits}
                for s in rows
            ]
        },
        message="Subjects listed.",
    )
