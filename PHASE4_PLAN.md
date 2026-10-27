# Phase 4: Groups + Chat (real-time) — Plan

## Requirements Summary

### 1. Groups
- **Create**: Owner + subject/section binding, mirrored conversation auto-created
- **List my groups**: Teacher/student sees their groups
- **Get group**: With membership check + role info
- **Add/remove members**: Owner only can invite; moderators can remove non-owners; last owner cannot leave without transferring ownership
- **Change member role**: Owner ↔ moderator, moderator ↔ member (owner confirms)
- **Leave group**: Any member can leave; if it's the last owner, must transfer ownership first
- **Group hierarchy**: subject_id, section_id optional; group_type: subject_group|section|team|club

### 2. Direct Messages
- **Open-or-get DM**: One conversation per user pair, enforced by unique constraint on normalized (least_id, greatest_id)
- **Role-based DM rules** (documented):
  - Students may DM teachers and students in their own department
  - Admins unrestricted
  - Teachers may DM students in their groups/department
- **Block/Mute**: Added as future work (schema clean — add `is_muted` on participant, block list model)
- **DM cannot be created across department barriers** for student↔student without teacher involvement

### 3. Messages
- **Send**: Text only, max 4000 chars, content plain text with client-side output encoding, attachments reference existing clean files from Phase 3
- **Edit**: Own messages only, within configurable window (e.g., 15 min), content wipe + `is_edited` flag + `edited_at` timestamp
- **Soft delete (tombstone)**: Content wiped, `message_type` → `MESSAGE_TYPE_SYSTEM`, `is_deleted=True`, audit trail preserved
- **Reply-to**: `reply_to_id` self-referencing FK
- **Message length limit**: 4000 chars enforced by schema + server-side

### 4. History (Keyset Pagination)
- **Cursor**: `before_id` (the id of a message previously seen)
- **Newest first**, stable ordering on `(created_at, id)`
- **No offset pagination** — use keyset (cursor) only
- **Index verified with EXPLAIN**: `ix_messages_conversation_created` supports the query

### 5. Socket.IO Events (exact set)
- `connect` — JWT handshake, expired token → clean disconnect with reason
- `disconnect`
- `join_group` — authorize DB membership, add to `group_<group_id>` room
- `leave_group` — force-leave sockets from room when member removed
- `send_group_message` — validate, service call, emit to room, ack with message id + server timestamp
- `edit_group_message` — own messages only, within window, emit updated content
- `delete_group_message` — tombstone (soft delete), emit delete event
- `typing` — throttled, never persisted
- `notification` — offline push, batched via Celery
- `read_receipt` — update `conversation_participants.last_read_at`, compute unread counts efficiently
- `delivery_status` — per-participant `delivered_at` tracking

**Key properties**:
- JWT required at handshake; expired tokens trigger clean disconnect
- Authorize EVERY event against current DB membership (rooms never trusted)
- Re-check when a member is removed (force-leave their sockets from the room)
- Validate every payload with schema; reject unknown fields
- Ack-based delivery: server acks each send with persisted message id and server timestamp
- Client dedupes using client-generated idempotency key to survive reconnect retries
- Spam protection: token bucket (30 msg / 30s), per-room limit, temporary mute on repeated violations
- Typing events throttled and never persisted

### 6. Read Receipts + Delivery
- **Per-participant** `last_read_message_id` (not one row per message — stored on `ConversationParticipant.last_read_at`)
- **delivered_at** on Message (set when all participants have received)
- **Unread counts** per conversation computed efficiently (single query with `last_read_at` comparison)
- **No N+1** in conversation list

### 7. Presence
- **Redis-based** online/offline with multi-tab and multi-device support (reference-counted by connection)
- **TTL heartbeat** so crashed servers do not leave ghost users online
- **Presence event only to users who share a room** with the person

### 8. Redis Adapter for Socket.IO
- **Multiple Gunicorn workers** via `message_queue=<redis>` in SocketIO init
- **Sticky sessions in Nginx** OR documented alternative (Redis adapter is the alternative)
- Test horizontal-scaling assumptions

