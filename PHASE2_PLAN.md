# Phase 2: Authentication + RBAC — End-to-End Implementation Plan

## 1. Requirements Overview

### Backend

1. **Google OAuth for Students**
   - Authorize endpoint returns consent-screen URL (already partially implemented).
   - Callback endpoint (`/api/v1/auth/google`) exchanges the code for userinfo.
   - **Email domain restriction**: only emails matching `GOOGLE_ALLOWED_DOMAINS` (comma-separated env var) are accepted; reject others with `UnauthorizedError`.
   - **Auto-provision**: first-time Google users are auto-created with the `Student` system role.
   - **Email verification**: reject unverified Google accounts (`email_verified` must be `True` from userinfo).
   - Returns canonical success envelope with `tokens` + `user`.

2. **Teacher OTP Login**
   - **Request OTP** (`/api/v1/auth/teachers/otp/request`):
     - Anti-enumeration: same response shape for unknown emails.
     - Rate limit: per-email (3 attempts per 5 minutes) and per-IP (5 attempts per minute).
     - OTP is issued via `otp_service.issue(email)` — already hashed in Redis with TTL.
     - Delivery via Celery `send_otp_email` task (Gmail SMTP dev).
   - **Verify OTP** (`/api/v1/auth/teachers/otp/verify`):
     - Max 5 attempts per email window; after 5 failures, 60-second lockout.
     - Code is single-use; reused codes are rejected.
     - Rate limit: per-email (5 attempts per 5 minutes).
   - Only pre-approved teacher emails (admin-managed allowlist in `teacher_allowlist` table) may log in.

3. **Token Lifecycle**
   - **Access JWT**: short-lived (15 min dev, configurable), carries `role` + `permissions` claims.
   - **Refresh token**: long-lived (30 days dev), delivered via `Set-Cookie` (`HttpOnly`, `Secure`, `SameSite=Lax`).
   - **Refresh rotation**: on each use, old refresh JTI is blocklisted in Redis; new pair issued with re-derived role/permissions.
   - **Reuse detection**: if a previously-revoked refresh JTI is replayed, the entire token family is revoked (all JTIs for that user are blocklisted).
   - **Logout**: revokes the presented refresh token (adds its JTI to blocklist).
   - **CSRF protection** for `/api/v1/auth/refresh`: require `X-CSRF-Token` header matching the value in a hidden form field or `XSRF-TOKEN` cookie.

4. **RBAC**
   - **Seed system roles** (Student, Teacher, Admin) and a permission catalog idempotently (already partially in `role_service.py`).
   - **Role/permission CRUD** with admin-only endpoints:
     - `GET /api/v1/rbac/roles` — list roles + their permission grants.
     - `GET /api/v1/rbac/permissions` — list all permission codes + descriptions.
     - `POST /api/v1/rbac/roles/{id}/permissions` — grant/replace permissions on a role.
     - `POST /api/v1/rbac/users/{id}/roles` — assign/revoke roles for a user (admin only).
   - **Effective permissions** included in `/api/v1/auth/me` response (`role` + `permissions`).
   - **`@permission_required` decorator** on every protected route (already partially in `middleware/rbac.py`).
   - **Last-admin protection**: the last admin user cannot be deactivated or demoted.
   - **Role hierarchy**: Admin > Teacher > Student; Admin implies all permissions.

5. **Admin: Teacher Allowlist & User Deactivation**
   - **Teacher allowlist** table: `teacher_allowlist(id, email, is_approved, approved_by, approved_at, expires_at)`.
   - Only emails on the allowlist may complete teacher OTP verification.
   - Admin can add/remove emails from the allowlist.
   - **User deactivation** (`PATCH /api/v1/admin/users/{id}`):
     - Admin cannot deactivate themselves.
     - The last admin cannot be demoted (role can only be changed, not deactivated, when they are the sole admin).
     - Audit event on deactivation.

6. **Audit Logging**
   - Log actions: `auth.login.student`, `auth.login.teacher`, `auth.logout`, `auth.refresh.reuse_detected`, `role.grant`, `role.revoke`, `user.deactivate`, `teacher.allowlist.add`, `teacher.allowlist.remove`.
   - Each entry: `action`, `entity_type`, `entity_id`, `request_id`, `changes` (before/after), `outcome` (success/failure), `ip_address`, `user_agent`.

### Frontend

1. **Login page**: 
   - Google sign-in button (opens `/api/v1/auth/google/authorize` then handles callback).
   - Teacher two-step OTP form (email entry → code entry), with resend cooldown.
   - Accessible error messages; do not reveal whether email is registered (same anti-enumeration response).

2. **Auth store** (Zustand):
   - Access token stored **in memory only** (remove token persistence from sessionStorage).
   - Silent session restore on app load: read refresh cookie, call `/api/v1/auth/me`; if authenticated, set tokens in memory and navigate to dashboard.
   - Axios interceptor with **single in-flight refresh**: concurrent 401s are queued and retried once the new access token is available.

