# OpenAPI/Swagger reference

The OpenAPI 3.1 spec is code-defined in `backend/app/blueprints/docs/__init__.py`
and served at:

- `GET /api/v1/openapi.json`
- `GET /api/v1/docs` (Swagger UI)

## Conventions

- Every path returns one of the two canonical envelopes (success / error).
- `401 UNAUTHORIZED` on every protected route when the JWT is missing/invalid.
- `403 FORBIDDEN` when the JWT lacks the required RBAC permission or role.
- List endpoints support `page`, `page_size`, `q` (search), `sort`, `order`.
- Error envelopes never include stack traces; internals are logged server-side.

## Extending the spec

When a new endpoint lands, add its `path`/`operation` block to
`backend/app/blueprints/docs/__init__.py:_spec()` and document it here.
Tag values must match the `tags` list in the spec.
