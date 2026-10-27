
# PROJECT MEMORY

## Project
CampusVault

## Current Status
Scaffolding complete

## Current Phase
Phase 1 — Scaffolding (done). Next: Phase 2 — Authentication end-to-end.

## Stack
- React, Vite, Tailwind CSS, Zustand, TanStack Query, React Router, Axios, Socket.IO Client, React Hook Form + Zod
- Flask, Flask-SocketIO, SQLAlchemy, Alembic, Gunicorn
- Supabase PostgreSQL, Supabase Storage, Redis, Celery, Docker, Nginx, Gmail SMTP (development only)
- pytest + Flask test client, Vitest + React Testing Library, Playwright

## Core Principles

- Security First
- API First
- Production Quality
- Documentation Driven
- Test Driven where practical

## Completed

- Functional Planning
- Initial Architecture
- Technology Selection
- Phase 1 scaffolding:
  - Repository layout (frontend/, backend/, docker/, tests/, .github/workflows/)
  - Backend: app factory, config per environment, extensions, constants, error handlers, response envelopes, request-logging middleware (request_id, user_id, endpoint, duration, status_code), security headers, JWT blocklist, RBAC decorator, Socket.IO init with JWT handshake, Celery app + tasks
  - Blueprints: health, auth, users, rbac, academic, groups, chat, library, files, notifications, admin, audit, docs (OpenAPI + Swagger)
  - Models + Alembic migration 0001: all 20 core tables (users, roles, permissions, user_roles, role_permissions, departments, programs, semesters, sections, subjects, groups, user_groups, conversations, conversation_participants, messages, files, resources, notifications, audit_logs), UUID PKs, FKs, composite indexes, soft deletes, check constraints
  - Frontend: Vite + Tailwind design tokens, lazy router with ProtectedRoute, Axios client with refresh-token interceptor, four Zustand stores (auth, theme, sidebar, socket), toast store, base UI kit (Button, Input, Card, Table, Dialog, Toast, Skeleton, EmptyState), ErrorBoundary, Auth/Dashboard layouts, placeholder pages (Login, Dashboard, Library, Chat, Admin, Notifications, NotFound)
  - Infra: Dockerfile, gunicorn.conf.py, wsgi.py, run.py, docker-compose.yml (backend, worker, redis, nginx), Nginx config with WS upgrade + security headers
  - CI: GitHub Actions workflow (lint, type check, pytest, vitest, build, dependency review, deploy smoke test)
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

## Pending

- Database Schema — DONE (migration 0001 + 0002 teacher_allowlist)
- Authentication — end-to-end flows completed (see above)
- RBAC — permission grants via admin UI completed; last-admin protection implemented
- Admin Dashboard — full UI implemented (allowlist, user deactivation, role matrix)
- Chat — scaffolded (REST + Socket.IO events)
- Library — scaffolded placeholder
- Notifications — scaffolded placeholder
- Deployment — CI smoke test scaffolded

Update this file after every completed feature.