3. **ProtectedRoute + PermissionGate + usePermission**:
   - `ProtectedRoute`: redirects to `/login` when `isAuthenticated` is `false`; preserves `from` location for redirect-back.
   - `PermissionGate`: renders children only if the user's effective permissions include the required code; otherwise shows `EmptyState`.
   - `usePermission(code)` hook: returns `boolean` + `loading` state from `/auth/me`.

4. **Admin UI**:
   - Roles/permissions grant matrix: multi-select for each role.
   - User list with role assignment dropdown and deactivation toggle (with last-admin protection warning).
   - Teacher allowlist management: add/remove email inputs, approve/revoke toggle.
   - Uses existing UI components (Button, Input, Card, Table, Dialog, Toast, Skeleton, EmptyState).
   - Skeleton loaders on data fetch, empty states for no items.

5. **Socket store**:
   - Connects only after authentication (JWT handshake).
   - Reconnects with a fresh token if the access token rotates.
   - Rooms: `group_<id>`, `dm_<id>` with authorization per event.

### Standards & Borders

- **Preserve canonical response envelopes** (success / error).
- **Thin-controller / service / repository layering** — never bypass.
- **Naming conventions**: UPPER_SNAKE_CASE for constants, camelCase for JS/TS, snake_case for DB/migrations.
- **New migrations via Alembic only** (e.g., `teacher_allowlist`, `refresh_token_family`, `audit_log` extensions). Never edit `0001_initial_core_tables.py`.
- **Update docs/api/README.md** and the OpenAPI spec for every new endpoint.
- **Write `docs/features/AUTH.md`** and `docs/features/RBAC.md` fully (models, API, security model, threat notes, tests, checklist).
- **Record any new library or decision in docs/** (decision log).

## 2. Affected Modules

### Backend
- `app/blueprints/auth/__init__.py` — enhance Google callback, add teacher OTP rate limiting, refresh CSRF, reuse detection.
- `app/services/auth_service.py` — email domain validation, auto-provision, teacher allowlist check.
- `app/services/token_service.py` — rotation with reuse detection, family revocation, CSRF-aware.
- `app/services/role_service.py` — ensure system roles exist, effective permissions, role/permission CRUD.
- `app/models/user.py` — no changes needed (soft delete already present).
- `app/models/role.py` — no changes needed.
- `app/models/permission.py` — no changes needed.
- `app/repositories/user_repository.py` — add `get_by_domain`, `is_teacher_allowlisted`, `can_deactivate`, `set_active`.
- `app/repositories/role_repository.py` — add `grant_permissions`, `revoke_permissions`, `assign_role`, `get_user_roles`.
- `app/repositories/permission_repository.py` — add `get_by_code`, list all.
- `app/models/teacher_allowlist.py` — new model: `id`, `email`, `is_approved`, `approved_by`, `approved_at`, `expires_at`.
- `app/middleware/auth.py` — CSRF validation for refresh endpoint.
- `app/middleware/rbac.py` — `@permission_required` decorator enhancement, last-admin guard.
- `app/middleware/security_headers.py` — add `SameSite=Lax` guidance.
- `app/utils/redis_utils.py` — OTP attempt counter, lockout tracker.
- `app/utils/responses.py` — consistent error shapes.
- `app/errors/exceptions.py` — new exceptions: `TeacherNotApprovedError`, `RefreshReuseDetectedError`, `CSRFTokenMissingError`.
- `app/tasks/emails.py` — OTP email with cooldown tracking.
- `app/middleware/security_headers.py` — set `Set-Cookie` on refresh response.

### Frontend
- `frontend/src/stores/useAuthStore.ts` — in-memory tokens, silent session restore, refresh interceptor.
- `frontend/src/routes/ProtectedRoute.tsx` — redirect-back, preserve `from` location.
- `frontend/src/routes/permissions.ts` — `usePermission` hook + `PermissionGate` component.
- `frontend/src/pages/auth/Login.tsx` — Google button + OTP two-step form, anti-enumeration.
- `frontend/src/components/ui/` — no new components; use existing kit.
- `frontend/src/services/apiClient.ts` — refresh interceptor with queue, CSRF header support.

### Database (Alembic migrations)
- New migration: `teacher_allowlist` table.
- New migration: `refresh_token_family` / JTI tracking enhancements.
- Potentially extend `audit_log` table or create separate `audit_events` table (but existing `audit_log` is already used — extend it).

### Docs
- `docs/features/AUTH.md` — full feature documentation.
- `docs/features/RBAC.md` — full feature documentation.
- `docs/api/README.md` — update endpoint catalog + real-time spec.

## 3. DB Impact

### New table: `teacher_allowlist`
| Column | Type | Constraints |
|---|---|---|
| `id` | UUID PK | |
| `email` | String(255) | UNIQUE, NOT NULL, INDEX |
| `is_approved` | Boolean | DEFAULT false |
| `approved_by` | UUID FK → users.id | NULLABLE |
| `approved_at` | DateTime | NULLABLE |
| `expires_at` | DateTime | NULLABLE |

### Enhancements to existing tables
- `users` table: `is_active` already present (soft delete). Add index on `email_verified_at` for OAuth eligibility checks.
- `audit_log` table: add `ip_address`, `user_agent`, `outcome` columns (or add as new column migration). Actually, looking at existing schema, audit_log already has `id`, `actor_id`, `action`, `entity_type`, `entity_id`, `request_context`, `changes`, `created_at`. We'll add `outcome` and `ip_address`/`user_agent` as new columns via migration.

### Indexes
- `teacher_allowlist.email` UNIQUE index.
- `audit_log.outcome` index for filtering.
- `users.email_verified_at` index for Google eligibility fast-path.

## 4. Security Impact & Threat Mitigation

| Threat | Mitigation |
|---|---|
| Google email enumeration | Anti-enumeration: same response shape for unknown emails; OTP request also same shape. |
| OTP brute-force | Max 5 attempts per email window; 60s lockout after 5 failures; per-IP rate limit (5/min); OTP hashed in Redis with TTL. |
| Refresh token theft | HttpOnly, Secure, SameSite=Lax cookie; jti blocklist in Redis with TTL; rotation on use; reuse detection + family revocation. |
| CSRF on refresh endpoint | `X-CSRF-Token` header required; token from `XSRF-TOKEN` cookie set on login. |
| Role escalation | Last-admin protection: when a user holds the `Admin` role and is the sole admin, deactivation and role-demotion are blocked. |
| Teacher impersonation | Only allowlist emails may complete OTP verification; allowlist managed by admin; OTP single-use, rate-limited. |
| Google domain bypass | Email domain check against `GOOGLE_ALLOWED_DOMAINS` env var; reject unverified Google accounts. |
| Audit tampering | Audit entries append-only; `request_id` + `ip_address` + `user_agent` captured per request. |

## 4. Testing Strategy

### Backend
- **Unit tests**: OAuth happy path (mock Google), OTP expiry/attempts/reuse/rate limit, refresh rotation/reuse detection, logout revocation, RBAC allow/deny per role, last-admin protection, audit entries.
- **Integration tests**: Real PostgreSQL (CI service container) for end-to-end flows: student Google login → auto-provision → dashboard access; teacher OTP request+verify with allowlist; refresh rotation; admin deactivate user; teacher allowlist management.
- **Coverage**: Raise `fail_under` to 70% for this phase.

### Frontend
- **Vitest + RTL**: Login form rendering, Google callback flow (mocked), ProtectedRoute redirect, PermissionGate, usePermission hook, refresh interceptor behavior (single in-flight queue).
- **Playwright E2E**: Student login flow (Google mocked), Teacher login flow (OTP request+verify with allowlist), Admin UI (roles/permissions matrix, allowlist management, deactivation with last-admin guard).
- **Cross-browser**: Chromium (default), Firefox, WebKit.

## 5. Definition of Done
- [ ] All backend endpoints implemented and tested (OAuth, OTP, refresh, RBAC, admin, audit).
- [ ] Frontend Login page fully functional (Google + OTP, accessible, anti-enumeration).
- [ ] Auth store in memory only, silent session restore, refresh interceptor with queue.
- [ ] ProtectedRoute + PermissionGate + usePermission hook working.
- [ ] Admin UI: roles/permissions matrix, teacher allowlist, user deactivation with last-admin guard.
- [ ] Socket.IO connects after auth, reconnects with fresh token.
- [ ] Lint, mypy, tsc, build all clean.
- [ ] `docs/features/AUTH.md` and `docs/features/RBAC.md` fully written.
- [ ] `docs/api/README.md` updated with new endpoint catalog.
- [ ] Coverage `fail_under` raised to 70% (backend + frontend).
- [ ] No regressions in existing tests.
- [ ] `docs/00_PROJECT_MEMORY.md` updated: Authentication and RBAC → Completed.

## 5. Residual Risks
- Google OAuth depends on third-party APIs; network failures may cause transient 500s.
- Redis downtime blocks JWT rotation, OTP verification, and socket rooms.
- Teacher allowlist is a single point of failure for teacher login; if the allowlist table is empty, no teacher can log in.
- CSRF token mismatch if the frontend does not properly read/set the `XSRF-TOKEN` cookie.
- OTP delivery via Gmail SMTP in dev only; production requires external email service configuration.

## 6. Phase 3 (Proposed)
- Library / Supabase Storage uploads + malware scan pipeline.
- Real-time chat enhancements (read receipts, typing indicators, message editing).
- Advanced RBAC: custom role creation, permission inheritance.
- Performance optimization: query indexing, query caching.
- End-to-end encryption for direct messages.