### 9. Offline Notifications
- **When recipient has no active socket**, persist a `Notification` row
- **Celery task batched**: a burst of messages produces one digest rather than 50 notifications
- **Respect per-user notification preferences** (minimal preferences model if table exists)

### 10. Moderation + Audit
- **Moderators/admins** can delete any message in their group (tombstone, with reason)
- **Audit entries** for: member changes, moderation deletes, admin actions
- **Do NOT audit** normal message sending (volume), only sampled metadata the Security Guide requires

### 11. REST Fallbacks (documented in docs/api + OpenAPI)
- Groups CRUD ✅ (already partially implemented)
- Members: add/remove, list my groups, get group with role
- Conversations list (with last message + unread count)
- History (keyset pagination)
- Send (fallback — REST POST /api/v1/chat/messages)
- DM open (POST /api/v1/chat/dm/open)
- Mark read (POST /api/v1/chat/:conversation_id/read)

### 12. Frontend
- **Chat page**: conversation list (groups + DMs) with unread badges, last message preview, presence dots; message pane with infinite scroll upward (TanStack Query infinite query using cursor), date separators, grouped bubbles, reply preview, edited/deleted indicators, message status ticks (sending, sent, delivered, read)
- **Composer**: React Hook Form + Zod, length counter, Enter to send / Shift+Enter for newline, attach a library file (picker from clean files), typing indicator emission (debounced)
- **Optimistic send** with idempotency key, retry on failure, offline banner while disconnected, automatic resync on reconnect that fetches only messages after last known cursor
- **Group management dialogs**: create, members, roles, leave — gated by PermissionGate and group role
- **Socket store**: connect only after auth, reconnect with backoff and fresh token, dedupe events, clean up listeners on unmount (no leaks on route changes)
- **Accessibility**: message list is ARIA live region with polite announcements, composer and conversation list keyboard navigable, respect reduced motion
- **Mobile-first layout**: list and thread as separate screens on small viewports
- **Notifications page + header badge** integrate with new real-time notification event

## Affected Modules

### Backend (new / modified)
| Module | Changes |
|---|---|
| `app/models/group.py` | Add `leave_group` logic, role transitions, ownership transfer |
| `app/models/conversation.py` | DM pair normalization, participant role tracking |
| `app/models/message.py` | Edit window, tombstone logic, reply_to, delivered_at |
| `app/models/notification.py` | Minimal preferences model (optional) |
| `app/repositories/group_repository.py` |leave, transfer ownership, member role CRUD |
| `app/repositories/conversation_repository.py` | `find_direct_between`, participant management, last_read tracking |
| `app/repositories/message_repository.py` | Edit window enforcement, cursor history, tombstone queries |
| `app/services/group_service.py` | Membership rules, role transitions, ownership transfer, leave validation |
| `app/services/chat_service.py` | DM open/create, edit window, tombstone, read receipts, delivery tracking |
| `app/sockets/connection.py` | Enhanced JWT verification, expired token disconnect reason |
| `app/sockets/events.py` | All 11 event handlers with full authorization + spam guard |
| `app/sockets/rooms.py` | Additional auth helpers, DM room management |
| `app/sockets/handlers.py` | Notification fan-out, emit helpers |
| `app/services/chat_service.py` | New methods: open_dm, send_dm, edit_message, delete_message, mark_read |
| `app/services/notification_service.py` | Batched offline notification Celery task |
| `app/utils/redis_utils.py` | Rate limiting helpers, presence TTL renewal |
| `app/blueprints/groups/__init__.py` | Enhanced: leave, role transfer, member removal, ownership transfer |
| `app/blueprints/chat/__init__.py` | REST fallbacks: DM open, conversation list, mark read, send fallback |
| `app/alembic/versions/0007_dm_normalization.py` | Unique constraint on normalized DM pair |
| `app/alembic/versions/0008_message_edit_window.py` | Edit window enforcement |
| `app/alembic/versions/0009_notification_preferences.py` | User notification preferences (optional) |

