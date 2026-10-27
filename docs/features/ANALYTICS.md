# Analytics Feature

## Overview

Analytics in CampusVault are **aggregate-only, privacy-aware, and non-invasive**.
No per-user reading, no chat-content analysis, no file-content analysis, and no
PII in any metrics payload. All metrics are derived from aggregated counters and
summary tables refreshed by a daily Celery beat task.

The documented metrics below are the *only* data collected for analytics purposes.
Any future addition must go through the security and privacy review process.

## Collected Metrics (aggregate only)

| Metric | Description | Source | Retention |
|---|---|---|---|
| `daily_active_users` | Count of distinct user IDs with activity in the last 24h | `users` table (`last_login_at`, activity on resources, messages) | 90 days in `daily_stats`; archived thereafter |
| `resources_published_per_day` | Count of resources with `is_published=True` created that day | `resources` table (`created_at`, `is_published`) | 90 days |
| `messages_sent_per_day` | Count of messages (all types) sent that day | `messages` table (`created_at`) | 90 days |
| `scan_outcomes_distribution` | Percentages of files with `scan_status` = clean/infected/failed | `files` table (`scan_status`, `created_at`) | 90 days |
| `active_groups_count` | Number of groups with `is_active=True` | `groups` table | 90 days |
| `downloads_total` | Cumulative count of resource downloads (sum of `download_count`) | `resources` table (`download_count`) | 90 days |
| `uploads_total` | Cumulative count of resources uploaded (count of resource rows) | `resources` table | 90 days |

## What is NOT Collected (explicitly)

- Per-user reading habits or attention metrics
- Chat message content or file content hashes/contents
- IP addresses in analytics payloads (IP is stored only in `audit_logs.request_context` with proper handling, not in metrics)
- Any personally identifiable information (PII) in metrics payloads
- Per-conversation or per-group message counts beyond the aggregate daily total

## Data Collection & Privacy By Design

1. **Aggregate-only queries**: Every metric is computed via `COUNT(DISTINCT ...)` or `SUM(...)` with `GROUP BY date`. No `SELECT *` or per-entity rows are returned via any API.
2. **No message/content storage in metrics**: The `messages_sent_per_day` counter only increments on `INSERT` of new `Message` rows; the content itself is never read or hashed.
3. **Privacy review**: Any proposed new metric must pass a privacy review (see `docs/06_SECURITY_GUIDE.md`) before deployment.
4. **Data retention**: The `daily_stats` table retains 90 days of data. A Celery beat task (see `app/tasks/daily_stats.py`) runs at 02:00 UTC daily and also archives data older than `RETENTION_DAYS` (configurable, default 90) into `daily_stats_archive` or cold storage (S3/Glacier).
5. **Export caution**: The audit log CSV export (admin feature) is a separate, audited endpoint. Analytics data exports must follow the same append-only guarantee and may not rewrite or delete rows.

## API Endpoints (internal/protected)

| Endpoint | Auth | Description |
|---|---|---|
| `GET /api/v1/admin/platform-stats` | Admin | Returns the latest aggregated stats from `daily_stats` (or computes from raw if table stale) |
| `GET /api/v1/dashboard/stats` | Any authenticated user | Returns a subset of safe stats (user counts by role aggregated, resource totals, scan outcomes) — intentionally limited to prevent information leakage |

## Rollback / Restore Procedure

1. **If `daily_stats` table is corrupted**: truncate and re-run `refresh_daily_stats` Celery task from raw data (`users`, `resources`, `messages`, `files`).
2. **If archive is needed back**: restore from cold storage (S3/Glacier) into a staging database, validate row counts against the original source, then promote the staging `daily_stats` partition back to production.
3. **Retention policy**: `RETENTION_DAYS` environment variable (default 90). Data older than this is considered for archival; the Celery task includes logic to move old rows to `daily_stats_archive` (a separate table not yet created in this phase, documented for future work).

## Privacy Guarantee

- No endpoint returns per-user or per-entity data under the guise of analytics.
- All metrics are **computed, not stored per entity** (except the `daily_stats` summary table, which is itself append-only and refreshed daily).
- The system is designed so that **no message content, file content, or PII** ever appears in a metrics payload or log line visible to unauthorized viewers.

## Related Docs

- `docs/features/CHAT.md` — message lifecycle, no content in analytics
- `docs/features/FILE_STORAGE.md` — scan outcomes, file lifecycle
- `docs/06_SECURITY_GUIDE.md` — privacy review process
- `docs/10_TESTING_GUIDE.md` — coverage and test requirements