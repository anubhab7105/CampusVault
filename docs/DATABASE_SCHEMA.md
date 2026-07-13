# CampusVault — Database Schema v1

Status: Draft for review
Stage: Feature Implementation Workflow → Step 3 (Database Design)
Depends on: 03_DATABASE_GUIDE.md, 06_SECURITY_GUIDE.md, 07_SOCKET_GUIDE.md, 08_API_GUIDE.md

## Decisions Locked This Round

1. **Separate identity tables.** `users` is the shared identity/profile record. Auth-method-specific
   data lives in `student_identities` (Google OAuth) and `teacher_identities` (OTP), each 1:1 with
   `users`. This keeps auth logic isolated per method and avoids nullable-field sprawl on `users`.
2. **`message_receipts` added.** Not in the original 16-table list, but required by
   07_SOCKET_GUIDE.md's `read_receipt` / `delivery_status` events. Tracks per-user, per-message
   delivered/read state.
3. **Single institution, multiple departments.** No `tenant_id` / `institution_id`. `departments`
   is a flat top-level table. If CampusVault ever needs to serve multiple institutions, this is the
   first table that would need a parent `institutions` table added — flagged for future, not built now.

## Tables Beyond the Original 16 (flagged additions, all justified by other guides)

| Table | Why it's needed |
|---|---|
| `student_identities` | Decision 1 above |
| `teacher_identities` | Decision 1 above |
| `otp_codes` | Teacher OTP flow needs somewhere to store hashed codes + expiry + attempt count (Security Guide: rate limiting, "assume malicious") |
| `refresh_tokens` | Security Guide requires refresh token rotation — needs persistence to detect reuse/revoke |
| `role_permissions` | Security Guide says "RBAC with permission checks" — `roles` and `permissions` need a join table |
| `user_sections` | Students/teachers need to be scoped to a section (class) for RBAC + chat group auto-membership; implied by `sections` existing but not modeled in original list |
| `group_members` | `groups` table existed but had no membership join table |
| `conversation_participants` | Needed for DMs (`conversations` with no group_id) — who's in the DM |
| `message_receipts` | Decision 2 above |

Everything else maps directly to your original list: `users`, `roles`, `permissions`, `user_roles`,
`departments`, `programs`, `semesters`, `sections`, `subjects`, `groups`, `messages`,
`conversations`, `files`, `resources`, `notifications`, `audit_logs`.

## Standards Applied (per 03_DATABASE_GUIDE.md)

- All primary keys: UUID (`gen_random_uuid()` / Python `uuid4`)
- Soft delete: `deleted_at TIMESTAMPTZ NULL` on tables where records are user-facing and
  recoverable (users, departments, programs, sections, subjects, groups, files, resources).
  Pure log/event tables (audit_logs, message_receipts, otp_codes, refresh_tokens) are NOT
  soft-deleted — they're either immutable or expire naturally.
- Every FK has an index; composite indexes noted per table below.
- Timestamps: `created_at` on everything, `updated_at` where records are mutable.
- All schema changes go through Alembic migrations — no direct DDL.

---

## 1. Auth Domain

### `users`
Common identity for every person in the system, regardless of auth method.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | citext, unique, not null | canonical email |
| full_name | text, not null | |
| avatar_url | text, null | Supabase Storage path |
| user_type | enum('student','teacher','admin'), not null | |
| is_active | bool, default true | |
| created_at | timestamptz | |
| updated_at | timestamptz | |
| deleted_at | timestamptz, null | soft delete |

Indexes: unique(email), index(user_type).

### `student_identities`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id, unique, not null | 1:1 |
| google_sub | text, unique, not null | Google OAuth `sub` claim |
| google_email | text, not null | may differ from users.email pre-verification |
| created_at | timestamptz | |

Indexes: unique(google_sub), unique(user_id).

### `teacher_identities`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id, unique, not null | 1:1 |
| otp_email | text, not null | delivery address for OTP (Gmail SMTP in dev per README) |
| last_verified_at | timestamptz, null | |
| created_at | timestamptz | |

Indexes: unique(user_id).

### `otp_codes`
Short-lived, single-use. Never store plaintext codes.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| teacher_identity_id | UUID FK → teacher_identities.id, not null | |
| code_hash | text, not null | hashed, never plaintext |
| expires_at | timestamptz, not null | short TTL (e.g. 5–10 min, config-driven) |
| attempts | int, default 0 | for rate limiting / lockout |
| consumed_at | timestamptz, null | |
| created_at | timestamptz | |

Indexes: index(teacher_identity_id), index(expires_at) for cleanup job.

### `refresh_tokens`
Supports rotation + revocation per Security Guide.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id, not null | |
| token_hash | text, unique, not null | never store raw token |
| device_info | text, null | user agent / device label |
| issued_at | timestamptz | |
| expires_at | timestamptz, not null | |
| revoked_at | timestamptz, null | set on rotation or logout |

Indexes: index(user_id), unique(token_hash), index(expires_at).

---

## 2. RBAC Domain

### `roles`
id (UUID PK), name (unique, not null), description, created_at.

