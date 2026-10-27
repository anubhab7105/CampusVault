# Phase 3: Library + File Storage + Malware Scan Pipeline — Implementation Plan

## 1. Requirements Overview

### Backend

#### 1.1 Supabase Storage Integration
- Define a `StorageBackend` protocol/interface (abstract base class) with methods:
  - `upload(key, fileobj, mime_type, size) -> dict` — returns `{storage_key, url, expires_at}`
  - `download(key) -> bytes` — returns file bytes
  - `delete(key) -> None`
  - `exists(key) -> bool`
- Create `SupabaseStorage` implementation that imports the Supabase client **only at runtime** (lazy import inside methods), never at module level, so the service layer never depends on the Supabase SDK directly.
- Fail fast at app startup if `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET` are not set (raise `ConfigError` from `create_app`).
- Record the decision in `docs/decision_log.md` (see section below).
- Add `supabase` to `requirements/dev.txt` (optional, only installed when env vars present) or `requirements/base.txt` with a try/except import pattern.

#### 1.2 Two-Phase Upload Flow
**Phase A: Upload Request** (`POST /api/v1/library/upload-request`)
- Validate:
  - Extension whitelist from config (`UPLOAD_ALLOWED_EXTENSIONS`)
  - MIME type (client-supplied must match actual magic bytes later)
  - Declared size against `UPLOAD_MAX_SIZE_BYTES` and per-type limits
  - Permission: Teacher/Admin may upload; Students may only view/download
- Create `files` row with:
  - `storage_key` = random 32-char base64 string (never user-supplied filename)
  - `scan_status` = `pending`
  - `uploader_id` = authenticated user ID
  - `file_id` = NULL (filled in Phase B)
  - `external_url` = NULL
  - `mime_type` = declared (to be verified in Phase B)
  - `file_size` = declared
- Return a **signed URL** (using Supabase Storage signed URLs, expiring in 5 minutes) or stream-though-the-backend approach. **Choice**: signed URL — simpler, offloads transfer to Supabase CDN, no bandwidth pressure on backend. The signed URL is returned in the JSON envelope; the frontend uploads directly to Supabase.

**Phase B: Finalize Upload** (`POST /api/v1/library/upload-finalize`)
- Verify:
  - The Supabase object exists (`HEAD` request or `exists`)
  - Real size matches declared size (via `Content-Length` from the upload or `obj.size` from Supabase)
  - Magic-byte sniffing: read first 256 bytes, compare MIME type against declared `mime_type` using `python-magic` or `file` command; if mismatch, set `scan_status = "infected"` (or `failed`) and notify
- Enqueue Celery scan task (see 1.3)
- Update `files` row: set `file_id` = Supabase file ID, keep `scan_status = "pending"` until scan completes

#### 1.3 Malware Scan Pipeline (Celery)
- **Scanner interface** (`app.services.scanner.Scanner`):
  - `scan(bytes) -> dict` returns `{status: "clean" | "infected" | "failed", mime_type, confidence}`
- **ClamAV implementation** (`app.services.scanner.clamav`) — connects to `clamd://host:3310` inside docker-compose; falls back to `python-magic` + heuristic if clamd unavailable.
- **Celery task** (`app/tasks/scan.py`):
  - States: `pending` → `scanning` → `clean` | `infected` | `failed`
  - Retries with exponential backoff (max 3 retries, 2s → 4s → 8s)
  - On `infected`: 
    - Quarantine: move the Supabase object to a `quarantine/` prefix or delete it from the serving bucket
    - Notify uploader and admins via the notification service
    - Write audit entry: `action = "scan.infected"`, `entity_type = "file"`, `entity_id = file_id`
  - On `failed` after retries: set `scan_status = "failed"`, notify admin, audit entry
- **Periodic task** (`app/tasks/health.py` — Celery beat):
  - Re-queue files stuck in `pending` or `scanning` for > 30 minutes
  - Mark as `failed` if no response from ClamAV after 10 minutes
- **Download guard**: `download()` endpoint checks `scan_status`; if not `clean`, returns `403 Forbidden` with error code `SCAN_REQUIRED`.

