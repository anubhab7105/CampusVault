# Authentication feature

## Overview

Students sign in with Google OAuth (email domain-verified, auto-provisioned with
the `Student` role). Teachers sign in with email OTP (two-phase flow; only
pre-approved teacher emails may complete the verification). Both paths converge
on JWT access/refresh token pairs with refresh-token rotation, reuse detection,
and Redis jti blocklist. Refresh tokens are delivered via httpOnly, Secure,
SameSite=Lax cookie; the access token lives in memory on the frontend.

## Database

- `users` (UUID PK, soft delete, `auth_provider`, `google_sub`, `email_verified_at`).
- `teacher_allowlist` (UUID PK, `email` UNIQUE, `is_approved`, `approved_by`,
  `approved_at`, `expires_at`) — admin‑managed allowlist of teacher emails.
- `roles` / `permissions` / `role_permissions` / `user_roles` (RBAC).
- `audit_logs` — `auth.login.student`, `auth.login.teacher`, `auth.logout`,
  `auth.refresh.reuse_detected`, `role.grant`, `role.revoke`,
  `user.deactivate`, `teacher.allowlist.add`, `teacher.allowlist.remove`
  events.

## API

| Method | Path | Body | Auth | Description |
| ------ | ---- | ---- | ---- | ----------- |
| GET | `/auth/google/authorize` | query `state` | none | Google consent URL |
| POST | `/auth/google` | `{ code }` | none | Student login via OAuth code |
| POST | `/auth/teachers/otp/request` | `{ email }` | none | Phase 1: queue OTP email (rate‑limited, anti‑enumeration) |
| POST | `/auth/teachers/otp/verify` | `{ email, code }` | none | Phase 2: exchange OTP for tokens (allowlist‑checked) |
| POST | `/auth/refresh` | `{}` | refresh JWT | Rotate token pair; CSRF token required; reuse detection |
| POST | `/auth/logout` | `{}` | refresh JWT | Revoke refresh token (jti blocklist) |
| GET | `/auth/me` | none | access JWT | Identity + role + effective permission list |

## Security

- **Google OAuth**: only emails matching `GOOGLE_ALLOWED_DOMAINS` (configurable via
  env) are accepted; unverified Google accounts are rejected. Auto‑provision
  `Student` role on first login.
- **OTP anti‑enumeration**: request endpoint returns the same shape for unknown
  emails; max 3 attempts per 5 minutes per email in Redis; 60‑second lockout
  after 5 failures.
- **Refresh token rotation**: each use blocklists the old JTI in Redis; if a
  previously‑revoked JTI is replayed, the entire token family (all JTIs for that
  user) is revoked — user must log in again.
- **HttpOnly, Secure, SameSite=Lax cookie** for refresh tokens; access token
  returned only in JSON body and kept in memory on the frontend.
- **CSRF protection**: `X‑CSRF‑Token` header required on `/auth/refresh`; token
  sourced from `XSRF‑TOKEN` cookie set on login.
- **Rate limiting**: 5/minute on auth endpoints (Redis‑backed); 3 OTP attempts
  per 5 minutes per email.
- **Teacher allowlist**: only approved emails may complete OTP verification;
  managed by admin via `teacher_allowlist` table.
- **Last‑admin protection**: the last admin user cannot be deactivated or
  demoted.
- **Audit**: every login, logout, refresh reuse detection, role change, and
  user deactivation is logged with `action`, `entity_type`, `entity_id`,
  `request_id`, `ip_address`, `user_agent`, and `outcome` (success/failure).

## Real-time

None (auth is request/response; real-time authorization is covered in the
Chat/Socket.IO feature guide).

## Tests

- **Unit**: OAuth happy/failure paths (mock Google), OTP expiry/attempts/reuse/rate
  limit, refresh rotation and reuse detection, logout revocation, RBAC allow/deny
  for each role, last‑admin protection, audit entries, socket auth rejection.
- **Integration**: real PostgreSQL CI flow for end‑to‑end student and teacher
  login flows (Google mocked), admin UI interactions, teacher allowlist
  management.
- **Frontend**: Vitest + RTL for login forms, ProtectedRoute, PermissionGate and
  the refresh interceptor; Playwright E2E for student and teacher login flows
  (Google mocked).
- Coverage gate: `fail_under` 70% for this phase, with a plan to reach 80%.

## Frontend

- `frontend/src/pages/auth/Login.tsx` — Google sign‑in button and teacher
  two‑step OTP form (React Hook Form + Zod, accessible error messages, resend
  cooldown display).
- `frontend/src/stores/useAuthStore.ts` — in‑memory tokens only (no session
  persistence). Silent session restore on app load via the refresh cookie. Axios
  interceptor with a single in‑flight refresh queue (`pendingEmitQueue` pattern).
- `frontend/src/hooks/usePermission.ts` — fetches `/auth/me` and returns
  `hasPermission + permissions`; used by `PermissionGate`.
- `frontend/src/routes/ProtectedRoute.tsx` — redirects to `/login` when the
  access token is absent; preserves `from` location for redirect‑back.
- `frontend/src/routes/PermissionGate.tsx` — renders children only if the user’s
  effective permissions include the required code; otherwise shows `EmptyState`.
- `frontend/src/pages/admin/Admin.tsx` — roles/permissions grant matrix, user
  list with role assignment and deactivation (with last‑admin guard), teacher
  allowlist management. Uses existing UI components, skeleton loaders, empty
  states and toasts.

## Done checklist

- [x] Models + migration (`teacher_allowlist` table, audit_log extensions)
- [x] Repository + service (AuthService, TokenService, OTPService, RoleService)
- [x] Blueprint + schema validation (marshmallow schemas, Zod on frontend)
- [x] Frontend page + components (Login, ProtectedRoute, PermissionGate, Admin UI)
- [x] `docs/features/AUTH.md` — full feature documentation
- [x] `docs/api/README.md` — updated endpoint catalog + real‑time spec
- [ ] `docs/00_PROJECT_MEMORY.md` — Authentication and RBAC → Completed (pending final review)