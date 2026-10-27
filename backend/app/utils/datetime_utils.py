"""UTC datetime helpers.

The database (and Supabase PostgreSQL) stores timestamps in UTC. These helpers
are the only place where "now" is borrowed, so tests can freeze time cleanly.
"""

from __future__ import annotations

import datetime as dt

UTC = dt.UTC


def utcnow() -> dt.datetime:
    """Timezone-aware current time in UTC."""
    return dt.datetime.now(tz=UTC)


def utcnow_iso() -> str:
    """ISO-8601 string (seconds precision, Z suffix) for envelopes/logs."""
    return utcnow().isoformat(timespec="seconds").replace("+00:00", "Z")