#### 1.3 Library Resources
- **Model** (`app/models/resource.py`):
  - UUID PK, `uploader_id` FK → users, soft delete
  - `subject_id` FK → subjects (academic hierarchy)
  - `file_id` FK → files (Supabase storage metadata) **or** `external_url` (TEXT, nullable)
  - Exactly one of `file_id` or `external_url` must be set (database constraint or app-level validation)
  - `title`, `description`, `resource_type` from `RESOURCE_TYPES`, `visibility` from `VISIBILITY_CHOICES`
  - `download_count` (atomic increment), `view_count` (atomic increment)
  - `is_published` boolean (default True)
  - `soft_delete` via `SoftDeleteMixin` — on delete, enqueue Supabase object removal task

- **Browse endpoint** (`GET /api/v1/library/resources`):
  - Query params: `department_id`, `program_id`, `semester_id`, `section_id`, `subject_id`, `resource_type`, `visibility`, `q` (full-text search), `sort`, `order`, `page`, `page_size`
  - Full-text search via PostgreSQL `tsvector` + `GIN` index (see migration below)
  - Pagination with atomic count
  - Sortable fields: `title`, `download_count`, `view_count`, `created_at`

- **Download endpoint** (`GET /api/v1/library/resources/{id}/download`):
  - Permission check: Teacher/Admin may download own/all resources; Students may download only their own uploaded resources
  - Increment atomic `download_count` via `SELECT ... FOR UPDATE` or `UPDATE ... RETURNING`
  - Return a **short-lived signed URL** (60 seconds) to the Supabase object
  - Also increment `view_count` on the same visit (or separate `GET /api/v1/library/resources/{id}`)

- **Delete endpoint** (`DELETE /api/v1/library/resources/{id}`):
  - Teacher may delete only their own resources
  - Admin may delete any resource
  - On delete: set `is_active = False` (soft delete), enqueue Celery task to remove Supabase object after a grace period (e.g., 24h)

- **Search**: PostgreSQL `tsvector` on `title || ' ' || description` with `GIN` index. Fallback to `LIKE` on SQLite in unit tests (via environment check).

#### 1.4 Quotas and Abuse Protection
- **Per-user upload rate limit**: 5 uploads per minute (Redis token bucket), enforced in upload-request endpoint
- **Max file size per type**: configurable via `MAX_FILE_SIZE_*` env vars (e.g., `MAX_FILE_SIZE_PDF = 10MB`)
- **Max pending uploads per user**: 3 concurrent uploads; reject new request if user has 3 pending

#### 1.5 Audit
- Log actions: `upload.requested`, `upload.finalized`, `scan.clean`, `scan.infected`, `download`, `delete`, `quarantine`
- Each entry: `action`, `entity_type`, `entity_id`, `request_id`, `ip_address`, `user_agent`, `outcome`, `changes` (before/after)

#### 1.6 Notifications
- Reuse Phase 1 notification service + offline queue
- On new resource published (scan passes): notify all users subscribed to the relevant `section_id`/`subject_id` via the notification service
- On infected file: notify uploader and admins
- On quota exceeded: notify user

### Frontend

#### 2.1 Library Page
- Hierarchical filter sidebar: Department → Program → Semester → Section → Subject (cascading dropdowns or breadcrumb trail)
- Search input with debounce (300ms via `useDebounce` hook)
- Sort select: `title`, `download_count`, `view_count`, `created_at`
- Pagination via TanStack Query (`usePaginatedQuery` pattern), keeps previous data on page change
- Skeleton loaders on initial load and page refetch
- Empty state: "No resources found — ask your teacher to publish notes"
- Error state: network error / search error banner

#### 2.2 Upload Dialog (Permission-Gated)
- Drag-and-drop zone + file picker button
- Client-side validation mirroring server rules (React Hook Form + Zod schema):
  - Extension check
  - MIME type check (client-side only, server validates)
  - Size check against limits
- Progress bar (via `axios.upload` progress event)
- Cancel button
- Visible scan status polling: every 2 seconds, fetch `/api/v1/library/resources/{id}` or via Socket.IO event `scan.status`; display one of: `pending`, `scanning`, `clean`, `infected`
- If infected: show warning banner + " quarantined, not available for download" + "Report to admin" link

#### 2.3 Resource Detail View
- Metadata: title, description, resource type, visibility, uploader name, download/view counts
- Download button: opens signed URL in new tab (60s expiry)
- Admin actions (dropdown): Edit, Delete (confirmation dialog with "This will remove the file from storage after 24h")
- Teacher actions: Edit, Delete (only own resources)

#### 2.4 My Uploads View (Teachers)
- List of resources owned by the teacher
- Each row: title, scan status badge (green/orange/red), download count, view count
- Action buttons: Edit, Delete, Re-scan (trigger new scan task)