### Frontend (new / modified)
| Module | Changes |
|---|---|
| `frontend/src/pages/chat/Chat.tsx` | Full chat UI: conversation list + message pane, infinite scroll, composer |
| `frontend/src/pages/groups/Groups.tsx` | Group list, create, member management, role transfer, leave |
| `frontend/src/components/chat/ConversationList.tsx` | Groups + DMs with unread badges, presence dots |
| `frontend/src/components/chat/MessagePane.tsx` | Infinite scroll upward, date separators, grouped bubbles, status ticks |
| `frontend/src/components/chat/Composer.tsx` | React Hook Form + Zod, length counter, Enter/Sender, file picker, typing |
| `frontend/src/components/chat/MessageBubble.tsx` | Optimistic send, edited/deleted indicators, reply preview |
| `frontend/src/components/chat/GroupManagementDialog.tsx` | Create, members, roles, leave with role checks |
| `frontend/src/hooks/useChat.ts` | TanStack Query infinite query, cursor logic, optimistic send, resync on reconnect |
| `frontend/src/hooks/useSocket.ts` | Connect/disconnect with backoff, event dedup, listener cleanup, reconnect resync |
| `frontend/src/stores/useSocketStore.ts` | Enhanced connect state (connecting, online, offline), presence |
| `frontend/src/types/chat.ts` | Extended types for edit, reply, tombstone, delivery status |
| `frontend/src/utils/validation.ts` | Stricter message content validation, edit window check |
| `frontend/src/constants/routes.ts` | New routes: /groups, /chat, /dm/:id |

### Infrastructure
| File | Changes |
|---|---|
| `docker/docker-compose.yml` | Add `redis` service (if not present), ensure `celery-worker` and `celery-beat` |
| `docker/nginx/campusvault.conf` | WebSocket upgrade (`Upgrade, websockets`), stickiness config or Redis adapter note, timeouts |
| `docs/03_DATABASE_GUIDE.md` | Updated table list (groups, user_groups, conversations, conversation_participants, messages, notifications) |
| `docs/api/README.md` | New endpoint catalog + Socket.IO event spec with payload schemas, acks, error codes |
| `docs/features/GROUPS.md` | Group CRUD, membership rules, role diagrams |
| `docs/features/CHAT.md` | Message lifecycle, history pagination, socket protocol, security model, threat notes, tests checklist |
| `docs/decision_log.md` | Phase 4 architectural decisions |
| `docs/15_FEATURE_IMPLEMENTATION_WORKFLOW.md` | Already exists — follow this workflow |

### Testing
| Category | Tests needed |
|---|---|
| **Unit** | Membership and role rules, DM pair normalization, edit-window rules, spam bucket, cursor encoding |
| **Integration (PostgreSQL + Redis)** | REST group and history flows; socket tests using Flask-SocketIO test client for join authorization, send/ack, edit/delete permissions, read receipts, forced leave on member removal, token-expiry disconnect, idempotent retry, two-client message fan-out through Redis adapter |
| **Celery** | Digest batching for offline notifications, using fakes |
| **Frontend** | Vitest + RTL: composer validation, optimistic send/retry, message status display, infinite scroll cursor logic, socket-store reconnect behavior (mock socket) |
| **Playwright E2E** | Two browser contexts (student and teacher) exchanging messages with read receipts |
| **Load check** | Simulate N concurrent sockets sending messages, observe p95 latency, Redis/DB load recorded in docs. Target: send ack under 300ms at documented concurrency |

### Documentation
- `docs/features/GROUPS.md` — Group CRUD, membership rules, role diagrams, sequence diagrams
- `docs/features/CHAT.md` — Models, REST API, socket protocol, sequence diagrams for send/ack/read/reconnect/removal, security model, threat notes, tests, checklist
- `docs/api/README.md` — Updated endpoint catalog + Socket.IO event spec
- `OpenAPI spec` — Updated with new group/chat endpoints
- `docs/03_DATABASE_GUIDE.md` — Table list matches actual schema
- `docs/00_PROJECT_MEMORY.md` — Chat and Notifications moved to Completed

