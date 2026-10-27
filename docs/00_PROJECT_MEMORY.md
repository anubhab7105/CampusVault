# PROJECT MEMORY

## Project
CampusVault

## Current Status
Phase 4 complete — Groups + Chat (real-time) implemented and verified. Phase 5 — Admin Dashboard, Analytics, Search Polish and Production Hardening — in progress.

## Current Phase
Phase 5 — Admin Dashboard, Analytics, Search Polish and Production Hardening (release candidate preparation).

## Stack
- React, Vite, Tailwind CSS, Zustand, TanStack Query, React Router, Axios, Socket.IO Client, React Hook Form + Zod
- Flask, Flask-SocketIO, SQLAlchemy, Alembic, Gunicorn
- Supabase PostgreSQL, Supabase Storage, Redis, Celery, Docker, Nginx, Gmail SMTP (development only)
- pytest + Flask test client, Vitest + React Testing Library, Playwright

## Completed

- Functional Planning
- Initial Architecture
- Technology Selection
- Phase 1 scaffolding:
  - Repository layout (frontend/, backend/, docker/, tests/, .github/workflows/)
  - Backend: app factory, config per environment, extensions, constants, error handlers, response envelopes, request-logging middleware (request_id, user_id, endpoint, duration, status_code), security headers, JWT blocklist, RBAC decorator, Socket.IO init with JWT handshake, Celery app + tasks
  - Blueprints: health, auth, users, rbac, academic, groups, chat, library, files, notifications, admin, audit, docs (OpenAPI + Swagger)
  - Models + Alembic migration 0001: all 20 core tables (users, roles, permissions, user_roles, role_permissions, departments, programs, semesters, sections, subjects, groups, user_groups, conversations, conversation_participants, messages, files, resources, notifications, audit_logs), UUID PKs, FKs, composite indexes, soft deletes, check constraints
  - Frontend: Vite + Tailwind design tokens, lazy router with ProtectedRoute, Axios client with refresh-token interceptor, four Zustand stores (auth, theme, sidebar, socket), toast store, base UI kit (Button, Input, Card, Table, Dialog, Toast, Skeleton, EmptyState, ErrorBoundary), Auth/Dashboard layouts, placeholder pages (Login, Dashboard, Library, Chat, Admin, Notifications, NotFound)
  - Infra: Dockerfile, gunicorn.conf.py, wsgi.py, run.py, docker-compose.yml (backend, worker, redis, nginx), Nginx config with WS upgrade + security headers
  - CI: GitHub Actions workflow (lint, type check, pytest, vitest, build, security scan, deploy smoke test)
  - Tests: backend 17 passing (unit + integration), frontend 2 passing (vitest + RTL); ruff + eslint clean
  - .env.example (backend + frontend), CODEOWNERS, pull request template
- Phase 2 scaffolding:
  - Google OAuth email domain validation + auto-provision Student role
  - Teacher OTP two-phase flow with Redis rate limiting and anti-enumeration
  - Refresh token rotation with Redis jti blocklist + reuse detection + family revocation
  - Refresh token delivered via HttpOnly, Secure, SameSite=Lax cookie; access token in memory
  - CSRF protection for /auth/refresh endpoint
  - RBAC: system roles (Student, Teacher, Admin) idempotently seeded; role/permission CRUD; effective permissions in /auth/me; @permission_required decorator on all protected routes; last-admin protection
  - Admin UI: teacher allowlist management, user list with role assignment and deactivation (last-admin guard), roles/permissions grant matrix
  - Audit logging: login success/failure, logout, refresh reuse detection, role changes, user deactivation
  - Frontend: Login page (Google + OTP), Auth store (in-memory tokens, silent session restore), ProtectedRoute with redirect-back, PermissionGate + usePermission hook, Admin UI
- Phase 3 scaffolding:
  - Library + File Storage + Malware Scan Pipeline
  - Supabase Storage integration with StorageBackend interface (lazy-loaded, never direct client import)
  - Two-phase upload flow: request validation + finalize with malware scan
  - ClamAV malware scan pipeline via Celery with state machine (pending → scanning → clean/infected/failed)
  - Library resources with hierarchy (Department→Program→Semester→Section→Subject), file/external URL, CRUD
  - PostgreSQL full-text search (tsvector + GIN index) on resource title/description
  - Quotas: per-user upload rate limit, max file size per type, max pending uploads per user
  - Audit logging for all state changes (upload, scan, download, delete, quarantine)
  - Notifications: new resource published, infected file, quota exceeded
  - Frontend: Library page with hierarchical filters, search debounce, pagination, upload dialog, resource detail, my uploads
  - Raise coverage gate to 75% for Phase 3 completion