#### 2.5 Accessibility
- Dropzone: keyboard-operable (Spacebar to activate, Tab navigation)
- ARIA live regions for upload progress and scan status announcements
- Focus management in dialogs (traps focus, returns focus on close)
- Color contrast meets WCAG AA

### Infrastructure

#### 3.1 Docker & Celery
- Update `docker-compose.yml`:
  - Add `clamav` service (official ClamAV Docker image)
  - Add `celery-beat` service (periodic task runner)
  - Update `redis` config (presence, lockouts)
  - Update `nginx` config for new endpoints (`/api/v1/library/*`)
- Update `backend/Dockerfile`: install `python-clamd`, `python-magic`, `cliquet` (if needed)
- Update `.env.example`:
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`
  - `CLAMAV_HOST`, `CLAMAV_PORT`
  - `UPLOAD_RATE_LIMIT_PER_USER`
  - `MAX_FILE_SIZE_PDF`, `MAX_FILE_SIZE_IMAGE`, etc.
- Update `README.md` deployment guide with new variables

#### 3.2 Database Migration
- Add `fts_resources` migration: `ALTER TABLE resources ADD COLUMN fts tsvector; CREATE INDEX idx_resources_fts ON resources USING GIN (fts);`
- Add `supabase_objects` tracking table (optional, for audit) or rely on Supabase metadata.

### Standards

- **Response envelopes**: canonical success/error envelopes everywhere
- **Layering**: thin controller → service → repository → database; services never import Supabase client directly (use the `StorageBackend` interface)
- **Alembic only**: new migrations for `teacher_allowlist` (Phase 2 already done), `fts_resources`, `scan_jobs`, `quota_usage`
- **No invented endpoints**: every new endpoint documented in `docs/api/README.md` and OpenAPI spec
- **Docs**: `docs/features/LIBRARY.md`, `docs/features/FILE_STORAGE.md`, decision log entry
- **Database guide**: update `docs/03_DATABASE_GUIDE.md` table list

### Security Checklist (must address each)

| Threat | Mitigation |
|---|---|
| Path traversal / filename injection | Never use user filename; always generate random storage key (32-char base64). Sanitize any filename displayed in UI. |
| MIME spoofing | Server-side magic-byte sniffing in scan task; client-supplied MIME only a hint, never trusted. |
| Zip bombs / oversized archives | Enforce `UPLOAD_MAX_SIZE_BYTES` (25MB default) + per-type maxes; reject multipart/uploads with bomb-like structures. |
| SSRF via external URLs | Validate external URLs: `https://` only, resolve via DNS but block `127.0.0.1`, `192.168.x.x`, `10.x.x.x`, `::1`; reject private-IP targets. |
| IDOR on download/delete | Permission checks on every endpoint: Teacher deletes only own; Admin deletes any; Students download only own. Signed URLs time-limited (60s) to prevent leakage. |
| Signed-URL leakage / expiry | Signed URLs expire in 60 seconds; never logged in plain text; use one-time tokens if needed. |
| Race between upload and scan | Phase B finalize validates size + magic bytes *before* enqueuing scan; scan status checked before download. |
| Storage-key guessing | 32-char base64 key (entropy ~192 bits); not guessable; not exposed in URLs longer than needed. |
| XSS via filenames/descriptions | Output-escape all HTML in UI; sanitize filenames before display; use `textContent` over `innerHTML` where possible. |
| DoS through upload flooding | Per-user rate limit (5/min); max concurrent uploads (3); max file size; quarantine infected files immediately. |

## 2. Affected Modules

### Backend
- `app/services/storage.py` — `StorageBackend` ABC + `SupabaseStorage` implementation
- `app/services/scanner.py` — `Scanner` ABC + `ClamAVScanner` + fallback
- `app/tasks/scan.py` — Celery task for malware scanning with state machine + retries
- `app/tasks/health.py` — Celery beat task for re-queuing stuck files
- `app/services/upload.py` — two-phase upload orchestrator (`request`, `finalize`)
- `app/models/resource.py` — Resource model with file/external URL, soft delete, counts
- `app/repositories/resource_repository.py` — browse, filter, search, pagination, ownership checks
- `app.blueprints.library` — `request_upload`, `finalize_upload`, `download`, `delete` blueprints
- `app.utils.validators` — MIME validation, magic-byte sniffing, extension whitelist
- `app.utils.quotas` — rate limit checks, per-user limits
- `app/models/audit_log.py` — extended with `outcome` and `changes` fields (or new column migration)
- `app/services/notification_service.py` — reuse Phase 1; add `notify_upload`, `notify_scan_infected`, `notify_quota_exceeded`

