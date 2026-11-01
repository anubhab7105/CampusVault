# CampusVault

CampusVault — an online academic library platform for a college.

## Repository layout

| Path | Purpose |
| ---- | ------- |
| `backend/` | Flask application: app factory, config, blueprints, models, services, repositories, schemas, middleware, sockets, tasks, Alembic migrations, tests |
| `frontend/` | React + Vite SPA: pages, components, layouts, routes, stores, services, hooks, types, tests |
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

## Rate Limiting

Rate limits are defined centrally in `backend/app/utils/rate_limit.py` and
applied via the `@cv_rate_limit` decorator (a wrapper over Flask-Limiter).
The route-coverage test
(`tests/unit/test_rate_limit_route_coverage.py`) fails if any route in the
required set lacks a limiter.

### Keying rules
- Authenticated routes: keyed on `user:<user_id>` from the verified JWT,
  with IP fallback when no valid token is present.
- Unauthenticated routes: keyed on `ip:<addr>` only.
- When `TRUST_PROXY=true` and the immediate `remote_addr` is listed in
  `TRUSTED_PROXIES`, the leftmost `X-Forwarded-For` entry is used.  This is
  safe because the header is only consulted for verified proxies.
- Socket.IO events are throttled per authenticated user via a Redis token
  bucket (`socket_throttle`).

### Error contract
HTTP 429 responses include a `Retry-After` header and a canonical JSON
error envelope (`{"success": false, "error": {"code": "RATE_LIMITED", ...}}`)
that leaks no keys, internals, or other-user data. Socket events emit a
matching `socket_error` event.

### Environment variables
| Variable | Default | Description |
|----------|---------|-------------|
| `RATELIMIT_DEFAULT` | `100/minute` | Default limit for general routes |
| `RATELIMIT_AUTH` | `5/minute` | Auth endpoints (login, OTP, refresh, logout, /me) |
| `RATELIMIT_SEARCH` | `30/minute` | Library browse/search |
| `RATELIMIT_CHAT_MESSAGE` | `30/minute` | HTTP chat message send |
| `RATELIMIT_UPLOAD` | `10/minute` | File upload request/finalize/register |
| `RATELIMIT_DOWNLOAD` | `30/minute` | Resource download |
| `RATELIMIT_ADMIN_WRITE` | `30/minute` | Admin write operations |
| `RATELIMIT_ADMIN_READ` | `30/minute` | Admin read operations |
| `RATELIMIT_SOCKET_MESSAGE` | `30/30seconds` | Socket send_group_message |
| `RATELIMIT_SOCKET_JOIN` | `60/minute` | Socket join_group |
| `RATELIMIT_SOCKET_TYPING` | `20/10seconds` | Socket typing |
| `TRUST_PROXY` | `false` | Enable X-Forwarded-For IP keying |
| `TRUSTED_PROXIES` | `127.0.0.1,::1` | Trusted proxy IPs (only used when TRUST_PROXY=true) |

See `docs/00_PROJECT_MEMORY.md` for phase status and `docs/api/` for the API
contract.