### `permissions`
id (UUID PK), code (unique, not null, e.g. `resource:upload`), description, created_at.

### `role_permissions`
role_id (FK → roles.id), permission_id (FK → permissions.id), composite PK(role_id, permission_id).

### `user_roles`
user_id (FK → users.id), role_id (FK → roles.id), assigned_at, composite PK(user_id, role_id).

---

## 3. Academic Structure Domain

### `departments`
id (UUID PK), name (unique, not null), code (unique, not null), created_at, updated_at, deleted_at.

### `programs`
id (UUID PK), department_id (FK → departments.id, not null), name, code, duration_years (int),
created_at, updated_at, deleted_at.
Index: index(department_id).

### `semesters`
id (UUID PK), program_id (FK → programs.id, not null), number (int, not null), name,
start_date, end_date, created_at, updated_at.
Composite index(program_id, number).

### `sections`
id (UUID PK), semester_id (FK → semesters.id, not null), name (not null), created_at, updated_at, deleted_at.
Index: index(semester_id).

### `subjects`
id (UUID PK), program_id (FK → programs.id, not null), semester_number (int, not null), name, code,
created_at, updated_at, deleted_at.
Composite index(program_id, semester_number).

### `user_sections` *(addition)*
Scopes a student/teacher to a section — drives RBAC scoping and auto-membership in the section's chat group.

id (UUID PK), user_id (FK → users.id, not null), section_id (FK → sections.id, not null),
role_context (enum('enrolled','teaching'), not null), joined_at.
Composite unique(user_id, section_id, role_context).

---

## 4. Chat Domain

### `groups`
id (UUID PK), name (not null), description, type (enum('section','custom'), not null),
section_id (FK → sections.id, null — set when type='section'), created_by (FK → users.id),
created_at, updated_at, deleted_at.
Index: index(section_id).

### `group_members` *(addition)*
group_id (FK → groups.id), user_id (FK → users.id), role_in_group (enum('admin','member'), default 'member'),
joined_at. Composite PK(group_id, user_id).

### `conversations`
id (UUID PK), type (enum('dm','group'), not null), group_id (FK → groups.id, null — set when type='group'),
created_at, updated_at.
Index: index(group_id).

### `conversation_participants` *(addition)*
Primarily for DMs (2 rows per conversation); group conversations can derive participants from `group_members`
but storing explicitly simplifies queries and socket room authorization.

conversation_id (FK → conversations.id), user_id (FK → users.id), joined_at.
Composite PK(conversation_id, user_id).

### `messages`
id (UUID PK), conversation_id (FK → conversations.id, not null), sender_id (FK → users.id, not null),
content (text, not null), content_type (enum('text','file'), default 'text'),
edited_at (timestamptz, null), deleted_at (timestamptz, null — soft delete for "delete_message" event),
created_at.
Composite index(conversation_id, created_at) for pagination.

### `message_receipts` *(addition, decision 2)*
id (UUID PK), message_id (FK → messages.id, not null), user_id (FK → users.id, not null),
status (enum('delivered','read'), not null), status_at (timestamptz, not null), created_at.
Composite unique(message_id, user_id, status) — one row per user per status transition.
Index: index(message_id).

---

## 5. Library / Files Domain

### `files`
id (UUID PK), uploader_id (FK → users.id, not null), original_filename (text, not null),
stored_filename (text, unique, not null — randomized per Security Guide), mime_type (text, not null),
size_bytes (bigint, not null), storage_path (text, not null — Supabase Storage key),
scan_status (enum('pending','clean','infected'), default 'pending'), scanned_at (timestamptz, null),
created_at, deleted_at.
Index: index(uploader_id), index(scan_status).

### `resources`
id (UUID PK), title (not null), description, file_id (FK → files.id, not null),
department_id (FK → departments.id, null), program_id (FK → programs.id, null),
subject_id (FK → subjects.id, null), uploaded_by (FK → users.id, not null),
created_at, updated_at, deleted_at.
Index: index(subject_id), index(department_id).

---

## 6. Notifications Domain

### `notifications`
id (UUID PK), user_id (FK → users.id, not null), type (text, not null — e.g. `message.new`, `resource.uploaded`),
title (text, not null), body (text, null), data (jsonb, null — structured payload for frontend routing),
read_at (timestamptz, null), created_at.
Composite index(user_id, read_at) for unread-count queries.

---

## 7. Audit Domain

### `audit_logs`
id (UUID PK), user_id (FK → users.id, null — null for unauthenticated/system events),
action (text, not null — e.g. `login`, `logout`, `upload`, `download`, `role.assign`),
entity_type (text, null), entity_id (UUID, null),
ip_address (inet, null), user_agent (text, null), metadata (jsonb, null),
created_at.
Composite index(user_id, created_at), index(action).
Never soft-deleted — audit logs are append-only.

---

## Open Items for Next Pass

- Full-text search / materialized views (flagged as "Future Improvements" in Database Guide — not blocking v1)
- Archival strategy for old messages/notifications — not blocking v1
- Whether `subjects` should also have a `section_id` link for per-section subject overrides, or stay
  program+semester scoped as modeled — assumed program+semester scoped for now
