# Phase 5: Admin Dashboard, Analytics, Search Polish and Production Hardening — Plan

## Requirements Summary

### A. Admin Dashboard (backend + frontend)

#### 1. Overview Stats Endpoint & Page
- **Total users by role**: Count users grouped by role (Student, Teacher, Admin)
- **Active users (7/30 days)**: Count distinct users with activity in last 7/30 days
  - Efficient: use `SELECT COUNT(DISTINCT user_id) FROM ... WHERE last_activity >= now() - interval '7 days'`
  - Materialized view or Celery-beat-refreshed summary table (see below)
- **Resources by type/department**: Breakdown of resources by `resource_type` and `department_id`
  - Pre-computed summary table refreshed every hour by Celery beat
- **Storage used**: Total bytes per bucket, per user quota usage
- **Uploads and downloads over time**: Time-series data (daily counts for last 30 days)
  - Summary tables refreshed nightly
- **Scan outcomes (clean/infected/failed)**: Count of files per scan_status
- **Chat activity**: Messages per day, active groups count
- **Pending items needing attention**: 
  - Stuck scans (pending/scanning > 30 min, requeued by health task)
  - Failed email deliveries (notification preferences + retry queue)

**Efficient computation justification**:
- All aggregates use indexed columns (`created_at`, `is_active`, `scan_status`, `conversation_type`)
- Summary tables (materialized views or dedicated tables refreshed by Celery beat) avoid N+1 / full-table scans on every request
- Choose: dedicated summary tables refreshed every hour by Celery beat (more flexible than PostgreSQL materialized views for concurrent writes); the Database Guide's "future improvements" item suggests this pattern
- Per-request queries fall back to indexed column scans when summary tables are stale (within 1-hour window), with a `stale_at` timestamp for transparency

#### 2. Management Screens
- **Users**: Search/filter by role/status, role assignment, deactivate/reactivate
  - Deactivate: soft delete (`is_active=False`), prevent self-deactivation, audit log
  - Reactivate: restore `is_active=True`
  - Role assignment: assign/revoke Student/Teacher/Admin roles via JWT-protected API
- **Academic structure**: CRUD for department → program → semester → section → subject
  - Referential checks: cannot delete department with existing programs/semesters (RESTRICT)
  - Soft delete on all academic tables (already have `is_active` + `deleted_at`)
  - Hierarchy validation: program belongs to department, semester to program, etc.
- **Groups**: View, archive, reassign owner
  - Archive: set `is_active=False` on group + conversation; prevent if still has participants
  - Reassign owner: same as Phase 4 transfer_ownership flow
- **Resources**: Moderation: unpublish/delete, view scan status
  - Unpublish: set `is_published=False`
  - Delete: soft delete with audit; underlying Supabase object moved to quarantine after 24h grace period
  - Scan status display: clean/infected/failed + quarantine button
- **Teacher allowlist (Phase 2)**: View, add, remove, approve emails
  - Admins can manage the teacher allowlist table

#### 3. Audit Log Viewer
- **Filter by**: actor (UUID), action (string), target (entity_type + entity_id), date range, request_id
- **Keyset pagination**: cursor on `created_at` + `id`, newest-first or oldest-first
- **Export to CSV**: streamed chunks, admin-only, the export action itself audited (actor=system, action="audit.export.csv")
- **Append-only guarantee**: No update/delete path in code or DB permissions; database-level revoke on UPDATE/DELETE on audit_logs table
- **UI**: Table with sortable columns, filter chips, date picker, export button, "no results" state

#### 4. Moderation Queue
- **Infected-file quarantine list**: Files with `scan_status='infected'` not yet dealt with
- **Actions per file**:
  - **Confirm delete**: Permanently remove from Supabase + set `is_active=False` on resource + audit with justification
  - **Restore for review**: If false positive, move back to active, re-scan optional, add admin note in audit
- **UI**: Table with file info, scan status, quarantine duration, action buttons, justification textarea

#### 5. System Settings (minimal, env-driven)
- **Upload size limits per type**: `MAX_FILE_SIZE_PDF`, `MAX_FILE_SIZE_IMAGE`, etc. (already in config)
- **Message edit window**: `MESSAGE_EDIT_WINDOW_MINUTES` (already in config, 15 min)
- **OTP settings**: Resend interval, expiry (already in config)
- **Storage**: Stored in validated settings table with audit trail OR kept as env-driven config
  - Decision: keep as env-driven config per docs; the "settings table" addition listed as future work if scope too large
  - Current approach: env vars + runtime config (already implemented); no new DB table needed

