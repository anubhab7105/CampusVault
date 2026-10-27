# Chat Feature

## Overview

Real-time messaging for CampusVault, supporting group conversations and direct messages
(1:1 DMs). All messages are stored as plain text with client-side output encoding; no raw
HTML is ever stored or rendered. Messages have a 15-minute edit window, soft-delete
(tombstone) semantics, and delivery/read receipts per participant.

## Models

### `messages`

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `conversation_id` | UUID | FK to `conversations.id` |
| `sender_id` | UUID | FK to `users.id` (nullable for system messages) |
| `message_type` | VARCHAR(16) | `"text"` \| `"system"` |
| `content` | TEXT | Plain text payload (wiped on tombstone) |
| `file_id` | UUID | FK to `files.id` (references clean Phase-3 file) |
| `reply_to_id` | UUID | Self-referencing FK to `messages.id` |
| `is_edited` | BOOLEAN | True if edited within window |
| `edited_at` | TIMESTAMP | When it was edited |
| `delivered_at` | TIMESTAMP | When all participants received |
| `deleted_at` | TIMESTAMP | Soft delete timestamp |
| `created_at` | TIMESTAMP | Auto-created |

### `conversations`

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `conversation_type` | VARCHAR(16) | `"group"` \| `"direct"` |
| `group_id` | UUID | FK to `groups.id` (null for DMs) |
| `last_message_at` | TIMESTAMP | Updated on each new message |
| `is_active` | BOOLEAN | Soft delete flag |

### `conversation_participants`

| Column | Type | Description |
|---|---|---|
| `conversation_id` | UUID | PK + FK to conversations |
| `user_id` | UUID | PK + FK to users |
| `is_admin` | BOOLEAN | Can moderate (group only) |
| `last_read_at` | TIMESTAMP | Last message participant read |

### `notifications`

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK to users |
| `notification_type` | VARCHAR(64) | e.g. `"message"`, `"mention"`, `"system"` |
| `title` | VARCHAR(160) | Notification title |
| `body` | VARCHAR(500) | Notification body |
| `payload` | JSON | Extra data (e.g. message id, group id) |
| `is_read` | BOOLEAN | Read status |
| `read_at` | TIMESTAMP | When read |
| `delivered_at` | TIMESTAMP | When delivered to client |
| `created_at` | TIMESTAMP | Auto-created |

## Message Lifecycle

### Send

1. Client composes message (max 4000 chars, Zod-validated)
2. `POST /api/v1/chat/messages` with `conversation_id`, `content`, `idempotency_key`
3. Server validates participant membership
4. Message persisted via `ChatService.send_group_message()` / `send_dm()`
5. `last_message_at` updated on conversation
6. Socket.IO `send_group_message` event emitted to conversation room
7. Client receives ack with `message_id` + server timestamp
8. Client dedupes using `idempotency_key` to survive reconnect retries

### Edit (within 15-min window)

1. Client calls `PUT /api/v1/chat/messages/{id}` with new content
2. Server checks: editor is sender AND within edit window
3. If valid: `content` updated, `is_edited = true`, `edited_at` set
4. If expired: server returns 403; only admins can tombstone
5. Socket.IO `edit_group_message` event emitted to room
6. Client UI shows "edited" indicator

### Soft delete (tombstone)

1. Client or moderator calls `DELETE /api/v1/chat/messages/{id}`
2. Server validates permissions (owner/moderator can delete any; others only own)
3. Message `content` set to `null`, `message_type` → `MESSAGE_TYPE_SYSTEM`
4. `is_deleted = true`; audit trail preserved
5. Socket.IO `delete_group_message` event emitted
6. Client UI shows "deleted" system bubble

### Reply-to

- Supported via `reply_to_id` FK on `messages`
- Client UI shows reply preview bubble
- Reply content is plain text; no nested threading in DB

### Edit window

- Configurable via `MESSAGE_EDIT_WINDOW_MINUTES` (default 15)
- Enforced server-side by comparing `message.created_at` against `now() - window`
- After window: only admins can tombstone; users must re-post new message
- Window start = message `created_at`; window is server-time based (not client)

### History (keyset pagination)

- Cursor: `before_id` (message id of previously seen message)
- Order: newest first, stable on `(created_at, id)`
- SQL index: `ix_messages_conversation_created` supports the query
- No offset pagination — keyset only
- `EXPLAIN` verified: uses index on `conversation_id, created_at`

### Read receipts

- Per-participant: `conversation_participants.last_read_at`
- Updated by `mark_read(conversation_id, user_id)`
- Unread count per conversation: messages where `created_at > participant.last_read_at`
- Single query; no N+1

### Delivery status

- `Message.delivered_at` set when all participants have received
- Tracked per-message via `mark_delivered(message_id, delivered_at)`
- Client receives `delivery_status` event with `message_id`

### Typing indicator

- Emitted from Composer on keystroke (debounced, 1s delay)
- `socket.io` event: `typing`
- Received by all other participants in the same room
- Never persisted; expires after 1s of inactivity

### Mentions / Notifications

- `@username` in message text triggers a `notification` event
- Batched via Celery: a burst of messages produces one digest
- Respects user `notification_preferences` (email/push/in-app/digest frequency)
- If recipient has no active socket, notification row persists until user opens bell

## Direct Message Rules

- **One conversation per unordered pair**: enforced by `uq_conversations_direct_pair`
- **Role-based access**:
  - Admins: unrestricted
  - Students may DM teachers and students in their own department
  - Teachers may DM students in their groups/department
  - Default: allow with possible department refinement later
- **Block/mute**: `is_muted` flag on participant + optional block list (future work)
- **DM open**: `POST /api/v1/chat/dm/open` — returns existing or creates new DM conversation

