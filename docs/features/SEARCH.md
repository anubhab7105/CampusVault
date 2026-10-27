# Search Feature

## Unified Search Endpoint

**`GET /api/v1/library/search`** — returns permission-aware results across
resources (and groups the user may see). Combines full-text search, filtering,
ranking, and typo tolerance in a single request.

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `q` | `string` (required) | Free-text search query. |
| `resource_type` | `string` (optional) | Filter by resource type (`pdf`, `image`, `video`, etc.). |
| `visibility` | `string` (optional) | Filter by visibility (`college`, `public`, `private`). |
| `department_id` | `uuid` (optional) | Filter by department. |
| `program_id` | `uuid` (optional) | Filter by program. |
| `semester_id` | `uuid` (optional) | Filter by semester. |
| `section_id` | `uuid` (optional) | Filter by section. |
| `subject_id` | `uuid` (optional) | Filter by subject. |
| `published` | `boolean` (optional) | If `true`, only show published resources. |
| `sort` | `string` (optional) | Sort field: `title`, `download_count`, `view_count`, `created_at`. Default: `created_at`. |
| `order` | `string` (optional) | `asc` or `desc`. Default: `desc`. |
| `page` | `integer` (optional) | Page number. Default: `1`. |
| `page_size` | `integer` (optional) | Items per page. Max `100`. Default: `20`. |

### Response Envelope

```json
{
  "success": true,
  "message": "Search results.",
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "string",
        "description": "string",
        "resource_type": "string",
        "visibility": "string",
        "uploader_name": "string",
        "download_count": 0,
        "view_count": 0,
        "scan_status": "clean|infected|failed|pending",
        "created_at": "iso-date",
        "highlight": "string",  // HTML-escaped snippet with search terms highlighted
        "matched_in": ["title", "description"]  // which fields matched
      }
    ],
    "total": 0,
    "page": 1,
    "page_size": 20
  }
}
```

### Search Logic

1. **Full‑text search (PostgreSQL)**:
   - The `resources` table has a `fts` column (`TSVector`) with a `GIN` index
   - Query: `to_tsquery('english', :query)` + `ts_rank` for relevance scoring
   - Ranked via `ts_rank_cvs(fts, to_tsquery('english', :query))` — higher is better

2. **Typo tolerance (PostgreSQL via `pg_trgm`)**:
   - If `pg_trgm` is installed, use `similarity(title || ' ' || description, :query) > 0.3` as a fallback
   - On SQLite (no `pg_trgm`), fall back to `LIKE` with `%` wildcards on `title` and `description`

3. **Permission‑aware filtering** (critical — never leak resources user cannot access):
   - The repository layer determines the user's visible departments, programs, semesters,
     sections, and subjects based on their role and group memberships:
     - **Student**: own department + public resources (`visibility='public'`)
     - **Teacher**: their department + their groups' resources
     - **Admin**: all resources
   - The `WHERE` clause enforces these filters at the SQL level; the application
     never materializes disallowed resources and then filters them.

4. **Result assembly**:
   - FTS‑ranked results are combined with any filter‑only results (e.g., a resource
     that matches the department filter but has lower FTS relevance)
   - Duplicates are deduplicated by `resource.id`
   - Each item includes a `highlight` field: the first 120 characters of the
     title or description with search terms wrapped in `<mark>` (HTML-escaped so
     the frontend can safely render it). If FTS is unavailable, the highlight
     falls back to the first 120 chars with `...` appended.

### Error Handling

- `q` missing or empty → `400 VALIDATION_ERROR` ("Search query is required.")
- No results → empty `items` array with `total: 0`
- Server-side FTS failure → fallback to `LIKE` query; if that also fails,
  return `500 SERVICE_UNAVAILABLE` with a descriptive message

### Example Requests

**Basic text search:**

```bash
curl "http://localhost:8000/api/v1/library/search?q=python"
```

**Search with filters:**

```bash
curl "http://localhost:8000/api/v1/library/search?q=django&department_id=5&published=true&sort=created_at&order=desc"
```

**Typo-tolerant search (PostgreSQL with pg_trgm):**

```bash
curl "http://localhost:8000/api/v1/library/search?q=ython"  # matches "python" via similarity
```

## Frontend: Global Search Bar

### Component Structure

```
SearchBar
  └─ input (type=text, aria-label="Search")
  └─ recent-chips (localStorage, max 10, clearable)
  └─ results-grid (conditional rendering)
```

### Behavior

- **Debounce**: 300ms on input keystrokes before triggering the fetch request
- **Keyboard shortcut**: `Cmd/Ctrl + K` focuses the search input (if focused elsewhere)
- **Recent searches**: stored client-side in `localStorage` under key
  `campusvault_search_history`, max 10 entries, oldest auto-removed, clearable
  with a single "clear all" button
- **Grouped results**: results are displayed in two sections:
  - **Resources** (labeled, with scan_status badge)
  - **Groups** (labeled, with member count badge) — only groups the user is
    permitted to see
- **Empty state**: "No results found. Try different keywords or check filters."
- **Error state**: "Search temporarily unavailable. Please try again later."
- **Accessibility**:
  - `aria-label="Search"` on the input
  - `aria-live="polite"` on the results region
  - ESC closes the search panel
  - Focus returns to the previous element on close

### API Integration (frontend hook)

```typescript
// hooks/useSearch.ts (to be implemented)
const { data, isLoading, error, search } = useSearch(query, debounceTime);
```

The hook performs a `fetch('/api/v1/library/search?q=' + query)` with the
appropriate query parameters, handles the response envelope, and returns the
`data.items`, `data.total`, and loading/error state.

## Search Polish — Design Decisions

1. **FTS over LIKE**: On PostgreSQL, the `tsvector` + `GIN` index gives
   sub‑millisecond search on hundreds of thousands of resources. On SQLite, the
   fallback `LIKE` is slower but functional for small datasets.
2. **Permission filtering at the SQL level**: Prevents any data leak; the
   application never "just queries everything and filters client-side" for
   resources/groups. This is the strongest guard against IDOR in the search
   domain.
3. **Highlight HTML-escaped**: The `highlight` field uses `html.escape()` on the
   wrapped `<mark>` tags. The frontend renders it as `innerHTML`, which is safe
   because the escaping happens server‑side.
4. **Typo tolerance via pg_trgm**: Adds a better user experience when users
   misspell search terms; on SQLite the trade-off is a broader `LIKE` fallback.
5. **Grouped results UX**: Separating resources from groups helps users who may
   be looking for either a learning material or a discussion forum; both are
   valuable in an academic SaaS context.

## Performance

- **Index usage**: The `idx_resources_fts` GIN index ensures FTS queries are
  fast (sub-second even at 100k+ resources).
- **Filter pushdown**: Department, program, semester, section, subject, and
  visibility filters are all `WHERE` clauses that the PostgreSQL planner can
  optimize with existing B-tree indexes on those columns.
- **No N+1**: The entire query (FTS + filters + pagination) is a single SQL
  statement; the ORM fetches only the DTO fields needed for the response.
- **Target**: p95 latency < 300ms on a seeded dataset of 10k resources with
  mixed FTS queries and filters (record in `docs/PERFORMANCE_RESULTS.md`).