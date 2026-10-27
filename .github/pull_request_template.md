# Pull Request Template — CampusVault

## Summary
Briefly describe the change and the feature it belongs to.

## Related issue
Closes #issue-number

## Checklist
- [ ] Requirement analysis documented (affected modules, DB + security impact)
- [ ] Architecture reviewed against locked tech stack (no new technologies)
- [ ] Database changes via Alembic migration (models + indexes)
- [ ] Backend: service + repository + blueprint, schema validation
- [ ] Frontend: form stack is React Hook Form + Zod only
- [ ] Tests: unit + integration added; coverage gate respected
- [ ] Real-time: socket events authorized + payload validated (if chat/notifications)
- [ ] Security review: secrets not hardcoded, headers + rate limits intact
- [ ] Documentation: docs/00_PROJECT_MEMORY.md updated, feature doc added
- [ ] UI: responsive, WCAG-aware, dark mode checked

## Conventional commit message
feat(<module>): <description>

## Reviewer
@backend-team @frontend-team (as applicable)
