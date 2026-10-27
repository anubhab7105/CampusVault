"""JSON logging helpers (single-line, parseable, secret-free)."""

from __future__ import annotations

import json
import logging
from typing import Any

_json_logger = logging.getLogger("campusvault.request")


def log_json(level: int, event: str, **fields: Any) -> None:
    """Emit one structured JSON log line.

    Values that are duplicated or high-cardinality secrets must never be
    included as field names; callers own that responsibility.
    """
    payload = {"event": event, **fields}

    def _default(obj: Any) -> str:
        return repr(obj)

    _json_logger.log(level, json.dumps(payload, default=_default, separators=(",", ":")))
