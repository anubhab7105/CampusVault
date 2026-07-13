# CampusVault — API Design: RBAC Domain v1

Status: Draft for review
Stage: Feature Implementation Workflow → Step 4 (API Design), RBAC domain
Depends on: DATABASE_SCHEMA.md (roles, permissions, role_permissions, user_roles), 06_SECURITY_GUIDE.md, 08_API_GUIDE.md

## Scope & Access

Everything in this domain is **admin-only** (`user_type=admin` or a role holding the relevant
`rbac:*` permission). Students/teachers never call these directly — their effective permissions
are exposed instead via `GET /api/v1/auth/me` (already spec'd) and enforced server-side by
middleware on every other endpoint.

Base path: `/api/v1/rbac`

## Seed Data Assumption

RBAC needs bootstrap data before the app is usable (an `admin` role, base `student`/`teacher`
roles, and a starter permission set). This is a migration-time seed, not an API endpoint — flagged
here so it isn't forgotten at the Backend Implementation step. No endpoint here creates the first
admin; that's a one-time Alembic data migration or CLI command.

---

## Roles

### `GET /api/v1/rbac/roles`
List all roles with their permission codes. Paginated per API Guide standards.

**Response `200`**
```json
{
  "success": true,
  "message": "OK",
  "data": {
    "items": [
      { "id": "uuid", "name": "teacher", "description": "...", "permissions": ["resource:upload", "group:create"] }
    ],
    "page": 1,
    "page_size": 20,
    "total": 4
  }
}
```

### `POST /api/v1/rbac/roles`
**Request**: `{ "name": "librarian", "description": "..." }`
**Response `201`**: created role object (no permissions yet).
**Errors**: `VALIDATION_ERROR` (400), `ROLE_NAME_TAKEN` (409).

### `PATCH /api/v1/rbac/roles/{role_id}`
Update name/description only — permission changes go through the dedicated endpoints below
(keeps the audit trail granular per action, matching `audit_logs.action` design).
**Errors**: `ROLE_NOT_FOUND` (404), `VALIDATION_ERROR` (400).

### `DELETE /api/v1/rbac/roles/{role_id}`
Hard delete — `roles` has no soft-delete column (see DATABASE_SCHEMA.md; roles are structural,
not user content). Blocked if any `user_roles` rows reference it.
**Errors**: `ROLE_NOT_FOUND` (404), `ROLE_IN_USE` (409).

---

## Permissions

### `GET /api/v1/rbac/permissions`
List all permission codes (reference data — small, likely no pagination needed in practice,
but keep the envelope consistent). Read-only via API; permission *codes* are expected to be
defined in the codebase/migrations, not created ad hoc by admins (prevents typo'd, unenforced
permission strings).

**Response `200`**
```json
{ "success": true, "message": "OK", "data": { "items": [ { "id": "uuid", "code": "resource:upload", "description": "..." } ] } }
```

### `PUT /api/v1/rbac/roles/{role_id}/permissions`
Replace a role's full permission set in one call (idempotent — simpler and safer than granular
add/remove for a low-frequency admin action).

**Request**: `{ "permission_codes": ["resource:upload", "group:create", "notification:send"] }`
**Service logic**: validate every code exists in `permissions`; diff against current
`role_permissions` rows; delete removed, insert added, all in one transaction. Write
`audit_logs`: `action="role.permissions_updated"`, `entity_type="role"`, `entity_id=role_id`,
`metadata={"before": [...], "after": [...]}`.
**Response `200`**: updated role with new permission list.
**Errors**: `UNKNOWN_PERMISSION_CODE` (400), `ROLE_NOT_FOUND` (404).

---

## User–Role Assignment

### `GET /api/v1/rbac/users/{user_id}/roles`
**Response `200`**: `{ "data": { "roles": ["student", "librarian"] } }`

### `PUT /api/v1/rbac/users/{user_id}/roles`
Replace a user's full role set (same idempotent-replace pattern as permissions, same reasoning).

**Request**: `{ "role_names": ["student", "librarian"] }`
**Service logic**: diff against `user_roles`, apply, single transaction. Write `audit_logs`:
`action="role.assign"`, `entity_type="user"`, `entity_id=user_id`, `metadata={"before": [...], "after": [...]}`.
This is one of the explicit audit actions named in 06_SECURITY_GUIDE.md ("admin actions").

**Response `200`**: updated role list.
**Errors**: `USER_NOT_FOUND` (404), `UNKNOWN_ROLE_NAME` (400).

---

## Middleware Contract (for Backend step)

Every non-RBAC endpoint elsewhere in the API is expected to declare required permission code(s)
at the route level (e.g. `@require_permission("resource:upload")`), resolved by a shared
middleware step that:
1. Reads `user_id` from the validated JWT.
2. Loads roles → permissions (cached; this is a hot path, candidate for Redis caching per
   10_PERFORMANCE_GUIDE.md — "cache frequently accessed data").
3. 403s with `code: "FORBIDDEN"` if the permission isn't present.

This contract is referenced by every other domain's API spec instead of being repeated in each one.

## Open Items for Backend Implementation Step

- Exact starter permission code list (e.g. `resource:upload`, `resource:delete`, `group:create`,
  `group:manage`, `notification:send`, `rbac:manage`, `user:manage`) — draft a full list at
  Backend Implementation time once every domain's endpoints are known.
- Cache invalidation strategy for the roles→permissions cache on `PUT .../permissions` and
  `PUT .../roles` calls.