### Frontend
- `frontend/src/pages/library/Library.tsx` — hierarchical filters, search debounce, pagination, skeleton loaders
- `frontend/src/pages/resource/Detail.tsx` — resource metadata, download button, owner/admin actions
- `frontend/src/pages/uploader/UploadDialog.tsx` — drag-and-drop, validation, progress, scan status polling
- `frontend/src/pages/my-uploads/MyUploads.tsx` — teacher view with scan status and download counts
- `frontend/src/hooks/useLibrary.ts` — TanStack Query hooks for browse, search, my uploads
- `frontend/src/hooks/useUpload.ts` — upload flow state, progress, status polling
- `frontend/src/components/ui/` — enhanced Dropzone, StatusBadge, ConfirmDialog components

### Database (Alembic Migrations)
- `alembic/versions/0003_fts_resources.py` — full-text search index on resources
- `alembic/versions/0004_scan_jobs.py` — `scan_jobs` table (task ID, file ID, status, retry count, created_at, finished_at)
- `alembic/versions/0005_quota_usage.py` — `quota_usage` table (user ID, uploads this session, max per session, reset_at)
- `alembic/versions/0006_audit_log_ext.py` — add `outcome`, `ip_address`, `user_agent`, `changes` columns
- `alembic/versions/0007_resource_softdelete.py` — soft delete handling, deferred cleanup task

### Infra
- `docker/docker-compose.yml` — add clamav, celery-beat services
- `backend/Dockerfile` — install clamd, python-magic
- `docker/nginx/campusvault.conf` — new endpoint location blocks
- `.env.example` — new env vars
- `docs/03_DATABASE_GUIDE.md` — table list update

### Docs
- `docs/features/LIBRARY.md` — full feature documentation
- `docs/features/FILE_STORAGE.md` — upload flow, scan sequence diagrams, threat notes
- `docs/decision_log.md` — Supabase storage decision recording
- `docs/api/README.md` — updated endpoint catalog
- `docs/03_DATABASE_GUIDE.md` — table list update

## 3. Database Impact

### New Tables

#### `scan_jobs`
| Column | Type | Constraints |
|---|---|---|
| `id` | UUID PK | |
| `file_id` | UUID FK → files.id | |
| `status` | String enum: `pending`, `scanning`, `clean`, `infected`, `failed` | |
| `clamav_message` | Text | (optional ClamAV output) |
| `retries` | Integer | DEFAULT 0 |
| `max_retries` | Integer | DEFAULT 3 |
| `created_at` | DateTime | DEFAULT now() |
| `finished_at` | DateTime | NULLABLE |

#### `quota_usage`
| Column | Type | Constraints |
|---|---|---|
| `user_id` | UUID FK → users.id | PK |
| `uploads_this_session` | Integer | DEFAULT 0 |
| `max_per_session` | Integer | DEFAULT 5 |
| `reset_at` | DateTime | DEFAULT (now + 1 hour) |

#### `files` table enhancements (via migration or app-level)
- Add `storage_key` column (if not already in 0001) — actually, the existing file_model.py may already have storage concepts. Reuse/examine.

#### Column additions to `resources`
- `fts` → `tsvector` (for full-text search)
- `scan_status` → String enum (if not already present; check existing 0001)

#### Column additions to `audit_log`
- `outcome` → String (success/failure)
- `ip_address` → INET
- `user_agent` → Text
- `changes` → JSONB (before/after state)

#### Indexes
- `idx_resources_fts` GIN on `fts`
- `idx_quota_usage_user_id` on `quota_usage.user_id`
- `idx_scan_jobs_file_id` on `scan_jobs.file_id`
- `idx_resources_uploader_id` on `resources.uploader_id`
- `idx_resources_published_active` partial index: `WHERE is_active = TRUE AND is_published = TRUE`

## 4. Security Impact

### Addressed Threats

