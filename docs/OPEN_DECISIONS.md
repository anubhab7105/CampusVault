# CampusVault — Open Decisions for Backend Implementation

Status: Awaiting answers
Stage: Between Feature Implementation Workflow steps 4 (API Design) and 5 (Backend Implementation)

Every item below was flagged in a prior doc (source noted) as an assumption made to keep design
moving. None block further design work, but each should be confirmed or corrected before the
matching code gets written, since several are security-relevant (auth timing, upload limits) and
are expensive to silently change later (e.g. shortening a JWT lifetime after clients depend on it).

Sensible defaults are pre-filled — reply with just the numbers/choices you want changed, or "keep
defaults" and I'll proceed with everything as-is.

---

## 1. Auth & Tokens (source: API_SPEC_AUTH.md)

| Item | Default | Notes |
|---|---|---|
| Access token lifetime | 15 min | Short-lived by design; refresh handles renewal |
| Refresh token lifetime | 30 days | Rotates on every use |
| OTP code length | 6 digits | |
| OTP expiry | 10 min | |
| OTP max requests per email/hour | 5 | Rate limit on `/otp/request` |
| OTP max verify attempts per code | 5 | Code invalidated after this |
| Logout scope | Single device (current session only) | "Log out everywhere" not built in v1 |
| JWT claims | `user_id`, `user_type`, `roles` | Confirm nothing else needed (e.g. active `section_id`) |

## 2. RBAC (source: API_SPEC_RBAC.md)

| Item | Default | Notes |
|---|---|---|
| First admin creation | One-time Alembic data migration / CLI command, not an API endpoint | |
| Starter permission codes | `resource:upload`, `resource:delete`, `group:create`, `group:manage`, `notification:send`, `rbac:manage`, `user:manage`, `academic:manage`, `library:manage_any`, `chat:manage` | Draft list — refine once all domains are implemented |
| Roles→permissions cache invalidation | Invalidate on every `PUT .../permissions` and `PUT .../roles` call | Redis-backed |

## 3. Academic (source: API_SPEC_ACADEMIC.md)

| Item | Default | Notes |
|---|---|---|
| Section creation auto-creates chat Group | Yes, coupled in the same transaction | Confirm this is desired vs. a separate explicit action |
| Semester deletion | Not supported in v1 (no delete endpoint) | May need an `is_active` status field instead later |
| Section deletion with active members | Blocked (409 `SECTION_IN_USE`) rather than cascading | Avoids silent data loss |

## 4. Chat (source: API_SPEC_CHAT.md)

| Item | Default | Notes |
|---|---|---|
| `delivery_status` semantics | Fires automatically when a connected client receives `message.new` (implicit); `read_receipt` is the separate explicit action | |
| `unread_count` computation | Computed per-request initially; add Redis caching if it becomes a hot path | |

## 5. Notifications (source: API_SPEC_NOTIFICATIONS.md)

| Item | Default | Notes |
|---|---|---|
| Presence tracking | Redis key scheme `presence:user:{user_id}`, written on socket connect/disconnect with TTL refresh | Shared helper `app/utils/presence.py`, used by both Chat and Notifications |
| Notification types (v1) | `message.new` only, extensible via generic `type` + `data` contract | `resource.uploaded`, `role.assigned` etc. can be added later without schema changes |
| Retention/archival | None in v1 | Matches Database Guide's "Future Improvements" |

## 6. Library (source: API_SPEC_LIBRARY.md)

| Item | Default | Notes |
|---|---|---|
| Max file size | 50 MB | |
| Allowed MIME/extension whitelist | `pdf`, `docx`, `pptx`, `xlsx`, `png`, `jpg`/`jpeg` | Covers the stated library-notes use case; extend later if needed |
| Malware scan provider | **Not decided — genuinely blocks the Celery scan task** | Options: self-hosted ClamAV (free, more ops overhead) vs. a hosted API (e.g. VirusTotal-style, less ops overhead, has usage limits/cost) |
| `file.scanned` notification on async scan completion | Add it | Uses the existing Notifications service contract, no new mechanism needed |
| "My uploads" filter bypassing scan-status gate | Add it (`GET /library/resources?mine=true`) | Lets uploaders see pending/infected state on their own files |
| Download URL expiry | 5 min (300s) | Signed Supabase Storage URL |

---

## Item That Actually Blocks Progress

Everything above has a workable default except **malware scan provider** in section 6 — that's an
infrastructure/vendor choice, not something I should default silently, since it affects Deployment
Guide's environment config and potentially has real cost implications. Worth deciding before
Library's backend implementation, though it doesn't block Auth/RBAC/Academic starting now.

---

## Suggested Path

Reply with any corrections to the defaults above (or "keep defaults" for the rest), and pick one
for the scan provider. I'll then start Backend Implementation with Auth (the foundation domain —
everything else depends on its middleware), and move through the remaining domains in the same
order they were designed: RBAC → Academic → Chat → Notifications → Library.
