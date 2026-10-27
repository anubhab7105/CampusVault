# Frontend test suite

Pyramid (docs/10_TESTING_GUIDE.md): unit → integration → E2E.

| Layer     | Command                      | Notes                        |
| --------- | ---------------------------- | ---------------------------- |
| Unit      | `vitest run`                 | jsdom + React Testing Library|
| E2E       | `npx playwright test`        | `/tests/e2e` (repo root)     |

Run:

```bash
cd frontend
npm ci
npm test            # vitest run
npm run lint        # eslint
npm run build       # tsc + vite build
```

Coverage gate: 80% lines/functions/statements, 70% branches
(see `vitest` section of `vite.config.ts`).
