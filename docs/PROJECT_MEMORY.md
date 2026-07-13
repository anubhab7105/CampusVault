# PROJECT MEMORY

## Project
CampusVault

## Current Status
In Development

## Current Phase
Backend Implementation (domain-by-domain)

## Stack
- React
- Vite
- Tailwind CSS
- Flask
- SQLAlchemy
- Socket.IO
- Supabase
- Redis
- Celery

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
- Database Schema (25 tables — DATABASE_SCHEMA.md, all SQLAlchemy models built and verified)
- API Design — all 6 domains (Auth, RBAC, Academic, Chat, Notifications, Library — API_SPEC_*.md, Pydantic schemas for every domain)
- Open Decisions consolidated (OPEN_DECISIONS.md — all defaults locked except malware scan provider, defaulted to ClamAV)
- Auth backend: repository, service, blueprint, JWT/OTP security utils, Celery email task — 24 tests passing
- RBAC backend: repository, service, blueprint, real permission-resolution middleware (replaces earlier TODO) — 23 tests passing
- Shared infra: centralized exception handling, response envelope, `require_auth`/`require_permission` middleware, real-Postgres pytest fixtures

## In Progress

- Academic backend implementation (repository, service, blueprint, tests) — next up, depends on RBAC (done)

## Pending

- Academic backend (Section↔Group auto-membership coupling with Chat still needs implementing)
- Chat backend (REST endpoints + actual Socket.IO event handlers in app/sockets/)
- Notifications backend
- Library backend (blocked on malware scan provider integration — ClamAV defaulted, not yet wired)
- Admin Dashboard (no API spec written yet — not covered by the 6 domains designed so far)
- App factory wiring (app/__init__.py, config, blueprint registration, Socket.IO server setup)
- Alembic migrations (models exist, no migration files generated yet)
- Frontend (entire React/Vite app — not started)
- Deployment / DevOps (Docker, CI pipeline, environment configs)

## Notes

- Test suite: 47 tests passing, 96% coverage, run against a real Postgres 16 instance (not SQLite/mocks), per Testing Guide's "Database fixtures" requirement.
- All specs and code live under a `campusvault/` folder with `docs/` and `backend/app/{models,schemas,repositories,services,blueprints,middleware,utils,tasks}/` structure per Backend Guide.

Update this file after every completed feature.
