# Frontend test suite

The frontend uses Vitest, jsdom, and React Testing Library. Tests are grouped by
the boundary they exercise:

- `ui/`: reusable UI primitives and keyboard/accessibility behavior.
- `components/`: interactive feature components such as the chat composer.
- `pages/`: page-level integration with query state, permissions, and services.
- `hooks/`: query and mutation behavior for persisted chat history.
- `services/`: request construction, filter serialization, and error propagation.
- `stores/`: authentication state and persistence.
- Root-level tests cover shared permission rules.

Run these commands from the frontend package root (`frontend/`), not from `frontend/tests/`:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

For the broader coverage report, run `npm run coverage`. The thresholds in
`vite.config.ts` are a repository-wide gate and should be increased only when
new code is accompanied by meaningful tests.

Frontend permission checks are presentation affordances only. The backend must
continue to authorize every protected API request independently.