| Threat | Mitigation Detail |
|---|---|
| Path traversal / filename injection | Storage key is 32-char random base64, never user-supplied. UI filenames are sanitized (replace `"` with `"`, etc.). |
| MIME spoofing | Server-side magic-byte sniffing in scan task (`python-magic` or `file` cmd). Client-supplied MIME ignored after Phase A. |
| Zip bombs / oversized archives | `UPLOAD_MAX_SIZE_BYTES = 25MB`; per-type maxes (e.g., PDF 10MB, Image 5MB). Multipart parsed with `defusedxml` protection. |
| SSRF via external URLs | URL validation: `https://` only; DNS resolve but block private IPs (`127.0.0.1`, `10.0.0.0/8`, `192.168.x.x`, `::1`); use `urllib.parse` + `socket.gethostbyname_ex` with allowlist. |
| IDOR on download/delete | Download: permission check (`Teacher/Admin may download own/all; Students own only`) + signed URL (60s expiry). Delete: same role checks + last-admin protection. |
| Signed-URL leakage / expiry | Signed URLs generated with `expires_in=60` seconds; never stored long-term; one-time use recommended. |
| Race between upload and scan | Phase B finalize validates size + magic bytes *before* enqueuing scan; `scan_status` checked atomically before download. |
| Storage-key guessing | 32-char base64 (≈192 bits entropy); not exposed in any client-facing URL longer than the signed URL. |
| XSS via filenames/descriptions | All output escaped via React's JSX (`{}` auto-escaping); `dangerouslySetInnerHTML` only with trusted types; filenames displayed in `<code>` or `<span>` with escape. |
| DoS through upload flooding | Per-user rate limit (5/min via Redis token bucket); max concurrent uploads (3); max file size enforced; infected files quarantined immediately; cleanup task removes orphaned objects after 24h. |

## 4. Testing Strategy

### Backend
- **Unit**: file validation (extension, MIME, magic bytes, size); storage-key generation; ownership rules; scan state machine transitions; quota checks.
- **Integration (real PostgreSQL)**: 
  - Upload request → finalize → scan clean → download (verify signed URL, counters increment atomically)
  - Infected file: quarantined, not downloadable, uploader + admins notified, audit entry written
  - Permission + IDOR denials for each role (Student, Teacher, Admin) on all endpoints
  - Full-text search returns correct results; fallback to LIKE on SQLite
  - Counters stay atomic under concurrent downloads (test with `ab` or `hey` with 50 parallel requests)
- **Celery tasks**: tested with fake Scanner (returns `clean`) and fake StorageBackend (no network); retry with backoff behavior; periodic health task re-queues stuck files.

### Frontend
- **Vitest + RTL**: upload dialog validation (extension/MIME/size errors); status display (pending/scanning/clean/infected); library filters (hierarchical, search debounce, sort, pagination); resource detail view; my uploads view.
- **Playwright E2E**: teacher upload → scan clean → student download flow; infected file quarantined and not downloadable; permission denials for each role; search and filter functionality.

### Coverage
- Raise `fail_under` to 75% for this phase (from 70% after Phase 2).

## 5. Definition of Done
- [ ] All backend endpoints implemented (upload-request, upload-finalize, download, delete, browse, search)
- [ ] Malware scan pipeline operational (ClamAV + Celery + state machine)
- [ ] Library CRUD with hierarchy, permissions, soft delete
- [ ] Full-text search working on PostgreSQL, fallback on SQLite
- [ ] Quotas and abuse protection active and tested
- [ ] Audit logging for all state changes
- [ ] Notifications: new resource published, infected file, quota exceeded
- [ ] Frontend: Library page, Upload dialog, Resource detail, My Uploads — all functional and accessible
- [ ] Lint, mypy, tsc, build all clean
- [ ] `docs/features/LIBRARY.md` and `docs/features/FILE_STORAGE.md` fully written
- [ ] `docs/api/README.md` updated with new endpoint catalog
- [ ] `docs/03_DATABASE_GUIDE.md` table list matches actual schema
- [ ] `docs/00_PROJECT_MEMORY.md` — Library moved to Completed
- [ ] Coverage `fail_under` ≥ 75%

## 5. Residual Risks
- ClamAV false positives/negatives; fallback heuristic may miss some malware
- Supabase CDN latency could delay signed URL generation; mitigate with local caching
- External URL SSRF if allowlist not strictly enforced
- Race condition if user deletes resource between scan finalize and download — mitigated by `scan_status` check
- Redis rate-limit store loss on restart — use Redis persistence (RDB/AOF)
- Supabase bucket permissions misconfiguration — fail fast at startup if vars missing

## 5. Phase 4 (Proposed)
- Chat: groups, DMs, real-time events (Socket.IO + Redis adapter), read receipts, presence
- Advanced RBAC: custom role creation, permission inheritance
- Performance: query caching, read replica consideration
- End-to-end encryption for direct messages