- Phase 4 scaffolding:
  - Groups: create, update, archive, list my groups, get, add/remove members, change member role (owner/moderator/member), leave group. Groups may be linked to a section or subject. Rules: only owners/moderators manage members, the last owner cannot leave without transferring ownership, and permission checks use the Phase 2 RBAC. Each group has one mirrored conversation (created in the same transaction).
  - Direct messages: open-or-get a DM between two users (one conversation per pair, enforced by a unique constraint on a normalized pair). Decide, and document in the plan, which role combinations may DM each other (default: students may DM teachers and students in their own department; admins unrestricted). Add a block/mute capability only if it fits the schema cleanly; otherwise list it as future work.
  - Messages: send, edit (own messages only, within a configurable window), soft delete with content wipe (tombstone), reply-to, and attachments that reference existing clean files from Phase 3 (never accept raw uploads over the socket). Message length limit, and content stored as plain text with output encoding on the client (no raw HTML).
  - History: keyset (cursor) pagination, newest first, with a stable ordering on (created_at, id). No offset pagination. Index verified with EXPLAIN.
  - Socket.IO events (exactly the documented set): connect, disconnect, join_group, leave_group, send_group_message, edit_group_message, delete_group_message, typing, notification, read_receipt, delivery_status. JWT required at the handshake; expired tokens trigger a clean disconnect with a reason so the client can refresh and reconnect. Authorize EVERY event against current DB membership (not cached room state), and re-check when a member is removed (force-leave their sockets from the room). Validate every payload with a schema; reject unknown fields. Ack-based delivery: the server acks each send with the persisted message id and server timestamp; the client dedupes using a client-generated idempotency key to survive reconnect retries. Spam protection: reuse the token bucket, add a per-room limit and a temporary mute on repeated violations; typing events throttled and never persisted. Read receipts and delivery: per-participant last_read_message_id (not one row per message), delivered_at, and unread counts per conversation computed efficiently. No N+1 in the conversation list. Presence: Redis-based online/offline with multi-tab and multi-device support (reference-counted by connection), TTL heartbeat so crashed servers do not leave ghost users online, and a presence event only to users who share a room with the person. Redis adapter for Socket.IO so multiple Gunicorn workers/instances work; document and test the horizontal-scaling assumptions (sticky sessions in the Nginx config or a documented alternative). Offline notifications: when a recipient has no active socket, persist a notification and enqueue a Celery task (batched, so a burst of messages produces one digest rather than 50 emails or notifications). Respect per-user notification preferences if that table exists; otherwise add a minimal preferences model. Moderation and audit: moderators/admins can delete any message in their group (tombstone, with reason), and audit entries are written for member changes, moderation deletes and admin actions. Do not audit normal message sending (volume), only the sampled metadata the Security Guide requires. REST fallbacks (documented in docs/api and the OpenAPI spec): groups CRUD, members, conversations list (with last message and unread count), history, send (fallback), DM open, mark read.
  - Frontend: Chat page with conversation list and message pane; Composer with RHForm+Zod, length counter, Enter/Sender, Shift+Enter for newline, attach library file, typing indicator; Optimistic send with idempotency key, retry on failure, offline banner, automatic resync on reconnect; Group management dialogs gated by PermissionGate; Socket store: connect only after auth, reconnect with backoff and fresh token, dedupe events, listener cleanup on unmount; Accessibility: ARIA live region, keyboard navigation, reduced motion; Mobile-first layout; Notifications page and header badge integrate with real-time notification event.
  - Backend: Admin dashboard with stats, users, academic CRUD, groups, resources, moderation queue, audit log viewer, teacher allowlist. Analytics: lightweight aggregated metrics only, privacy-aware. Search polish: unified search across resources + groups with FTS, ranking, highlighting, filters, typo tolerance. Production hardening: observability (structured JSON logs, error tracking, health endpoints, Prometheus metrics), security review (dependency audit, secret scanning, CSP, CORS, cookie flags, rate-limit coverage, auth/permission decorator coverage test), performance review (EXPLAIN hot queries, index optimization, Redis caching, frontend bundle analysis, Lighthouse > 90, API p95 < 300ms), resilience (graceful shutdown, Celery retry/dead-letter, idempotent tasks, DB/Redis timeouts, degrade/fall-close behavior), backup and recovery (scripted verification, restore drill, RPO/RTO), deployment (docker compose, Nginx hardening, environment matrix, startup validation script, zero-downtime migration guidance, rollback runbook), CI/CD (GitHub Actions per docs/21_DEVOPS_GUIDE.md, coverage gate 80%+, required status checks for branch protection). Documentation: docs/features/GROUPS.md, docs/features/CHAT.md, docs/api/README.md updated, docs/03_DATABASE_GUIDE.md updated, docs/00_PROJECT_MEMORY.md updated.
  - Coverage gate raised to 80%.

## Pending

- Phase 5 completion: Admin Dashboard full management screens, Analytics summary tables, Search polish unified endpoint, Production hardening (observability, security, performance, resilience, backup, deployment, CI/CD), Release candidate preparation.
- Database Schema — materialized views / summary tables (Phase 5 item)
- Performance validation: Lighthouse > 90 on all key pages, API p95 < 300ms on seeded dataset
- Security scan clean (pip-audit, npm audit, CSP/CORS verification)
- Automated test enumerating all routes + auth/permission checks
- Playwright E2E: admin flow and full smoke path against staging compose
- Rollback runbook documented and tested
- Rollout to production per docs/22_RELEASE_GUIDE.md

## Stack (continued)
- Frontend: React, Vite, Tailwind CSS, Zustand, TanStack Query, React Router, Axios, Socket.IO Client, React Hook Form + Zod
- Backend: Flask, Flask-SocketIO, SQLAlchemy, Alembic, Gunicorn
- Database: Supabase PostgreSQL + PostGIS (option), Redis, Celery
- DevOps: Docker, Nginx, GitHub Actions, pip-audit, npm audit

## Upcoming
- Phase 5 finish + release candidate v1.0.0-rc.1
- Post-release roadmap: mobile app, notification preferences, moderation tools expansion, analytics expansion, internationalization

## Next Step
Continue with Phase 5 implementation to complete the release candidate.