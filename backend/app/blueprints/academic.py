"""
Academic blueprint. Read endpoints require only auth (any authenticated
user); write endpoints require the `academic:manage` permission, per
API_SPEC_ACADEMIC.md's scope note.
"""
import uuid

from flask import Blueprint, g, request

from app.middleware.auth_middleware import require_auth, require_permission
from app.schemas.academic import (
    DepartmentCreateRequest,
    DepartmentOut,
    DepartmentUpdateRequest,
    ProgramCreateRequest,
    ProgramOut,
    SectionCreateRequest,
    SectionMemberAddRequest,
    SectionMembersOut,
    SectionOut,
    SemesterCreateRequest,
    SemesterOut,
    SubjectCreateRequest,
    SubjectOut,
)
from app.services.academic_service import AcademicService
from app.utils.responses import success

academic_bp = Blueprint("academic", __name__, url_prefix="/api/v1/academic")


def _get_service() -> AcademicService:
    from flask import current_app
    return AcademicService(db=current_app.extensions["db_session"]())


# ---------- Departments ----------

@academic_bp.get("/departments")
@require_auth
def list_departments():
    service = _get_service()
    items = [DepartmentOut.model_validate(d).model_dump(mode="json") for d in service.list_departments()]
    return success({"items": items})


@academic_bp.post("/departments")
@require_permission("academic:manage")
def create_department():
    payload = DepartmentCreateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    dept = service.create_department(payload.name, payload.code)
    return success(DepartmentOut.model_validate(dept).model_dump(mode="json"), status=201)


@academic_bp.patch("/departments/<uuid:department_id>")
@require_permission("academic:manage")
def update_department(department_id: uuid.UUID):
    payload = DepartmentUpdateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    dept = service.update_department(department_id, payload.name, payload.code)
    return success(DepartmentOut.model_validate(dept).model_dump(mode="json"))


@academic_bp.delete("/departments/<uuid:department_id>")
@require_permission("academic:manage")
def delete_department(department_id: uuid.UUID):
    service = _get_service()
    service.delete_department(department_id)
    return success({}, message="Department deleted.")


# ---------- Programs ----------

@academic_bp.get("/programs")
@require_auth
def list_programs():
    department_id = request.args.get("department_id")
    service = _get_service()
    items = [
        ProgramOut.model_validate(p).model_dump(mode="json")
        for p in service.list_programs(uuid.UUID(department_id) if department_id else None)
    ]
    return success({"items": items})


@academic_bp.post("/programs")
@require_permission("academic:manage")
def create_program():
    payload = ProgramCreateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    program = service.create_program(payload.department_id, payload.name, payload.code, payload.duration_years)
    return success(ProgramOut.model_validate(program).model_dump(mode="json"), status=201)


@academic_bp.delete("/programs/<uuid:program_id>")
@require_permission("academic:manage")
def delete_program(program_id: uuid.UUID):
    service = _get_service()
    service.delete_program(program_id)
    return success({}, message="Program deleted.")


# ---------- Semesters ----------

@academic_bp.get("/semesters")
@require_auth
def list_semesters():
    program_id = uuid.UUID(request.args["program_id"])
    service = _get_service()
    items = [SemesterOut.model_validate(s).model_dump(mode="json") for s in service.list_semesters(program_id)]
    return success({"items": items})


@academic_bp.post("/semesters")
@require_permission("academic:manage")
def create_semester():
    payload = SemesterCreateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    semester = service.create_semester(
        payload.program_id, payload.number, payload.name, payload.start_date, payload.end_date
    )
    return success(SemesterOut.model_validate(semester).model_dump(mode="json"), status=201)


# ---------- Sections ----------

@academic_bp.get("/semesters/<uuid:semester_id>/sections")
@require_auth
def list_sections(semester_id: uuid.UUID):
    service = _get_service()
    items = [SectionOut.model_validate(s).model_dump(mode="json") for s in service.list_sections(semester_id)]
    return success({"items": items})


@academic_bp.post("/semesters/<uuid:semester_id>/sections")
@require_permission("academic:manage")
def create_section(semester_id: uuid.UUID):
    payload = SectionCreateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    section = service.create_section(semester_id, payload.name, created_by=g.user_id)
    return success(SectionOut.model_validate(section).model_dump(mode="json"), status=201)


@academic_bp.delete("/sections/<uuid:section_id>")
@require_permission("academic:manage")
def delete_section(section_id: uuid.UUID):
    service = _get_service()
    service.delete_section(section_id)
    return success({}, message="Section deleted.")


# ---------- Subjects ----------

@academic_bp.get("/subjects")
@require_auth
def list_subjects():
    program_id = uuid.UUID(request.args["program_id"])
    semester_number = request.args.get("semester_number")
    service = _get_service()
    items = [
        SubjectOut.model_validate(s).model_dump(mode="json")
        for s in service.list_subjects(program_id, int(semester_number) if semester_number else None)
    ]
    return success({"items": items})


@academic_bp.post("/subjects")
@require_permission("academic:manage")
def create_subject():
    payload = SubjectCreateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    subject = service.create_subject(payload.program_id, payload.semester_number, payload.name, payload.code)
    return success(SubjectOut.model_validate(subject).model_dump(mode="json"), status=201)


# ---------- Enrollment ----------

@academic_bp.get("/sections/<uuid:section_id>/members")
@require_auth
def list_section_members(section_id: uuid.UUID):
    service = _get_service()
    result = service.list_section_members(section_id)
    out = SectionMembersOut(
        enrolled=[{"user_id": m.user_id, "full_name": name, "joined_at": m.joined_at} for m, name in result["enrolled"]],
        teaching=[{"user_id": m.user_id, "full_name": name, "joined_at": m.joined_at} for m, name in result["teaching"]],
    )
    return success(out.model_dump(mode="json"))


@academic_bp.post("/sections/<uuid:section_id>/members")
@require_permission("academic:manage")
def add_section_member(section_id: uuid.UUID):
    payload = SectionMemberAddRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    service.add_section_member(section_id, payload.user_id, payload.role_context)
    return success({}, message="Member added.", status=201)


@academic_bp.delete("/sections/<uuid:section_id>/members/<uuid:user_id>")
@require_permission("academic:manage")
def remove_section_member(section_id: uuid.UUID, user_id: uuid.UUID):
    service = _get_service()
    service.remove_section_member(section_id, user_id)
    return success({}, message="Member removed.")
