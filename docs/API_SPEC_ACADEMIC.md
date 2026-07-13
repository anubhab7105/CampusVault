# CampusVault — API Design: Academic Structure Domain v1

Status: Draft for review
Stage: Feature Implementation Workflow → Step 4 (API Design), Academic domain
Depends on: DATABASE_SCHEMA.md, API_SPEC_RBAC.md (permission middleware contract), 08_API_GUIDE.md

## Scope & Access

Read endpoints: any authenticated user (students/teachers need to browse the structure to find
their section/subjects). Write endpoints: `require_permission("academic:manage")` (admin/staff only).

Base path: `/api/v1/academic`

## Hierarchy

`departments → programs → semesters → sections` (a section is a specific class within a semester's
run) and `programs → subjects` (subjects are scoped to program + semester number, not to a specific
section — see DATABASE_SCHEMA.md's open item on this). `user_sections` links people to sections.

All list endpoints below follow the same pagination/filtering/sorting pattern from 08_API_GUIDE.md;
omitted from each block for brevity after the first example.

---

## Departments

### `GET /api/v1/academic/departments`
**Response `200`**
```json
{
  "success": true, "message": "OK",
  "data": {
    "items": [ { "id": "uuid", "name": "Computer Science", "code": "CS" } ],
    "page": 1, "page_size": 20, "total": 8
  }
}
```

### `POST /api/v1/academic/departments`
**Request**: `{ "name": "Computer Science", "code": "CS" }`
**Errors**: `VALIDATION_ERROR` (400), `DEPARTMENT_CODE_TAKEN` (409).

### `PATCH /api/v1/academic/departments/{id}`
### `DELETE /api/v1/academic/departments/{id}`
Soft delete (sets `deleted_at`). Blocked if active `programs` reference it.
**Errors**: `DEPARTMENT_NOT_FOUND` (404), `DEPARTMENT_IN_USE` (409).

---

## Programs

### `GET /api/v1/academic/programs?department_id={id}`
Filter by department. Same envelope shape as departments list.

### `POST /api/v1/academic/programs`
**Request**: `{ "department_id": "uuid", "name": "B.Tech CSE", "code": "BTCSE", "duration_years": 4 }`

### `PATCH /api/v1/academic/programs/{id}`
### `DELETE /api/v1/academic/programs/{id}`
Soft delete; blocked if active `semesters` or `subjects` reference it.

---

## Semesters

### `GET /api/v1/academic/semesters?program_id={id}`

### `POST /api/v1/academic/semesters`
**Request**: `{ "program_id": "uuid", "number": 3, "name": "Semester 3", "start_date": "2026-08-01", "end_date": "2026-12-15" }`
**Errors**: `DUPLICATE_SEMESTER_NUMBER` (409) — unique per program per DATABASE_SCHEMA.md constraint.

### `PATCH /api/v1/academic/semesters/{id}`

Semesters have no delete endpoint in v1 — closing out a semester is a state/reporting concern, not
a deletion. Flagged as an open item below.

---

## Sections

### `GET /api/v1/academic/semesters/{semester_id}/sections`

### `POST /api/v1/academic/semesters/{semester_id}/sections`
**Request**: `{ "name": "A" }`
**Service logic**: on creation, if this is meant to auto-create the section's chat group
(per Chat domain's `Group.type=section`), that happens here as a side effect in the same
transaction — confirm this coupling at Backend Implementation time; documented as a dependency now.

### `PATCH /api/v1/academic/sections/{id}`
### `DELETE /api/v1/academic/sections/{id}`
Soft delete; blocked if active `user_sections` reference it (must offboard members first, or
cascade — decide at Backend step; leaning toward "block" to avoid silent data loss).

---

## Subjects

### `GET /api/v1/academic/subjects?program_id={id}&semester_number={n}`

### `POST /api/v1/academic/subjects`
**Request**: `{ "program_id": "uuid", "semester_number": 3, "name": "Data Structures", "code": "CS301" }`
**Errors**: `DUPLICATE_SUBJECT_CODE` (409) — unique per program+semester+code.

### `PATCH /api/v1/academic/subjects/{id}`
### `DELETE /api/v1/academic/subjects/{id}`
Soft delete; blocked if active `resources` reference it.

---

## Enrollment (`user_sections`)

### `GET /api/v1/academic/sections/{section_id}/members`
Lists everyone scoped to a section, split by role_context.

**Response `200`**
```json
{
  "success": true, "message": "OK",
  "data": {
    "enrolled": [ { "user_id": "uuid", "full_name": "...", "joined_at": "..." } ],
    "teaching": [ { "user_id": "uuid", "full_name": "...", "joined_at": "..." } ]
  }
}
```

### `POST /api/v1/academic/sections/{section_id}/members`
Enroll or assign a user to a section.

**Request**: `{ "user_id": "uuid", "role_context": "enrolled" }`
**Service logic**: insert `user_sections` row; if the section has a linked chat `Group`
(`type=section`), also insert a `group_members` row in the same transaction (this is the
"auto-membership" behavior referenced in DATABASE_SCHEMA.md's `user_sections` rationale).
Write `audit_logs`: `action="section.member_added"`.
**Errors**: `USER_NOT_FOUND` (404), `SECTION_NOT_FOUND` (404), `ALREADY_MEMBER` (409).

### `DELETE /api/v1/academic/sections/{section_id}/members/{user_id}`
Removes a `user_sections` row (and mirrors removal from the section's `group_members`, per the
same coupling). **Errors**: `MEMBERSHIP_NOT_FOUND` (404).

---

## Open Items for Backend Implementation Step

- Whether creating a `Section` should *always* auto-create its `Group`/`Conversation`, or whether
  that's a separate explicit action — currently assumed automatic and coupled; confirm before coding.
- Semester lifecycle (no delete endpoint currently) — may need an `is_active` / status field instead
  of relying on date ranges; revisit once the Admin Dashboard requirements are clearer.
- Cascading behavior on section deletion with active members — currently "block," could instead be
  "soft-delete section, leave `user_sections` rows orphaned but inert." Decide before writing the
  repository layer.