### B. Analytics (lightweight, privacy-aware)

#### 1. Aggregated, non-invasive metrics only
- **What IS collected** (documented in `docs/features/ANALYTICS.md`):
  - Daily active user count (distinct user_ids with activity in last 24h)
  - Resources published per day
  - Messages sent per day (aggregate, no content)
  - Scan outcomes distribution (clean/infected/failed percentages)
  - Active group count
  - Download count total (sum)
  - Upload count total (sum)
- **What is NOT collected** (explicitly):
  - Per-user reading habits
  - Chat message content or file content
  - IP addresses in analytics (only in audit logs with proper handling)
  - Any PII in metrics payloads
- **Privacy by design**: All metrics are aggregate-only; no per-entity row exposed via API endpoints

#### 2. Summary tables / materialized views with refresh schedule
- **Tables**:
  - `daily_stats` (date, users_active, resources_published, messages_sent, scans_clean, scans_infected, scans_failed, downloads_total, uploads_total)
  - `chat_activity` (date, conversation_type, messages_count, active_groups)
- **Refresh schedule**: Celery beat task daily at 02:00 UTC, recomputes from raw tables
- **Retention/archival strategy** (Database Guide):
  - Keep 90 days in production `daily_stats`
  - Archive to cold storage/partition beyond 90 days
  - Retain full `audit_logs` per compliance (7 years or as required)
- **Rollback/restore procedure**:
  - If daily_stats data is corrupted: truncate and re-run Celery task from raw data
  - If archive is needed back: restore from cold storage (S3/Glacier) into staging DB, validate row counts, promote back

### C. Search Polish

#### 1. Unified search endpoint across resources (and groups user may see)
- **Endpoint**: `GET /api/v1/library/search?q={query}&filters={...}`
- **FTS**: PostgreSQL `tsvector` + `gin` index on `resources(fts)` (Phase 3)
- **Ranking**: `ts_rank` with query weight; TF-IDF boost for title match over description
- **Highlighting snippets**: HTML-escaped `ts_headline` or fallback to first 100 chars with `...`
- **Filters**: `resource_type`, `visibility`, `department_id`, `program_id`, `semester_id`, `section_id`, `subject_id`, `published` (boolean)
- **Typo tolerance**: `pg_trgm` `similarity()` > 0.3 for LIKE fallback on SQLite; on PostgreSQL use `%.3` operator
- **Permission-aware results**: 
  - Filter by user's visible departments/programs/semesters/sections/subjects via their role/group memberships
  - Never leak resources or groups user cannot access (enforce in repository layer)
  - Student sees only their department's resources + public resources; Teacher sees their groups + department; Admin sees all
- **Response envelope**: Canonical success with `items`, `total`, `page`, `page_size`, plus `highlight` per item

#### 2. Frontend: Global search bar
- **Debounce**: 300ms
- **Keyboard shortcut**: `Cmd/Ctrl + K` focus search input
- **Grouped results**: Resources § Groups (labeled, separated)
- **Recent searches**: Stored client-side in `localStorage`, max 10, clearable icon
- **Empty state**: "No results found. Try different keywords or check filters."
- **Error state**: "Search temporarily unavailable. Please try again later."
- **Accessibility**: ARIA-autocomplete, ESC to close, focus trap

### D. Production Hardening

#### 1. Observability
- **Structured JSON logs** with `request_id` propagation into Celery tasks and socket events
  - Logger: `logger.json({level, message, request_id, correlation_id, component, ...})`
- **Error tracking** integration behind interface (Sentry, configured via `SENTRY_DSN` env var, disabled in dev `APP_ENV=development`)
- **Health endpoints** extended with dependency checks:
  - `/api/v1/health/db` → PostgreSQL reachable
  - `/api/v1/health/redis` → Redis reachable + queue depth
  - `/api/v1/health/storage` → Supabase bucket accessible
  - `/api/v1/health/scanner` → ClamAV daemon responsive (ping)
  - `/api/v1/health/celery` → Worker count, queue depth, ready tasks
- **Prometheus-style metrics endpoint** (internal access only, `/metrics` behind internal LB or IP allowlist):
  - `http_requests_total` (counter, by method+path+status)
  - `http_request_duration_seconds` (histogram, by method+path)
  - `socket_connections_active` (gauge)
  - `celery_queue_depth_<name>` (gauge per queue)
  - `scan_duration_seconds` (histogram)
  - `error_rate` = `http_requests_total` with 5xx / total