## Security Checklist (address each explicitly)

| # | Threat | Mitigation |
|---|---|---|
| 1 | Unauthorized room join | Every `join_group` validates DB membership; room name never trusted |
| 2 | IDOR on history/conversation ids | Authorization check per-event; `conversation_id` validated against user's participant record |
| 3 | Removed members still receiving events | On member removal, `leave_group_room` forces-leave all their sockets from the room; `force_leave_room` helper |
| 4 | Stored XSS through message content | Client-side output encoding; content stored plain text, never raw HTML; `dangerouslySetInnerHTML` with trusted types only |
| 5 | Token expiry mid-connection | Handshake JWT verified; `connect_error` handler; client auto-reconnect with fresh token; server acks with idempotency key for resync |
| 6 | Event flooding / message spam | Token bucket rate limit (30/30s), per-room limit, temporary mute on repeated violations, typing throttled |
| 7 | Oversized payloads | Schema validation: max 4000 chars per message, group name max 120, description max 1000 |
| 8 | Duplicate delivery on reconnect | Client idempotency key dedup; server stores `delivered_at` per participant, only sends if not yet delivered |
| 9 | Cross-conversation read-receipt tampering | `last_read_at` stored on `ConversationParticipant`, updated only by participant own handler; server computes unread counts from this |
| 10 | Presence information leaks | Presence only emitted to users who share a room; no global "who's online" endpoint without room membership |
| 11 | Attachment access bypass | Attachment references existing `file_id` from Phase 3; sender must have access to the file (permission check in service) |
| 12 | DM harassment vectors | Block/mute schema (add `is_muted` + block list); role-based DM rules restrict student↔student across departments; report/audit for moderation review |

## Scaling Impact
- **Redis adapter** for Socket.IO enables horizontal scaling (multiple Gunicorn workers)
- **Rate-limited token bucket** in Redis prevents single-user spam across workers
- **Batched offline notifications** (Celery) reduce DB writes under load
- **Keyset pagination** avoids OFFSET performance degradation at large message counts
- **Conversation participant `last_read_at`** enables efficient unread count computation without N+1

## Design Decisions
1. **DM unique constraint**: Normalized pair `(least(user_a, user_b), greatest(user_a, user_b))` enforced via partial unique index in migration 0007
2. **Edit window**: 15 minutes configurable via app config; after window, only admins can edit (tombstone + re-post)
3. **Tombstone semantics**: Soft delete preserves audit trail; content wiped (`is_deleted=True`, `message_type=SYSTEM`), visible only to admins/owners unless disabled
4. **Read receipts per participant**: `ConversationParticipant.last_read_at` — single row per user per conversation, not per message
5. **Presence TTL**: 24h session TTL in Redis; heartbeat renewal from client every 45s; crashed server cleanup via TTL expiry
6. **Offline notification batching**: Celery task accumulates notification rows per user per minute, then sends one digest; reduces notification spam

## Residual Risks
- Race between member removal and socket event: mitigated by `force_leave_room` on member delete + re-authorization on each event
- Clocks skew on `delivered_at` / `last_read_at`: use server UTC time, tolerance in comparisons
- Redis TTL expiry gap: backup cleanup task runs every hour to catch missed expirations
- Edit window bypass if client manipulates local time: server-enforced window via DB compare, not client time
- DM harassment if block list not policed: moderator review path via audit

## Phase 5 (Proposed)
- Admin Dashboard: analytics, user/group management, message search across conversations
- Advanced analytics: active users, peak hours, most active groups
- Production hardening: monitoring (Prometheus + Grafana), backups, release candidate per docs/22_RELEASE_GUIDE.md
- End-to-end encryption option for DMs (Phase 5 stretch goal)