"""JSON response envelope builders.

Success: {"success": true,  "message": "...", "data": {...}}
Failure: {"success": false, "error": {"code": "...",   "message": "..."}}

Every route in the codebase returns through these helpers so the wire format
stays identical (docs/08_API_GUIDE.md).
"""

from __future__ import annotations

from typing import Any

from flask import jsonify
from flask.typing import ResponseReturnValue

API_META_HEADER = "X-Request-ID"


def success_response(
    data: Any = None,
    message: str = "Operation completed.",
    *,
    status_code: int = 200,
    paging: dict[str, Any] | None = None,
) -> ResponseReturnValue:
    """Build the canonical success envelope."""
    payload: dict[str, Any] = {"success": True, "message": message, "data": data or {}}
    if paging is not None:
        payload["paging"] = paging
    response = jsonify(payload)
    response.status_code = status_code
    return response


def error_response(
    code: str,
    message: str,
    *,
    status_code: int = 400,
    details: dict[str, Any] | None = None,
) -> ResponseReturnValue:
    """Build the canonical error envelope. Never includes stack traces."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    response = jsonify({"success": False, "error": error})
    response.status_code = status_code
    return response