- **Alert thresholds** documented: e.g., p95 latency > 500ms, error_rate > 2%, queue depth > 1000, scan failure rate > 5% over 1h

#### 2. Security review pass
- **Dependency audit**: `pip-audit` and `npm audit` in CI, failing on high severity
- **Secret scanning** in CI (detect `SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET_KEY` in repo)
- **CSP review**: 
  - Swagger UI route (`/api/v1/docs`) CSP: `default-src 'self' https://cdn.jsdelivr.net; script-src 'self' 'unsafe-inline';` 
  - Supabase/storage origins in `img-src` and `connect-src`
  - No inline styles in admin HTML beyond design tokens
- **CORS allowlist per environment**: Development `http://localhost:5173`, staging `https://staging.campusvault.edu`, production `https://campusvault.edu`
- **Cookie flags**: `Secure`, `HttpOnly`, `SameSite=Lax` on JWT refresh tokens; `SameSite=Strict` on session if used
- **Security header verification test**: HSTS, X-Frame-Options, X-Content-Type-Options, Content-Security-Policy
- **Rate-limit coverage report**: List every route + its limit; verify no route is unprotected
- **Automated test**: Enumerate all registered Flask routes and assert `@ensure_authenticated` or `@permission_required` or explicit entry in `PUBLIC_ALLOWLIST` (blueprint-level)

#### 3. Performance review (docs/20_PERFORMANCE_GUIDE.md)
- **EXPLAIN every hot query**:
  - `browse` resources: `ix_resources_department_program_semester_section_subject_visibility_is_active`
  - `search` resources: `idx_resources_fts` (GIN) + `resources_fts_query` pattern
  - `history` messages: `ix_messages_conversation_created` (composite)
  - `conversation list`: `ix_conversations_type_last_msg` + participant indexes
  - `dashboard stats`: summary tables (see above)
- **Add/adjust indexes** through Alembic as needed (new migrations)
- **Cache read-heavy aggregates** in Redis with explicit invalidation or TTL (1 hour)
  - Key format: `stats:dashboard:v1` with TTL=3600, invalidated on: resource create/delete, user activate/deactivate, message send, scan complete
- **Frontend bundle analysis** with route-level code splitting verified
  - Routes: `/`, `/login`, `/library`, `/chat`, `/admin`
  - Dynamic imports for heavy pages
- **Image/asset optimization**: WebP/AVIF conversion, responsive images, CDN
- **Lighthouse > 90** on: Login, Library, Chat, Admin pages (mobile + desktop)
- **API p95 < 300ms** on seeded dataset (record numbers in docs)

#### 4. Resilience
- **Graceful shutdown** for Gunicorn/eventlet workers (SIGTERM handler, wait for active requests, cancel pending)
- **Celery retry and dead-letter handling**:
  - `max_retries=3`, `default_retry_delay=2` (exponential backoff 1s, 2s, 4s)
  - Dead-letter queue on exhaust; alert on repeated DLQ
