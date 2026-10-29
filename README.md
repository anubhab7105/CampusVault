# CampusVault

CampusVault — an online academic library platform for a college.

## Repository layout

| Path | Purpose |
| ---- | ------- |
| `backend/` | Flask application: app factory, database models, services, middleware, tasks, Alembic migrations, tests |
| `frontend/` | React + Vite SPA: pages, components, routes, stores, services, hooks, types, tests |
| `docker/` | docker-compose + Nginx config for local development |
| `tests/` | Playwright E2E tests (repo root) |
| `docs/` | Engineering documentation (guides + API + feature docs) |
| `.github/` | CODEOWNERS, pull request template, CI workflow |

This repository contains Phase-1 scaffolding: application factory, database
models and first Alembic migration, placeholder UI, and CI/CD pipelines.

See `docs/` for detailed design and deployment steps.

## Stack (locked)

Frontend: React, Vite, Tailwind CSS, Zustand, TanStack Query, React Router,
Axios, Socket.IO Client, React Hook Form + Zod.
Backend: Flask, Flask-SocketIO, SQLAlchemy, Alembic, Gunicorn.
Infra: Supabase PostgreSQL, Supabase Storage, Redis, Celery, Docker, Nginx,
Gmail SMTP (development only).

## Quick start (local development)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/base.txt -r requirements/test.txt -r requirements/dev.txt
cp ../.env.example .env   # edit with Supabase credentials
APP_ENV=development APP_SECRET_KEY=dev JWT_SECRET_KEY=dev python -m alembic upgrade head
python run.py             # API + sockets on :8000

# Frontend
cd ../frontend
npm ci
npm run dev               # Vite on :5173, proxies /api to :8000

# Full local stack (Docker)
docker compose -f docker/docker-compose.yml up --build
```

## Testing

```bash
cd backend  && pytest                       # unit + integration
cd frontend && npm test                     # vitest + React Testing Library
cd ..      && npx playwright test           # E2E (under tests/)
```

Coverage minimum 80% (Definition of Done); the backend ratchet starts at 40%
for scaffolding and rises per feature.

## Security checks

Pull requests and branch pushes run Python dependency auditing, frontend dependency auditing, and Gitleaks secret scanning. The supplementary dependency-review job can be enabled after turning on GitHub's Dependency graph feature and setting `DEPENDENCY_GRAPH_ENABLED=true`. See [the scanning and triage guide](docs/security/dependency-and-secret-scanning.md) for thresholds, false-positive handling, and credential rotation steps.

See `docs/00_PROJECT_MEMORY.md` for phase status and `docs/api/` for the API
contract.
