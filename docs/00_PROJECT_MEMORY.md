
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

## Pending

- Database Schema — DONE (migration 0001)
- Authentication — scaffolded; end-to-end flows next
- RBAC — scaffolded; permission grants via admin UI next
- Admin Dashboard — scaffolded placeholder
- Chat — scaffolded (REST + Socket.IO events)
- Library — scaffolded placeholder
- Notifications — scaffolded placeholder
- Deployment — CI smoke test scaffolded

Update this file after every completed feature.
