# Decision Log

## Supabase Storage Integration (Phase 3)

- **Decision**: Use Supabase Storage as the object store, accessed through a `StorageBackend` interface so the service layer never imports the Supabase client at module level.
- **Rationale**: 
  - Keeps the backend agnostic — a `LocalFileStorage` implementation exists for tests/local dev.
  - Fail‑fast at startup if `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET` are missing (raises `ConfigError`).
  - Signed URLs (5‑min expiry) offload transfer to the Supabase CDN, avoiding bandwidth pressure on the Flask process.
- **Implementation**: 
  - `app/services/storage.py` — `StorageBackend` Protocol + `SupabaseStorage` + `LocalFileStorage`.
  - Lazy import of `supabase` inside `SupabaseStorage._get_client()`.
  - Registered in the app factory (`app/factory.py`) based on environment variables.
- **Env vars added to `.env.example`**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`.
- **Alternate considered**: local‑file storage for development only; not persisted in production.

## ClamAV Scanner (Phase 3)

- **Decision**: Plug‑in scanner ABC (`app/services/scanner.py`) with a `ClamAVScanner` implementation that connects to a `clamd` daemon, plus a `NoOpScanner` fallback for when AV is unavailable.
- **Rationale**: 
  - Keeps the scan pipeline testable without a running ClamAV instance.
  - Allows swapping in a commercial AV or heuristic solution later without touching the service layer.
  - Transient failures are retried with exponential backoff (1s, 2s, 4s); after 3 attempts the file is marked ``failed`` and the uploader/admins are notified.
- **Implementation**: 
  - `app/services/scanner.py` — `Scanner` ABC, `ClamAVScanner`, `NoOpScanner`.
  - `app/tasks/scan.py` — Celery task with retry logic + infected‑file handling (quarantine + notification).
  - `app/tasks/health.py` — Celery beat task that re‑queues files stuck in ``pending``/``scanning`` for >30 minutes.

## Two‑Phase Upload (Phase 3)

- **Decision**: Split the upload flow into a *request* phase (validate + create ``files`` row + signed URL) and a *finalize* phase (verify object, run scanner, update state).
- **Rationale**: 
  - The frontend can start the upload immediately without waiting for scanner results.
  - The scanner runs on the backend after the full file has been received, ensuring magic‑byte verification.
  - Clear separation of concerns: validation → storage → scanning → state transition.
- **Endpoints**: 
  - `POST /api/v1/library/upload-request` (Phase A)
  - `POST /api/v1/library/upload-finalize` (Phase B)

## Full‑Text Search (Phase 3)

- **Decision**: PostgreSQL `tsvector` + `GIN` index on `resources(fts)`, with a fallback to `LIKE` on SQLite for unit tests.
- **Rationale**: 
  - Provides fast free‑text search on `title` and `description`.
  - The migration is idempotent and can be rolled back.
  - Fallback keeps the test suite running without a PostgreSQL instance.

## Quota & Abuse Protection (Phase 3)

- **Decision**: Per‑user rate limit (5 uploads/minute, Redis token bucket), per‑type max file size, max 3 concurrent pending uploads per user.
- **Rationale**: 
  - Prevents a single user from flooding the system with uploads.
  - Rate limits are enforced in the upload‑request endpoint and tracked in the `quota_usage` table.
  - Max file sizes are configurable via env vars (`MAX_FILE_SIZE_PDF`, `MAX_FILE_SIZE_IMAGE`, etc.).

## Audit Log Enhancement (Phase 3)

- **Decision**: Add `outcome`, `ip_address`, `user_agent`, `changes` (JSONB) columns to the `audit_log` table.
- **Rationale**: 
  - Captures the full lifecycle of uploads, scans, downloads, and deletions.
  - `changes` stores a before/after JSON object useful for incident investigation.
  - `ip_address` and `user_agent` help with IDOR and DoS investigations.

## Celery + Beat (Phase 3)

- **Decision**: Add a dedicated `celery-beat` service to the Docker Compose file for the periodic health task that re‑queues stuck scan jobs.
- **Rationale**: 
  - Decouples the periodic logic from the worker process.
  - Ensures that files stuck in `pending` or `scanning` for >30 minutes are re‑queued automatically.
  - The beat schedule is configured in the Celery config (10‑minute interval).

## Library Hierarchy & Soft Delete (Phase 3)

- **Decision**: Resources are tied to the academic hierarchy (Department → Program → Semester → Section → Subject) and have exactly one of `file_id` or `external_url`. Soft delete via `is_active` flag; the underlying Supabase object is removed by a deferred Celery task (24h grace period).
- **Rationale**: 
  - Mirrors the real‑world academic structure.
  - Soft delete avoids data loss and allows admin recovery.
  - Deferred cleanup prevents accidental permanent deletion while a resource is still "in grace period".

## Chat & Real‑Time (Phase 4 - proposed)

- **Decision**: Deferred to Phase 4; will build on the existing Socket.IO + Redis adapter from Phase 1, adding group channels (`group_<id>`), direct messages (`dm_<id>`), read receipts, and presence.
- **Rationale**: 
  - Keeps Phase 3 focused on storage & RBAC.
  - Allows incremental delivery of real‑time features without scope creep.

## Frontend Framework Choices (Phase 3)

- **Decision**: TanStack Query for server‑state management, React Hook Form + Zod for form validation, Tailwind CSS for styling, and custom Dropzone component for drag‑and‑drop uploads.
- **Rationale**: 
  - TanStack Query provides automatic caching, refetching, and stale‑while‑revalidate behaviour.
  - React Hook Form + Zod gives strong type‑safe validation with minimal boilerplate.
  - Tailwind CSS enables rapid UI development with consistent design tokens.
  - Custom Dropzone provides accessible drag‑and‑drop with ARIA live regions.

## Documentation Structure (Phase 3)

- **Decision**: Create `docs/features/LIBRARY.md`, `docs/features/FILE_STORAGE.md`, and update `docs/03_DATABASE_GUIDE.md`.
- **Rationale**: 
  - Keeps all feature‑specific docs in one place under `docs/features/`.
  - The decision log (`docs/decision_log.md`) captures architectural choices for future reference.
  - The API spec (`docs/api/README.md`) is updated for every new endpoint, maintaining the "single source of truth" principle.

---
*This file was last updated during Phase 3 implementation.  Each entry corresponds to a deliberate architectural decision that was discussed and approved before implementation began.*