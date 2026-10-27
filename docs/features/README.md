# Feature documentation index

Each feature has a document describing its models, routes, events, tests, and
security posture. Update `docs/00_PROJECT_MEMORY.md` after every completed
feature (locked workflow, docs/15_FEATURE_IMPLEMENTATION_WORKFLOW.md).

| Feature | Document | Status |
| ------- | -------- | ------ |
| Authentication | docs/features/AUTH.md | scaffolding |
| RBAC | docs/features/RBAC.md | pending |
| Academic structure | docs/features/ACADEMIC.md | pending |
| Groups | docs/features/GROUPS.md | pending |
| Chat | docs/features/CHAT.md | pending |
| Library / resources | docs/features/LIBRARY.md | pending |
| Files / uploads | docs/features/FILES.md | pending |
| Notifications | docs/features/NOTIFICATIONS.md | pending |
| Admin | docs/features/ADMIN.md | pending |
| Audit logs | docs/features/AUDIT.md | pending |
| Deployment | docs/features/DEPLOYMENT.md | pending |

Template for a new feature doc:

```markdown
# <Feature>

## Overview
One paragraph.

## Database
Tables involved; indexes; soft-delete status.

## API
Endpoints with method, path, auth requirement, request/response schemas.

## Real-time (if applicable)
Socket events, rooms, authorization rules.

## Security
Validation, rate limits, audit events.

## Tests
Unit/integration coverage locations.

## Done checklist
- [ ] models + migration
- [ ] repository + service
- [ ] blueprint + schema validation
- [ ] frontend page + components
- [ ] docs/00_PROJECT_MEMORY.md updated
```
