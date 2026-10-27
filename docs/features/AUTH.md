# Authentication feature

## Overview

Students sign in with Google OAuth; teachers sign in with email OTP (two
phases). Both converge on JWT access/refresh token pairs with refresh-token
rotation. Refresh tokens are jti-blocklisted in Redis on logout/rotation.

## Database

- `users` (UUID PK, soft delete, `auth_provider`, `google_sub`, `email_verified_at`)
- `roles` / `permissions` / `role_permissions` / `user_roles` (RBAC)
- `audit_logs` — `auth.login.student` / `auth.login.teacher` events

## API

| Method | Path | Body | Auth | Description |
| ------ | ---- | ---- | ---- | ----------- |
| GET | `/auth/google/authorize` | query `state` | none | Google consent URL |
| POST | `/auth/google` | `{ code }` | none | Student login via OAuth code |
| POST | `/auth/teachers/otp/request` | `{ email }` | none | Phase 1: queue OTP email |
| POST | `/auth/teachers/otp/verify` | `{ email, code }` | none | Phase 2: tokens |
| POST | `/auth/refresh` | `{}` | refresh JWT | rotate token pair |
| POST | `/auth/logout` | `{}` | refresh JWT | blocklist refresh token |
| GET | `/auth/me` | none | access JWT | identity + claims |

## Security

- Anti-enumeration: OTP request returns the same shape for unknown emails.
- Rate limit: 5/minute on auth endpoints (Redis).
- Codes are hashed (passlib) in Redis with 10-min TTL, 3-attempt cap, 60-s
  resend lockout.
- Google userinfo email must be verified.

## Real-time

None (auth is request/response).

## Tests

- `backend/tests/unit/test_response_helpers.py` — envelope contract.
- `backend/tests/unit/test_rbac_decorator.py` — permission decorator.
- `backend/tests/integration/test_health_integration.py` — headers + 401.

## Frontend

- `frontend/src/pages/auth/Login.tsx` — provider selection + OTP phases
  (React Hook Form + Zod).
- `frontend/src/services/authService.ts` — API wrapper.
- `frontend/src/stores/useAuthStore.ts` — session-scoped token persistence.
- `frontend/src/services/apiClient.ts` — axios + 401 refresh-token rotation.

## Done checklist
- [x] models + migration (users, roles, permissions, associations)
- [x] repository + service (AuthService, TokenService, OTPService)
- [x] blueprint + schema validation (marshmallow)
- [x] frontend page + components
- [ ] docs/00_PROJECT_MEMORY.md — pending (see below)
