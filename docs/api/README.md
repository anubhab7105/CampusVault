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
| **Groups** | **POST `/groups`, GET `/groups`, GET `/groups/{id}`, POST `/groups/{id}/members`, POST `/groups/{id}/leave`, POST `/groups/{id}/transfer-ownership`, POST `/groups/{id}/members/{member_id}/role`, GET `/groups/{id}/members`** | **JWT + membership** |
| **Chat** | **POST `/chat/messages`, GET `/chat/history`, POST `/chat/{conversation_id}/read`, POST `/chat/dm/open`, GET `/chat/dm/conversation`** | **JWT + participation** |
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
Moderators/admins can force-leave a user's sockets from a room when membership
changes.

## Rate limiting

Auth endpoints: 5/minute. Default: 100/minute. Redis-backed.

## Phase 4 Additions

### Groups

- `POST /groups` — Create group with mirrored conversation
- `POST /groups/{id}/leave` — Leave group (last owner must transfer ownership first)
- `POST /groups/{id}/transfer-ownership` — Initiate ownership transfer
- `POST /groups/{id}/members/{member_id}/role` — Change member role (owner/moderator)
- `GET /groups/{id}/members` — List group members

### Chat

- `POST /chat/messages` — Send message with idempotency key for dedup on reconnect
- `GET /chat/history` — Keyset-paginated message history (cursor: `before_id`)
- `POST /chat/{conversation_id}/read` — Mark conversation read, update `last_read_at`
- `POST /chat/dm/open` — Open-or-get direct message between two users
- `GET /chat/dm/conversation` — List DM conversations for a user

### Notifications

- `POST /notifications/{id}/read` — Mark single notification as read
- `POST /notifications/read-all` — Mark all notifications as read

### Quota

- Endpoints for per-user upload rate limiting and quota tracking (enforced in
  upload-request phase, details in docs/features/FILE_STORAGE.md)

## Response Envelope Consistency

All endpoints return the canonical envelope:

```json
// Success
{ "success": true, "message": "Operation completed.", "data": { ... } }

// Error
{ "success": false, "error": { "code": "...", "message": "..." } }
```

Error codes follow the existing taxonomy: `VALIDATION_ERROR`, `UNAUTHORIZED`,
`FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `INTERNAL_ERROR`,
`SERVICE_UNAVAILABLE`.

## OpenAPI / Swagger

The OpenAPI 3.1 spec at `/api/v1/openapi.json` includes all endpoints,
payload schemas, ack mechanisms, and error codes. Swagger UI is at
`/api/v1/docs`.

## Real-time Details

See `docs/features/CHAT.md` for the full socket protocol, payload schemas,
ack flow, reconnect & removal sequences, and security model.

See `docs/features/GROUPS.md` for group CRUD, membership rules, and role diagrams.