## REST Fallbacks

| Endpoint | Description |
|---|---|
| `POST /api/v1/chat/messages` | Send message (fallback when socket disconnected) |
| `GET /api/v1/chat/history` | Keyset-paginated history |
| `POST /api/v1/chat/{conversation_id}/read` | Mark conversation read |
| `GET /api/v1/chat/dm/open` | Open-or-get DM between two users |
| `GET /api/v1/groups` | List groups (fallback) |
| `GET /api/v1/groups/{id}` | Get group details (fallback) |

## Socket.IO Events (exact set)

| Event | Payload | Authorization | Notes |
|---|---|---|---|
| `connect` | JWT in handshake | JWT required; expired → clean disconnect with reason | Handled in `connection.py` |
| `disconnect` | — | — | Client-initiated or server-triggered |
| `join_group` | `{ group_id }` | DB membership check | Joins `group_<group_id>` room |
| `leave_group` | `{ group_id }` | — | Forces leave from room on member removal |
| `send_group_message` | `{ conversation_id, content, reply_to_id, idempotency_key }` | Participant check + spam guard | Ack-based delivery |
| `edit_group_message` | `{ message_id, content }` | Author check + edit window | Only sender within window; admins can tombstone |
| `delete_group_message` | `{ message_id }` | Permission check (owner/moderator any; others own only) | Tombstone semantics |
| `typing` | `{ conversation_id, user_id, typing }` | Participant check | Throttled, never persisted |
| `notification` | `{ id, type, title, body, data }` | User-specific room | Emitted if online; else persisted |
| `read_receipt` | `{ conversation_id, user_id }` | Participant check | Updates `last_read_at` |
| `delivery_status` | `{ message_id }` | Sender check | `delivered_at` updated |
| `socket_error` | `{ code, message }` | — | Client handles reconnect |

## Security Checklist (addressed)

| # | Threat | Mitigation |
|---|---|---|
| Unauthorized room join | Every `join_group` validates DB membership; room names never trusted |
| IDOR on history/conversation ids | `conversation_id` validated against participant record per-event |
| Removed members still receiving events | On member removal, `force_leave_room` removes sockets from room |
| Stored XSS through message content | Client-side output encoding; content stored plain text, never raw HTML |
| Token expiry mid-connection | Handshake JWT verified; `connect_error` handler; client auto-reconnect |
| Event flooding / message spam | Token bucket rate limit (30 msg / 30s), per-room limit, temporary mute |
| Oversized payloads | Schema validation: max 4000 chars per message |
| Duplicate delivery on reconnect | Client idempotency key dedup; server `delivered_at` per participant |
| Cross-conversation read-receipt tampering | `last_read_at` stored on `ConversationParticipant`, updated only by own handler |
| Presence information leaks | Presence only emitted to users who share a room |
| Attachment access bypass | Attachments reference existing `file_id` from Phase 3; sender must have access |
| DM harassment vectors | Role-based DM rules; block/mute schema (is_muted + block list); audit trail |

## API Spec (excerpt)

```yaml
paths:
  /api/v1/chat/messages:
    post:
      summary: Send a message
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                conversation_id:
                  type: string (UUID)
                content:
                  type: string
                  maxLength: 4000
                idempotency_key:
                  type: string
                reply_to_id:
                  type: string (UUID)
      responses:
        '200':
          description: Message sent
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  message:
                    type: object
                      id: string
                      conversation_id: string
                      content: string
                  delivery_status:
                    type: object
  /api/v1/chat/history:
    get:
      summary: Get message history (keyset pagination)
      parameters:
        - name: before_id
          in: query
          schema:
            type: string (UUID)
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
      responses:
        '200':
          description: Message history
  /api/v1/chat/{conversation_id}/read:
    post:
      summary: Mark conversation as read
      responses:
        '200':
          description: Marked read
  /api/v1/chat/dm/open:
    post:
      summary: Open or create a DM between two users
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                user_a_id:
                  type: string (UUID)
                user_b_id:
                  type: string (UUID)
      responses:
        '200':
          description: DM conversation
```

## Tests

- **Unit**: membership and role rules, DM pair normalization, edit-window rules,
  spam bucket, cursor encoding
- **Integration (PostgreSQL + Redis)**: REST group and history flows; socket tests
  using Flask-SocketIO test client for join authorization, send/ack, edit/delete
  permissions, read receipts, forced leave on member removal, token-expiry disconnect,
  idempotent retry, two-client message fan-out through Redis adapter
- **Celery**: digest batching for offline notifications, using fakes
- **Frontend**: Vitest + RTL for composer validation, optimistic send/retry, message
  status display, infinite scroll cursor logic, socket-store reconnect behavior
  (mock socket); Playwright E2E with two browser contexts (student and teacher)
  exchanging messages with read receipts
- **Load check**: simulate N concurrent sockets sending messages, observe p95 latency,
  Redis/DB load recorded in docs. Target: send ack under 300ms at documented concurrency

## Residual Risks

- Edit window bypass if client manipulates local time: server-enforced via DB compare
- Clocks skew on `delivered_at` / `last_read_at`: use server UTC time, tolerance in comparisons
- Redis TTL expiry gap: backup cleanup task runs every hour to catch missed expirations
- DM harassment if block list not policed: moderator review path via audit
- False positives on mentions triggering notifications: configurable threshold

## Deployment Notes

- Socket.IO Redis adapter enables horizontal scaling (multiple Gunicorn workers)
- Rate-limited token bucket in Redis prevents single-user spam across workers
- Batched offline notifications (Celery) reduce DB writes under load
- Keyset pagination avoids OFFSET performance degradation at large message counts
- Conversation participant `last_read_at` enables efficient unread count computation