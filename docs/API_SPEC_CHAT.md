# CampusVault — API Design: Chat Domain v1

Status: Draft for review
Stage: Feature Implementation Workflow → Step 4 (API Design), Chat domain
Depends on: DATABASE_SCHEMA.md, 07_SOCKET_GUIDE.md, API_SPEC_ACADEMIC.md (section↔group coupling), 08_API_GUIDE.md

## REST vs. Socket.IO Split

07_SOCKET_GUIDE.md defines the *live* event surface (send/edit/delete message, typing, receipts).
This domain needs REST endpoints too, for anything that isn't a live push: listing conversations,
paginated message history, group CRUD, and membership management. Rule applied throughout:

- **REST** = anything you'd want on page load, refresh, or pagination (source of truth, persisted reads/writes).
- **Socket.IO** = anything that needs to reach *other* connected clients in real time.

Message send/edit/delete are the one gray area: per 07_SOCKET_GUIDE.md they're socket **events**,
not REST calls — the client emits `send_group_message` etc. directly. REST still exposes a
**history** endpoint for initial load/pagination/scrollback. The socket handlers and the REST
history endpoint both go through the same service-layer function to avoid divergent logic
(Backend Guide: "Business logic belongs in services").

Base path: `/api/v1/chat`

---

## Conversations

### `GET /api/v1/chat/conversations`
Lists the current user's conversations (both DMs and groups they're a member of), ordered by
most recent message. This powers the chat sidebar on load.

**Response `200`**
```json
{
  "success": true, "message": "OK",
  "data": {
    "items": [
      {
        "id": "uuid",
        "type": "group",
        "group": { "id": "uuid", "name": "CS301 - Section A", "type": "section" },
        "last_message": { "content": "...", "sender_id": "uuid", "created_at": "..." },
        "unread_count": 3
      },
      {
        "id": "uuid",
        "type": "dm",
        "other_participant": { "id": "uuid", "full_name": "...", "avatar_url": null },
        "last_message": { "content": "...", "sender_id": "uuid", "created_at": "..." },
        "unread_count": 0
      }
    ],
    "page": 1, "page_size": 20, "total": 12
  }
}
```
`unread_count` is derived from `message_receipts` (messages in this conversation with no `read`
receipt from the current user) — computed in the service layer, not stored.

### `POST /api/v1/chat/conversations/dm`
Starts (or returns existing) a DM conversation with another user. Idempotent — calling twice with
the same `user_id` returns the same conversation.

**Request**: `{ "user_id": "uuid" }`
**Service logic**: look up an existing `conversation` where `type=dm` and both users are in
`conversation_participants`; if none, create `conversation` + two `conversation_participants` rows
in one transaction.
**Errors**: `USER_NOT_FOUND` (404), `CANNOT_DM_SELF` (400).

---

## Message History

### `GET /api/v1/chat/conversations/{conversation_id}/messages?before={message_id}&limit=50`
Cursor-paginated history (per 08_API_GUIDE.md pagination standard), newest-first, for scrollback.

**Authorization**: caller must be in `conversation_participants` for this conversation — enforced
by the same check the socket layer uses before allowing a room join (shared service function).

**Response `200`**
```json
{
  "success": true, "message": "OK",
  "data": {
    "items": [
      {
        "id": "uuid", "sender_id": "uuid", "content": "...", "content_type": "text",
        "edited_at": null, "created_at": "...",
        "receipt_summary": { "delivered_count": 4, "read_count": 2 }
      }
    ],
    "has_more": true,
    "next_cursor": "uuid-of-oldest-message-in-page"
  }
}
```
Soft-deleted messages (`deleted_at` set) are returned with `content: null` and a `deleted: true`
flag rather than omitted, so clients can render "message deleted" placeholders in order.

**Errors**: `CONVERSATION_NOT_FOUND` (404), `FORBIDDEN` (403 — not a participant).

---

## Groups

