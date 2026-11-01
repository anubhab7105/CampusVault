"""Centralized rate-limit policies and keying.

Single source of truth for all rate limits (PRD FR-AUTH-05, NFR 9.1,
PRD §14.10).

Keying rules:
- Authenticated routes: ``user:<user_id>`` from the JWT, with an IP
  fallback when no valid token is present.
- Unauthenticated routes: ``ip:<addr>`` only.
- When ``TRUST_PROXY`` is enabled and the immediate ``remote_addr`` is a
  trusted proxy, the leftmost ``X-Forwarded-For`` entry is used.  This is
  safe because the header is only consulted for verified proxies, so an
  untrusted client cannot spoof another user's IP.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import wraps
from typing import Final

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity


# --------------------------------------------------------------------------- #
# Policy constants (all configurable via environment variables)
# --------------------------------------------------------------------------- #

def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


RATELIMIT_DEFAULT: Final[str] = _env("RATELIMIT_DEFAULT", "100/minute")
RATELIMIT_AUTH: Final[str] = _env("RATELIMIT_AUTH", "5/minute")
RATELIMIT_SEARCH: Final[str] = _env("RATELIMIT_SEARCH", "30/minute")
RATELIMIT_CHAT_MESSAGE: Final[str] = _env("RATELIMIT_CHAT_MESSAGE", "30/minute")
RATELIMIT_UPLOAD: Final[str] = _env("RATELIMIT_UPLOAD", "10/minute")
RATELIMIT_DOWNLOAD: Final[str] = _env("RATELIMIT_DOWNLOAD", "30/minute")
RATELIMIT_ADMIN_WRITE: Final[str] = _env("RATELIMIT_ADMIN_WRITE", "30/minute")
RATELIMIT_ADMIN_READ: Final[str] = _env("RATELIMIT_ADMIN_READ", "30/minute")

# Socket limits use flask-limiter-compatible strings where the window can be
# sub-minute (e.g. "30/30seconds").  These are applied in-process for socket
# events via the Redis token bucket in ``app/sockets/events.py``.
RATELIMIT_SOCKET_MESSAGE: Final[str] = _env("RATELIMIT_SOCKET_MESSAGE", "30/30seconds")
RATELIMIT_SOCKET_JOIN: Final[str] = _env("RATELIMIT_SOCKET_JOIN", "60/minute")
RATELIMIT_SOCKET_TYPING: Final[str] = _env("RATELIMIT_SOCKET_TYPING", "20/10seconds")
RATELIMIT_SOCKET_EDIT: Final[str] = _env("RATELIMIT_SOCKET_EDIT", "30/minute")
RATELIMIT_SOCKET_DELETE: Final[str] = _env("RATELIMIT_SOCKET_DELETE", "20/minute")
RATELIMIT_SOCKET_LEAVE: Final[str] = _env("RATELIMIT_SOCKET_LEAVE", "10/minute")
RATELIMIT_SOCKET_READ: Final[str] = _env("RATELIMIT_SOCKET_READ", "60/minute")
RATELIMIT_SOCKET_DELIVERY: Final[str] = _env("RATELIMIT_SOCKET_DELIVERY", "60/minute")

TRUST_PROXY: Final[bool] = os.environ.get("TRUST_PROXY", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
TRUSTED_PROXIES: Final[frozenset[str]] = frozenset(
    part.strip()
    for part in os.environ.get("TRUSTED_PROXIES", "127.0.0.1,::1").split(",")
    if part.strip()
)


# --------------------------------------------------------------------------- #
# Key function
# --------------------------------------------------------------------------- #

def rate_limit_key() -> str:
    """Return the rate-limit key for the current request.

    Authenticated requests are keyed on ``user:<user_id>`` taken from the
    verified JWT.  When no valid token is present (unauthenticated route or
    invalid credentials) the request is keyed on ``ip:<addr>`` instead.
    Trusted-proxy ``X-Forwarded-For`` handling applies only when
    ``TRUST_PROXY`` is enabled and the immediate ``remote_addr`` is listed
    in ``TRUSTED_PROXIES``.
    """
    # Authenticated user takes precedence.
    try:
        identity = get_jwt_identity()
        if identity:
            return f"user:{identity}"
    except Exception:
        # No valid JWT context — fall through to IP keying.
        pass

    return f"ip:{_client_ip()}"


def _client_ip() -> str:
    remote_addr = request.remote_addr or ""
    if TRUST_PROXY and remote_addr in TRUSTED_PROXIES:
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            # Leftmost entry is the original client.  Safe to trust because
            # remote_addr is a verified proxy.
            return xff.split(",")[0].strip()
    return remote_addr


# --------------------------------------------------------------------------- #
# Decorator: applies flask-limiter and tags the view for coverage tests
# --------------------------------------------------------------------------- #

_RATE_LIMITED_ATTR = "_cv_rate_limited"
_LIMIT_STRING_ATTR = "_cv_rate_limit_string"


def cv_rate_limit(limit_string: str) -> Callable:
    """Apply a flask-limit *and* tag the view as rate-limited for coverage tests.

    Use this in place of ``@limiter.limit(...)`` so the route-enumeration
    test can verify every required route carries a limiter.
    """

    def decorator(f: Callable) -> Callable:
        # Lazy import to avoid a circular import (extensions.py imports this
        # module, and this module needs the limiter instance).
        from app.extensions import limiter as _limiter

        wrapped = _limiter.limit(limit_string)(f)
        setattr(wrapped, _RATE_LIMITED_ATTR, True)
        setattr(wrapped, _LIMIT_STRING_ATTR, limit_string)
        return wrapped

    return decorator


def is_rate_limited(view_func: Callable) -> bool:
    """Whether ``view_func`` was decorated with :func:`cv_rate_limit`."""
    return bool(getattr(view_func, _RATE_LIMITED_ATTR, False))


def limit_string_for(view_func: Callable) -> str | None:
    """The configured limit string for a rate-limited view, if any."""
    return getattr(view_func, _LIMIT_STRING_ATTR, None)


# --------------------------------------------------------------------------- #
# Route sets for the automated route-coverage test
# --------------------------------------------------------------------------- #

# Routes that are intentionally *not* rate limited (infrastructure probes,
# documentation).  Adding a route here requires a code-review justification.
EXEMPT_ROUTES: Final[frozenset[str]] = frozenset(
    {
        # Infrastructure probes — not user traffic; rate limiting at the edge
        # (Nginx / platform) instead.
        "health.liveness",
        "health.readiness",
        # Documentation.
        "docs.openapi_json",
        "docs.swagger_ui",
    }
)

# Routes that REQUIRE rate limiting.  The route-coverage test fails if any
# route in this set lacks a ``@cv_rate_limit`` decorator.  Adding a new
# sensitive endpoint without a limiter must make this test fail.
REQUIRED_RATE_LIMITED_ROUTES: Final[frozenset[str]] = frozenset(
    {
        # --- Auth (PRD FR-AUTH-05, §14.10) -------------------------------- #
        "auth.google_authorize",
        "auth.google_callback",
        "auth.teacher_request_otp",
        "auth.teacher_verify_otp",
        "auth.refresh",
        "auth.logout",
        "auth.me",
        # --- Library / files (PRD FR-FILE-01, FR-SEARCH-04, §14.5, §14.10) #
        "library.request_upload",
        "library.finalize_upload",
        "library.browse_resources",
        "library.download_resource",
        "library.my_uploads",
        "files.register_upload",
        "files.get_file",
        # --- Chat (PRD FR-CHAT-04, §14.10) -------------------------------- #
        "chat.history",
        "chat.send_group_message",
        "chat.open_dm",
        "chat.mark_read",
        # --- Groups ------------------------------------------------------- #
        "groups.create_group",
        "groups.my_groups",
        "groups.get_group",
        "groups.add_member",
        "groups.leave_group",
        "groups.transfer_ownership",
        "groups.change_member_role",
        "groups.list_members",
        # --- Admin writes (PRD FR-ADMIN-02, §14.13) ---------------------- #
        "admin.deactivate_user",
        "admin.reactivate_user",
        "admin.assign_user_role",
        "admin.remove_user_role",
        "admin.department_create",
        "admin.department_update",
        "admin.department_delete",
        "admin.program_create",
        "admin.program_update",
        "admin.section_create",
        "admin.group_archive",
        "admin.group_reassign_owner",
        "admin.resource_unpublish",
        "admin.resource_soft_delete",
        "admin.allowlist_add",
        "admin.allowlist_remove",
        "admin.allowlist_approve",
        "admin.moderation_confirm_delete",
        # --- Users -------------------------------------------------------- #
        "users.get_me",
        "users.list_users",
        # --- Academic writes ---------------------------------------------- #
        "academic.create_department",
        "academic.create_program",
        "academic.create_semester",
        "academic.create_section",
        "academic.create_subject",
        # --- RBAC writes -------------------------------------------------- #
        "rbac.grant_permissions",
        "rbac.revoke_permission",
        "rbac.assign_role",
        # --- Notifications ------------------------------------------------ #
        "notifications.mark_read",
        "notifications.mark_all_read",
    }
)

__all__ = [
    "RATELIMIT_DEFAULT",
    "RATELIMIT_AUTH",
    "RATELIMIT_SEARCH",
    "RATELIMIT_CHAT_MESSAGE",
    "RATELIMIT_UPLOAD",
    "RATELIMIT_DOWNLOAD",
    "RATELIMIT_ADMIN_WRITE",
    "RATELIMIT_ADMIN_READ",
    "RATELIMIT_SOCKET_MESSAGE",
    "RATELIMIT_SOCKET_JOIN",
    "RATELIMIT_SOCKET_TYPING",
    "RATELIMIT_SOCKET_EDIT",
    "RATELIMIT_SOCKET_DELETE",
    "RATELIMIT_SOCKET_LEAVE",
    "RATELIMIT_SOCKET_READ",
    "RATELIMIT_SOCKET_DELIVERY",
    "TRUST_PROXY",
    "TRUSTED_PROXIES",
    "rate_limit_key",
    "cv_rate_limit",
    "is_rate_limited",
    "limit_string_for",
    "EXEMPT_ROUTES",
    "REQUIRED_RATE_LIMITED_ROUTES",
]
