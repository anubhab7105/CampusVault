# CampusVault — API Design: Notifications Domain v1

Status: Draft for review
Stage: Feature Implementation Workflow → Step 4 (API Design), Notifications domain
Depends on: DATABASE_SCHEMA.md, API_SPEC_CHAT.md (offline-notification dependency), 07_SOCKET_GUIDE.md, 08_API_GUIDE.md

## Resolving the Chat → Notifications Dependency

API_SPEC_CHAT.md flagged: a `message.new` event for an offline (not-connected) user should create
a `notifications` row. Resolved here:

- The chat service layer, after persisting a message, checks which `conversation_participants`
  (excluding the sender) do **not** have an active socket connection (tracked via a Redis
  presence set — connect/disconnect handlers write to it, per 07_SOCKET_GUIDE.md's Redis adapter).
- For each offline participant, it calls the **Notifications service** (not the REST API — direct
  in-process service call per Backend Guide's service-layer pattern) to create a `notifications`
  row with `type="message.new"` and `data={conversation_id, message_preview, sender_name}`.
- This keeps chat and notifications decoupled at the REST/socket layer while still connected at
  the service layer, matching Architecture Guide's "Feature Isolation" principle — notifications
  doesn't know about chat internals beyond the generic `type` + `data` contract.
- The same pattern applies to other future notification sources (`resource.uploaded`, etc.) —
  any domain can call the Notifications service with a `type` + `data` payload without the
  Notifications domain needing to know what triggered it.

Base path: `/api/v1/notifications`

---

## Listing & Reading

### `GET /api/v1/notifications?unread_only=true`
Cursor-paginated, newest-first.

**Response `200`**
```json
{
  "success": true, "message": "OK",
  "data": {
    "items": [
      {
        "id": "uuid",
        "type": "message.new",
        "title": "New message from Jane Doe",
        "body": "Hey, did you see the assignment...",
        "data": { "conversation_id": "uuid" },
        "read_at": null,
        "created_at": "..."
      }
    ],
    "has_more": true,
    "next_cursor": "uuid-of-oldest-in-page",
    "unread_count": 5
  }
}
```
`unread_count` is a cheap indexed count (`WHERE user_id = ? AND read_at IS NULL`) — the
`(user_id, read_at)` composite index in DATABASE_SCHEMA.md exists specifically for this query.

### `GET /api/v1/notifications/unread-count`
Lightweight endpoint for badge polling/refresh (cheaper than fetching the full list just to get
a number). **Response**: `{ "data": { "unread_count": 5 } }`

### `PATCH /api/v1/notifications/{id}/read`
Marks a single notification read. **Service logic**: set `read_at = now()` if not already set
(idempotent — re-marking an already-read notification is a no-op, not an error).
**Errors**: `NOTIFICATION_NOT_FOUND` (404), `FORBIDDEN` (403 — not the owner).

### `POST /api/v1/notifications/mark-all-read`
Bulk update — sets `read_at = now()` on all unread notifications for the current user.
**Response**: `{ "data": { "updated_count": 5 } }`

---

## Real-Time Delivery

Per 07_SOCKET_GUIDE.md, the `notification` socket event already exists for live push. Contract:

| Event (server→client) | Payload |
|---|---|
| `notification` | Same shape as a single item in the `GET /notifications` list above |

**Flow**: when the Notifications service creates a row, it does two things in the same call:
1. Persist the `notifications` row (source of truth, read via REST).
2. If the target user has an active socket connection (checked via the same Redis presence set
   used for the Chat domain's offline detection), emit `notification` directly to their socket —
   no separate "push" endpoint needed since it's server-initiated.

If the user is offline at creation time, no socket emit happens — they'll see it via `GET
/notifications` (or the unread-count badge) next time they load the app. No separate "queue and
retry" mechanism needed since the REST list already serves as the durable queue.

---

## No Public Create Endpoint

There is intentionally no `POST /api/v1/notifications` — notifications are only created by other
domains' service layers calling the Notifications service directly (in-process), never by a client.
This prevents notification spoofing/spam and matches Security Guide's "assume every request is
malicious" posture — a client-facing create endpoint would need its own abuse-prevention layer
for no real benefit, since nothing legitimate needs it.

## Open Items for Backend Implementation Step

- Exact Redis presence-set key scheme (e.g. `presence:user:{user_id}` with socket connect/disconnect
  TTL refresh) — needs to be shared code between Chat and Notifications services; document as a
  shared `app/utils/presence.py` helper at Backend Implementation time rather than duplicating logic.
- Notification types beyond `message.new` (e.g. `resource.uploaded`, `role.assigned`) — full type
  registry to be finalized once Library domain's API spec exists (next) and once RBAC assignment
  notifications are decided as in-scope for v1 or deferred.
- Retention/archival for read notifications — flagged as a Database Guide "Future Improvement"
  (archival strategy), not blocking v1.