### `GET /api/v1/chat/groups?type=custom`
Lists groups the user belongs to. `type=section` groups are typically read-only membership
(managed via Academic domain's section membership, see API_SPEC_ACADEMIC.md); this filter mainly
matters for `type=custom` groups the user created or joined directly.

### `POST /api/v1/chat/groups`
Creates a **custom** group (not `type=section` — those are created by the Academic domain's
section-creation flow, per the coupling documented in API_SPEC_ACADEMIC.md).

**Request**: `{ "name": "Study Group - DBMS", "description": "..." }`
**Service logic**: create `groups` row (`type=custom`, `created_by=current_user`), create matching
`conversations` row (`type=group`), add creator as `group_members` with `role_in_group=admin` and
as `conversation_participants`, all in one transaction.
**Response `201`**: created group + its conversation_id.

### `PATCH /api/v1/chat/groups/{group_id}`
Update name/description. **Authorization**: `role_in_group=admin` for this group, or global
`chat:manage` permission (staff override).
**Errors**: `GROUP_NOT_FOUND` (404), `FORBIDDEN` (403).

### `DELETE /api/v1/chat/groups/{group_id}`
Soft delete. Only for `type=custom` groups — `type=section` groups are deleted via the Academic
domain's section deletion, not directly here.
**Errors**: `CANNOT_DELETE_SECTION_GROUP` (400) if `type=section`.

---

## Group Membership

### `GET /api/v1/chat/groups/{group_id}/members`

### `POST /api/v1/chat/groups/{group_id}/members`
Add a member to a **custom** group (section groups are managed via Academic domain membership,
which mirrors into `group_members` automatically — see API_SPEC_ACADEMIC.md).
**Request**: `{ "user_id": "uuid" }`
**Service logic**: insert `group_members` + `conversation_participants` rows together.
**Errors**: `ALREADY_MEMBER` (409), `CANNOT_MODIFY_SECTION_GROUP` (400).

### `DELETE /api/v1/chat/groups/{group_id}/members/{user_id}`
Same custom-group-only restriction.

---

## Socket.IO Event Contracts (reference — implemented in `app/sockets/`, not REST)

Documenting request/response *shapes* for the events already named in 07_SOCKET_GUIDE.md, since
the guide named the events but not their payloads:

| Event (client→server) | Payload | Server emits back |
|---|---|---|
| `join_group` | `{ conversation_id }` | joins room `group_<id>` or `dm_<id>`; no ack payload needed beyond success/error |
| `send_group_message` | `{ conversation_id, content, content_type }` | broadcasts `message.new` to room with full message object |
| `edit_group_message` | `{ message_id, content }` | broadcasts `message.edited` to room |
| `delete_group_message` | `{ message_id }` | broadcasts `message.deleted` to room (soft delete) |
| `typing` | `{ conversation_id, is_typing: bool }` | broadcasts `typing` to room, excluding sender |
| `read_receipt` | `{ message_id }` | inserts `message_receipts` row (`status=read`); broadcasts `receipt.updated` to room |

Every handler: (1) validates the JWT on the socket connection (already required per guide),
(2) re-validates the payload (same Pydantic schemas as REST would use — no event trusts input
just because it's a socket), (3) checks `conversation_participants` membership before touching
data, per "Authorize every event" in the Socket Guide's best practices.

## Open Items for Backend Implementation Step

- `delivery_status` event (named in Socket Guide but not detailed above) — assumed it fires
  automatically when a client's socket receives `message.new` while connected (implicit delivery),
  distinct from `read_receipt` which is an explicit user action. Confirm this interpretation.
- Whether `unread_count` in the conversations list should be cached (Redis) given it's computed
  per-conversation per-request — likely needed once conversation counts grow; flagged for
  10_PERFORMANCE_GUIDE.md's "cache frequently accessed data" at implementation time.
- Offline notification queueing (Socket Guide best practice) — this is the bridge to the
  Notifications domain (a `message.new` for an offline user should create a `notifications` row);
  documented here as a dependency for that domain's spec.
