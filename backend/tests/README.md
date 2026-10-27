# Backend test suite

Pyramid (docs/10_TESTING_GUIDE.md): unit → integration → E2E.

| Layer        | Location                | Marker          | Notes                          |
| ------------ | ----------------------- | --------------- | ------------------------------ |
| Unit         | `tests/unit/`           | `pytest -m unit`| Pure logic, no DB/network      |
| Integration  | `tests/integration/`    | `pytest -m integration` | Flask test client + in-memory DB |
| E2E          | `/tests/e2e` (repo root)| Playwright      | Real browser against a running stack |

Run:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/test.txt -r requirements/dev.txt
pytest --cov=app
```

Coverage policy: `pyproject.toml` keeps `fail_under` as an explicit ratchet.
Scaffolding baseline is 40%; every Phase-2 feature PR must raise it toward
the 80% Definition-of-Done bar (raise the number with the feature PR).
