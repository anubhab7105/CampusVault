# CampusVault — API Design: Library Domain v1

Status: Draft for review
Stage: Feature Implementation Workflow → Step 4 (API Design), Library domain — final domain, closes API Design phase
Depends on: DATABASE_SCHEMA.md, 06_SECURITY_GUIDE.md (upload security), API_SPEC_ACADEMIC.md (department/program/subject scoping), 08_API_GUIDE.md

## Two-Step Upload (File then Resource)

Kept as two distinct steps rather than one combined endpoint:

1. **`POST /files`** — handles the raw upload + security pipeline. Returns a `file_id` once
   accepted (scan may still be `pending`).
2. **`POST /resources`** — attaches metadata (title, description, department/program/subject
   scoping) to an already-uploaded `file_id`.

Reasoning: the security pipeline (MIME validation, extension whitelist, size limits, malware scan)
is identical regardless of what the file will become (a library resource today, a chat file
attachment or avatar upload later). Splitting keeps `files` reusable across future features
instead of coupling upload logic to "library resource" specifically — matches Architecture Guide's
Feature Isolation principle.

Base path: `/api/v1/library`

---

## File Upload

### `POST /api/v1/files` (multipart/form-data)
**Request**: multipart body with the file itself.

**Service logic** (per 06_SECURITY_GUIDE.md's Upload Security checklist, in order):
1. Enforce max size limit (config-driven, reject oversized before reading full body where possible).
2. Validate MIME type against an explicit whitelist (not just trusting the client-sent
   `Content-Type` header — sniff actual content).
3. Validate extension against a whitelist; reject mismatches between claimed extension and
   sniffed MIME type (a `.pdf` that's actually an executable gets rejected here).
4. Generate a random `stored_filename` (never trust/reuse the client's original filename for
   storage — `original_filename` is kept only for display).
5. Upload to Supabase Storage at a path keyed by the random filename.
6. Insert `files` row: `scan_status="pending"`.
7. Enqueue a Celery task for malware scanning (async — response doesn't block on scan completion).
8. Write `audit_logs` row: `action="upload"`.

**Response `201`** (scan still pending — this is expected and normal)
```json
{
  "success": true, "message": "File uploaded, scan in progress.",
  "data": { "id": "uuid", "original_filename": "notes.pdf", "mime_type": "application/pdf", "size_bytes": 204800, "scan_status": "pending" }
}
```

**Errors**
| Code | HTTP | When |
|---|---|---|
| `FILE_TOO_LARGE` | 413 | exceeds configured max size |
| `MIME_TYPE_NOT_ALLOWED` | 415 | not on whitelist, or sniffed type mismatches extension |
| `RATE_LIMITED` | 429 | too many uploads from this user in a window |

### `GET /api/v1/files/{file_id}`
Metadata + current `scan_status`. Clients poll this (or listen for a future `file.scanned`
notification — see Open Items) to know when a `pending` upload becomes safe to reference.

**Errors**: `FILE_NOT_FOUND` (404).

### `GET /api/v1/files/{file_id}/download`
Only serves the file if `scan_status="clean"`. Returns a signed, short-lived Supabase Storage URL
rather than proxying bytes through Flask (avoids the API server becoming a file-serving bottleneck —
10_PERFORMANCE_GUIDE.md's profiling/bundle concerns apply here even though it's backend, same
"don't do unnecessary work in the hot path" principle).

**Response `200`**: `{ "data": { "download_url": "https://...", "expires_in": 300 } }`
**Errors**: `FILE_NOT_FOUND` (404), `FILE_NOT_CLEAN` (409 — still pending or flagged infected),
`FILE_INFECTED` (410 — explicit distinct code so the frontend can show a real warning, not a
generic error, if scan came back positive).

Every download also writes an `audit_logs` row (`action="download"`) per Security Guide's explicit
requirement to audit downloads.

---

## Resources (Library Entries)

### `GET /api/v1/library/resources?department_id=&program_id=&subject_id=&q=`
Search/filter/paginate per 08_API_GUIDE.md standards. `q` does a simple title/description search
in v1 (full-text search is a Database Guide "Future Improvement," not blocking v1).

**Response `200`**
```json
{
  "success": true, "message": "OK",
  "data": {
    "items": [
      {
        "id": "uuid", "title": "DBMS Unit 3 Notes", "description": "...",
        "file": { "id": "uuid", "original_filename": "notes.pdf", "mime_type": "application/pdf", "size_bytes": 204800 },
        "subject": { "id": "uuid", "name": "Database Management Systems", "code": "CS303" },
        "uploaded_by": { "id": "uuid", "full_name": "..." },
        "created_at": "..."
      }
    ],
    "page": 1, "page_size": 20, "total": 47
  }
}
```
Only resources whose `file.scan_status="clean"` are returned — a resource pointing at a
still-scanning or infected file is invisible to normal listing (visible to the uploader via a
separate "my uploads" filter so they can see pending state, per Open Items).

### `POST /api/v1/library/resources`
**Request**
```json
{
  "file_id": "uuid",
  "title": "DBMS Unit 3 Notes",
  "description": "...",
  "department_id": "uuid",
  "program_id": "uuid",
  "subject_id": "uuid"
}
```
`department_id`/`program_id`/`subject_id` are all optional (nullable in DATABASE_SCHEMA.md) —
a resource can be scoped as broadly or narrowly as the uploader chooses.

**Service logic**: verify `file_id` belongs to the requesting user (or caller has
`library:manage_any`), verify referenced department/program/subject exist, insert `resources` row.
**Errors**: `FILE_NOT_FOUND` (404), `FILE_NOT_OWNED_BY_USER` (403), `VALIDATION_ERROR` (400).

### `PATCH /api/v1/library/resources/{id}`
Update title/description/scoping. Cannot change `file_id` — that's a new resource, not an edit.
**Authorization**: uploader, or `library:manage_any` permission.

### `DELETE /api/v1/library/resources/{id}`
Soft delete. Note: does **not** delete the underlying `files` row (a file could theoretically be
referenced elsewhere later, and hard-deleting storage on every resource removal is riskier than
necessary) — file cleanup is a separate retention/archival job, not part of this request/response cycle.

---

## Open Items for Backend Implementation Step

- "My uploads" filter (`GET /library/resources?mine=true`) showing the uploader's own resources
  regardless of scan status, so they can see pending/infected state — not detailed above, needs
  its own auth check (owner-only, bypasses the `scan_status=clean` filter).
- Whether a `file.scanned` notification (via the Notifications domain, same pattern as Chat's
  `message.new`) should fire when an async scan completes, so uploaders don't have to poll
  `GET /files/{id}` — natural fit given the Notifications service's generic `type` + `data`
  contract from API_SPEC_NOTIFICATIONS.md; recommend adding at Backend Implementation time.
- Malware scan provider/implementation itself (ClamAV, third-party API, etc.) — not an API design
  concern, but needs deciding before the Celery task in step 7 above can be written.
- Concrete max file size + MIME/extension whitelist values — used generically above; needs actual
  numbers before implementation (e.g. 50MB cap, whitelist: pdf/docx/pptx/xlsx/png/jpg).

---

# API Design Phase — Complete

All 6 domains now have API specs: **Auth**, **RBAC**, **Academic**, **Chat**, **Notifications**,
**Library**. Combined with the Database Design (25 tables, DATABASE_SCHEMA.md) from the previous
step, CampusVault now has a full, internally-consistent contract from data layer through every
REST/socket surface, ready for Backend Implementation (step 5 of the Feature Implementation
Workflow) per 15_FEATURE_IMPLEMENTATION_WORKFLOW.md.

Cross-domain dependencies resolved along the way (all documented in their respective specs):
- Academic sections auto-create/manage Chat groups + membership
- Chat offline delivery creates Notifications rows via direct service call
- Library resource visibility gates on File scan_status
- RBAC's permission middleware contract is referenced, not repeated, by every other domain

Open items collected across all specs (OTP config values, Redis presence scheme, malware scan
provider, section-deletion cascade behavior, file size/MIME whitelist, etc.) should be resolved as
a batch before or during Backend Implementation — none block further design work, but several
should be decided before writing service-layer code.
