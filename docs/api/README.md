# CampusVault API Documentation

Base path: `/api/v1`. JSON only. Stateless JWT authentication.

## Response envelopes (docs/08_API_GUIDE.md)

Success:
```json
{ "success": true, "message": "Operation completed.", "data": {} }
```
Error:
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "..." } }
```

Error codes: `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`,
`CONFLICT`, `RATE_LIMITED`, `INTERNAL_ERROR`, `SERVICE_UNAVAILABLE`.

## Machine-readable spec

`GET /api/v1/openapi.json` — OpenAPI 3.1 document.
`GET /api/v1/docs` — Swagger UI.

## Endpoint catalog

| Area | Endpoints | Auth |
| ---- | --------- | ---- |
| Health | GET `/health/live`, GET `/health/ready` | none |
| Auth | GET `/auth/google/authorize`, POST `/auth/google`, POST `/auth/teachers/otp/request`, POST `/auth/teachers/otp/verify`, POST `/auth/refresh`, POST `/auth/logout`, GET `/auth/me` | refresh endpoints need JWT + CSRF token; OTP endpoints anti-enumeration |
| Users | GET `/users/me`, GET `/users` | JWT + `admin:users:manage` for list |
| RBAC | GET `/rbac/roles`, GET `/rbac/permissions`, POST/DELETE `/rbac/roles/{id}/permissions/*`, POST `/rbac/users/{id}/roles` | admin |
| Academic | GET/POST `/academic/departments|programs|semesters|sections|subjects` | read: any; write: admin |
| Groups | POST/GET `/groups`, GET `/groups/{id}`, POST `/groups/{id}/members` | JWT + membership |
| Chat | GET/POST `/chat/conversations/{id}/messages`, POST `/chat/conversations/dm/{peer}`, POST `/chat/conversations/{id}/read` | JWT + participation |
| Library | GET/POST `/library/resources`, GET `/library/resources/{id}`, POST `/library/resources/{id}/download`, DELETE `/library/resources/{id}` | JWT + permissions |
| Files | POST `/files`, GET `/files/{id}` | JWT |
| Notifications | GET `/notifications`, GET `/notifications/unread-count`, POST `/notifications/{id}/read`, POST `/notifications/read-all` | JWT |
| Audit | GET `/audit-logs` | admin |

## Real-time (Flask-SocketIO + Redis adapter)

Connect with `auth: { token: <access_token> }` on the Socket.IO handshake —
unauthenticated connections are refused.

Rooms: `group_<id>`, `dm_<id>`.
Events: connect, disconnect, join_group, leave_group, send_group_message,
edit_group_message, delete_group_message, typing, notification, read_receipt,
delivery_status, socket_error.

Every event is authorized against the database and payload-validated; a
token-bucket rate limit (30 msg / 30 s per user) guards against spam.

## Rate limiting

Auth endpoints: 5/minute. Default: 100/minute. Redis-backed.
