# CampusVault — API Design: Auth Domain v1

Status: Draft for review
Stage: Feature Implementation Workflow → Step 4 (API Design), Auth domain first
Depends on: 03_DATABASE_GUIDE.md (implemented), 06_SECURITY_GUIDE.md, 08_API_GUIDE.md, DATABASE_SCHEMA.md

## Assumption Flagged

No guide specifies a backend validation library. Frontend is locked to Zod (05_FRONTEND_GUIDE.md);
backend `schemas/` folder (04_BACKEND_GUIDE.md) doesn't name one. Using **Pydantic v2** — pairs
naturally with the typed SQLAlchemy 2.0 models already built. Flag if you'd rather use Marshmallow.

## Conventions (per 08_API_GUIDE.md)

- Base path: `/api/v1/auth`
- All responses use the locked envelope:
  ```json
  { "success": true, "message": "...", "data": {} }
  { "success": false, "error": { "code": "...", "message": "..." } }
  ```
- JWT access tokens are short-lived (assume 15 min, configurable); refresh tokens are long-lived
  (assume 30 days, configurable) and rotate on every use per 06_SECURITY_GUIDE.md.
- Rate limiting applies to every endpoint below, especially OTP request/verify (brute-force target).

---

## Student Flow: Google OAuth

### `POST /api/v1/auth/student/google`
Exchanges a Google ID token (obtained client-side via Google Sign-In) for CampusVault session tokens.

**Request**
```json
{ "id_token": "eyJhbGciOi..." }
```

**Service logic**
1. Verify `id_token` signature + audience against Google's public keys.
2. Extract `sub` (Google subject id) and `email`.
3. Look up `student_identities.google_sub`.
   - If found → load linked `users` row (existing student).
   - If not found → this is first login. Create `users` row (`user_type=student`) +
     `student_identities` row in one transaction.
4. Check `users.is_active` — reject if deactivated.
5. Issue access token (JWT, embeds `user_id`, `user_type`, `roles`) + refresh token
   (persisted to `refresh_tokens`, hashed).
6. Write `audit_logs` row: `action="login"`, `entity_type="user"`.

**Response `200`**
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "email": "student@college.edu",
      "full_name": "Jane Doe",
      "user_type": "student",
      "avatar_url": null
    }
  }
}
```

**Errors**
| Code | HTTP | When |
|---|---|---|
| `INVALID_GOOGLE_TOKEN` | 401 | signature/audience verification fails |
| `ACCOUNT_DEACTIVATED` | 403 | `users.is_active = false` |
| `RATE_LIMITED` | 429 | too many attempts from IP/identity |

---

## Teacher Flow: OTP

### `POST /api/v1/auth/teacher/otp/request`
Requests an OTP be emailed to a teacher's registered address.

**Request**
```json
{ "email": "teacher@college.edu" }
```

**Service logic**
1. Look up `teacher_identities.otp_email` (case-insensitive).
   - Not found → do **not** reveal whether the account exists (Security Guide: assume malicious).
     Return the same generic success response regardless, only actually send email if found.
2. Generate a 6-digit code, hash it (never store plaintext), insert into `otp_codes` with
   `expires_at` (assume 10 min) and `attempts=0`.
3. Enforce rate limiting: max N requests per email per hour (config-driven).
4. Send email via Celery task (async, don't block the request) — Gmail SMTP in dev per README.
5. Write `audit_logs` row: `action="otp.requested"`.

**Response `200`** (always this shape, regardless of whether the account exists)
```json
{ "success": true, "message": "If an account exists, a code has been sent.", "data": {} }
```

**Errors**
| Code | HTTP | When |
|---|---|---|
| `RATE_LIMITED` | 429 | too many requests for this email/IP |
| `VALIDATION_ERROR` | 400 | malformed email |

### `POST /api/v1/auth/teacher/otp/verify`
Verifies the OTP and issues session tokens.

**Request**
```json
{ "email": "teacher@college.edu", "code": "482913" }
```

**Service logic**
1. Look up the latest unconsumed, unexpired `otp_codes` row for this `teacher_identity_id`.
2. Compare hash. On mismatch, increment `attempts`; lock out after N failures (config-driven)
   by invalidating the code early.
3. On match: set `consumed_at`, set `teacher_identities.last_verified_at`.
4. Issue access + refresh tokens exactly as in the student flow.
5. Write `audit_logs` row: `action="login"`.

**Response `200`** — same shape as student login, `user_type: "teacher"`.

**Errors**
| Code | HTTP | When |
|---|---|---|
| `INVALID_OR_EXPIRED_CODE` | 401 | no match, expired, or already consumed |
| `TOO_MANY_ATTEMPTS` | 429 | attempts exceeded on this code |
| `RATE_LIMITED` | 429 | too many verify calls overall |

---

## Shared: Token Lifecycle

### `POST /api/v1/auth/refresh`
Rotates a refresh token for a new access + refresh token pair.

**Request**
```json
{ "refresh_token": "eyJ..." }
```

**Service logic**
1. Hash incoming token, look up in `refresh_tokens`.
2. If not found, or `revoked_at` is set, or expired → reject. If a *revoked* token is presented,
   treat as possible theft: revoke all other active refresh tokens for that `user_id` too
   (reuse detection per Security Guide).
3. On valid: set `revoked_at` on the old row, issue + persist a new refresh token row, issue a
   new access token.

**Response `200`** — same token shape as login.

**Errors**
| Code | HTTP | When |
|---|---|---|
| `INVALID_REFRESH_TOKEN` | 401 | not found, expired, or malformed |
| `TOKEN_REUSE_DETECTED` | 401 | previously revoked token presented — all sessions revoked |

### `POST /api/v1/auth/logout`
Requires valid access token (middleware-authenticated).

**Service logic**
1. Revoke the refresh token tied to the current session (client sends it in body, or server
   tracks current session token — implementation detail for Backend step).
2. Write `audit_logs` row: `action="logout"`.

**Response `200`**
```json
{ "success": true, "message": "Logged out.", "data": {} }
```

### `GET /api/v1/auth/me`
Requires valid access token. Returns the current user's profile + roles.

**Response `200`**
```json
{
  "success": true,
  "message": "OK",
  "data": {
    "id": "uuid",
    "email": "...",
    "full_name": "...",
    "user_type": "student",
    "roles": ["student"],
    "avatar_url": null
  }
}
```

**Errors**
| Code | HTTP | When |
|---|---|---|
| `UNAUTHORIZED` | 401 | missing/invalid/expired access token |

---

## Open Items for Backend Implementation Step

- Exact OTP length/expiry/rate-limit numbers — used sensible defaults above (6 digits, 10 min,
  configurable) — confirm before hardcoding.
- Whether logout should revoke *all* refresh tokens for the user (full logout) or just the current
  device's — assumed single-device logout above; multi-device "log out everywhere" could be a
  separate endpoint later.
- JWT claims payload — assumed `user_id`, `user_type`, `roles` embedded; confirm nothing else needed
  (e.g. active `section_id` for scoping) before implementation.
