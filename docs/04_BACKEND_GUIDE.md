
# Backend Guide

## Stack
- Flask
- Flask-SocketIO
- SQLAlchemy
- Alembic
- Gunicorn

## Architecture

Use feature-based blueprints.

app/
├── blueprints/
├── models/
├── services/
├── repositories/
├── schemas/
├── middleware/
├── sockets/
├── tasks/
└── utils/

## Request Flow

Client
→ Middleware
→ Blueprint
→ Validation
→ Service Layer
→ Repository
→ Database
→ Response

## Rules

- Controllers remain thin.
- Business logic belongs in services.
- Database access goes through repositories.
- Validate every request.
- Return consistent JSON responses.
- Centralize exception handling.
- Never expose stack traces.
- Use Alembic for every schema change.

## API Standards

- /api/v1
- Pagination
- Filtering
- Sorting
- Structured error objects

## Logging

Every request logs:
- request_id
- user_id
- endpoint
- duration
- status_code