- **Idempotent tasks**: scan result update, daily stats refresh (use `INSERT ... ON CONFLICT DO NOTHING` or `UPSERT`)
- **DB connection pool tuning** (SQLAlchemy `pool_size=20`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=280`)
- **Redis reconnect behavior** (SocketIO message_queue reconnects automatically; custom handler for presence TTL renewal)
- **Timeouts on all outbound calls**:
  - Supabase: 10s connect, 30s operation
  - SMTP: 5s connect, 15s send
  - ClamAV scanner: 5s timeout per scan
- **Behavior when Redis unavailable**: 
  - Socket.IO degrades: events not broadcast across workers; fallback to long-polling or accept single-worker mode
  - Rate limits fall back to in-memory (less accurate but functional)
  - Presence: TTL expiry leads to users marked offline after 24h (already designed)
  - Justify: acceptable for short-term outage; admin-visible warning
- **Behavior when scanner unavailable**: 
  - Files marked `scan_status='failed'`; uploader notified; admin can re-scan manually
  - Quarantine not triggered; file remains available until admin acts
  - Justify: false negative risk > immediate block; human in the loop

#### 5. Backup and recovery
- **Documented and scripted backup verification** for:
  - Supabase PostgreSQL: `pg_dump` daily, verify row counts, store in S3/Glacier
  - Supabase Storage: bucket backup script (list all objects + metadata, store manifest)
- **Restore drill checklist**:
  1. Spin up fresh Supabase project
  2. Restore PostgreSQL dump
  3. Restore Storage bucket from manifest
  4. Re-apply Alembic migrations to latest
  5. Seed with test data (10 users, 5 groups, 20 resources, 50 messages)
  6. Validate: login, upload, scan, download, chat, audit
  7. Compare row counts vs pre-disaster backup
- **Recorded RPO/RTO target**: RPO = 1 hour (last hourly stats summary); RTO = 4 hours (restore + validate)

#### 6. Deployment
- **Finalize docker/docker-compose.yml** (dev) and production reference (Render/VPS instructions)
  - Dev: `docker-compose.yml` with `api`, `redis`, `celery-worker`, `celery-beat`, `nginx`, `supabase` (via official images or local emulation)
  - Production: separate compose or Render/VPS docs with separate DB/Redis instances, TLS, resource limits
- **Nginx hardening**:
  - TLS 1.3 only, strong cipher suite, HSTS 1 year, preload
  - Request size limits (`client_max_body_size 50M`)
  - WebSocket stickiness: either `ip_hash` (simple) or Redis adapter (preferred, already configured)
  - Gzip on, level 6, exclude `text/html` for API responses (already gzip)
- **Environment matrix**: Development, Staging, Production with complete `.env.example` and startup validation script that fails fast on missing/weak config
  - Validation checks: `SECRET_KEY` length ≥ 32, `JWT_SECRET_KEY` length ≥ 64, `SUPABASE_URL` present, `CLAMAV_HOST` reachable, `REDIS_URL` present, `DEBUG` not true in production
- **Zero-downtime migration guidance**:
  - Expand: add new column, default, deploy, populate, then alter not-null
  - Contract: remove column after ensuring no code references, deploy, then drop
  - Data migrations: Alembic + Celery one-shot task, wrapped in transaction
- **Rollback runbook**: Steps to revert code + DB to previous version, verify health checks, re-apply old .env if needed

#### 7. CI/CD
- **GitHub Actions pipeline** per docs/21_DEVOPS_GUIDE.md:
  - `install`: `pip install -e .`, `npm ci`
  - `lint`: `flake8`, `black --check`, `eslint`
  - `type check`: `mypy` backend, `tsc` frontend
  - `test`: `pytest -q` with coverage report, fail if `< 80%`
  - `build`: `vite build`
  - `security scan`: `pip-audit --format=table`, `npm audit --audit-level=high`
  - `deploy to staging`: `flyctl deploy --remote-staging` or Docker compose push
  - `smoke test`: Script hitting `/health`, `/api/v1/auth/me`, `/api/v1/library/resources`, `/api/v1/chat/messages`
  - `manual approval`: GitHub environment `production` requires review
  - `production deploy`: `flyctl deploy` or Docker compose with `--release`
  - `health check`: POST `/api/v1/health/db`, `/api/v1/health/redis`, etc.
- **Caching**: pip cache, npm cache, Docker layer caching
- **Coverage gate**: at least 80% enforced (already set in pyproject.toml)
- **Required status checks** documented for branch protection on `main` and `develop`

### E. Release Candidate

#### 1. Run full docs/23_CHECKLISTS.md
- Before merging: verify each item
- Before deployment: re-verify
- Production readiness: final sign-off

#### 2. Prepare v1.0.0-rc.1 per docs/22_RELEASE_GUIDE.md
- **CHANGELOG.md**: Unreleased section + Phase 1-5 entries
- **Version bump**: `VERSION=1.0.0-rc.1` in `app/constants.py` and `setup.cfg/pyproject.toml`
- **Migration review**: All pending Alembic migrations reviewed and applied to staging
- **Release notes**: Summary of new features (Admin Dashboard, Search polish, Hardening)
- **Smoke test script for staging**: Bash/Python script hitting key endpoints
- **Rollback plan**: Documented steps (see above)

#### 3. Update every doc to match real system
- `docs/00_PROJECT_MEMORY.md`: All phases complete, status: Release Candidate
- `docs/03_DATABASE_GUIDE.md`: Final schema (add summary tables, audit extensions)
- `docs/api` and OpenAPI spec: All new endpoints documented
- **Root README**: Accurate setup, architecture overview, links to docs, phases status
- **docs/RUNBOOK.md**: On-call basics: common failures, how to check logs, restart workers, handle stuck scan queue, Redis outage
- **docs/DECISIONS.md**: Every library and architectural decision across phases

## Security Checklist (address each explicitly)

| # | Threat | Mitigation |
|---|---|---|
| 1 | Admin privilege escalation | All admin endpoints guarded by `assert_admin()` + role JWT claim; route-level decorator; automated test enumerates all routes |
| 2 | IDOR on admin endpoints | Every admin endpoint validates actor against target resource (user_id, group_id, resource_id); `assert_admin` + membership check |
| 3 | CSV export injection (formula injection in cells) | Export encodes special characters (`\n` → `\\n`, `"` → `\"`), no formulas allowed, add `='<value>'` guard cell; use Python `csv` module with `quotechar` and `quoting=csv.QUOTE_MINIMAL` |
| 4 | Audit log tampering | DB permissions: revoke UPDATE/DELETE on `audit_logs` table; code has no write path; every export action audited |
| 5 | Metrics/health endpoint exposure | `/metrics` behind internal LB/IP allowlist; `/health` basic checks only; no sensitive data in responses |
| 6 | Search result permission leaks | Repository-layer permission filter on every search result; never return resources/groups user cannot access; snippet HTML-escaped; no raw content in API |
| 7 | Snippet XSS | `html.escape()` on all headline/text snippets before sending to frontend; Content-Security-Policy restricts inline scripts |
| 8 | Analytics privacy leakage | Aggregate-only metrics; no per-user data in any metrics API; privacy policy documented in `docs/features/ANALYTICS.md` |
| 9 | Secrets in logs or error tracking payloads | Structured JSON logs omit secrets; Sentry `attachments` stripped of env vars; `SENTRY_DSN` not committed; `filter[extra]` sanitization |
| 10 | Dependency vulnerabilities | `pip-audit` + `npm audit` in CI, fail on `high`; Dependabot auto-merged PRs for critical updates |
| 11 | Misconfigured CORS/CSP | CORS allowlist per environment (dev/staging/prod); CSP header set per environment; automated CI test checks both |
| 12 | Denial of service through expensive admin queries/exports | Query timeouts (30s default, 60s admin); export async with size limit (5000 rows); browse/search pagination hard caps (max 100 per page); Redis cache with TTL; rate limits on all admin endpoints |

## Testing

### Unit
- Aggregation logic (daily stats, resource counts, scan outcomes)
- Settings validation script (env var ranges, secret strength)
- Search ranking and permission filtering (user A sees only their permitted resources)
- CSV escaping (special chars, formula injection prevention)
- Config validation script (fails fast on missing/weak config)

### Integration (real PostgreSQL + Redis)
- Admin endpoints per role (allow/deny matrix): superadmin sees all, admin sees their org, teacher sees their dept, student sees public only
- Audit viewer filters and append-only guarantee (try UPDATE/DELETE, should fail)
- Moderation queue actions (confirm delete, restore, with justification audit)
- Search permission isolation (user A never sees user B's private resources or groups)
- Summary table refresh (Celery task produces correct daily_stats rows)
- Health and metrics endpoints (all dependency checks return 200 OK when deps up, 503 when down)
- **Automated test**: Enumerate all registered Flask routes, assert `@ensure_authenticated` or `@permission_required` or explicit `PUBLIC_ALLOWLIST` entry

### Frontend
- Vitest + RTL for admin tables and filters, search bar, permission gating
- Playwright E2E for admin flow: assign role → deactivate user → review quarantine queue → export audit CSV → verify audit row
- Full smoke path (login, upload, scan, download, chat) against staging-like compose stack

### Load and Soak
- Repeatable script exercising browse, search, chat send and downloads at documented concurrency
- Record results in `docs/PERFORMANCE_RESULTS.md`
- Target: p95 latency under 300ms for API, Redis under 80% max memory, Gunicorn workers stable at N=4 under load

### Coverage Gate
- At least 80% on both backend and frontend (already configured)

## Definition of Done
- Tests pass, lint/mypy/tsc/build clean
- Security scans clean (or exceptions documented)
- Docs and API spec updated
- Checklists in `docs/23_CHECKLISTS.md` all verified
- Performance targets met or exceptions documented
- Responsive and accessible UI verified (keyboard navigation and screen-reader labels on admin tables and search)
- No regressions
- Release candidate tagged v1.0.0-rc.1

## Output
Give the plan, then the changed/new files grouped by backend, migrations, frontend, infra/CI, tests and docs. Finish with: the verification table, the completed checklist report, performance and load numbers, design decisions, residual risks and known limitations, the staging deploy and rollback steps, and a proposed post-release roadmap (e.g. mobile app, notification preferences, moderation tools, analytics expansion, internationalization).