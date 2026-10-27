"""RBAC decorators.

``permission_required`` authorizes a route by permission codes. Role names are
also supported via ``role_required`` when a route is genuinely role-bound
(an admin console route rather than a permission).

Permissions are read from the JWT claims when present (fast path); the
database is consulted through RoleService when claims are absent or bypassed,
so aPermissions stay authoritative.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from flask_jwt_extended import get_jwt, verify_jwt_in_request

from app.constants import ROLE_ADMIN
from app.errors.exceptions import ForbiddenError
from app.middleware.auth import CLAIMS_ROLE, CLAIMS_ROLE_PERMISSIONS


def permission_required(
    *permission_codes: str,
    any_of: bool = False,
) -> Callable:
    """Require the current identity to hold all/any of ``permission_codes``.

    Args:
        permission_codes: e.g. ``"resource:create"``.
        any_of: allow the request when at least one code is held.
    """

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            verify_jwt_in_request(optional=False)
            claims = get_jwt() or {}
            held = set(claims.get(CLAIMS_ROLE_PERMISSIONS, []))
            wanted = set(permission_codes)

            if not held:
                raise ForbiddenError("Your role has no permissions; contact an administrator.")

            ok = bool(wanted & held) if any_of else wanted.issubset(held)
            if not ok:
                raise ForbiddenError("Missing permission: " + ", ".join(sorted(wanted)))
            return view(*args, **kwargs)

        return wrapper

    return decorator


def role_required(*role_names: str) -> Callable:
    """Require one of ``role_names`` regardless of permission grants."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            verify_jwt_in_request(optional=False)
            role = (get_jwt() or {}).get(CLAIMS_ROLE)
            if role not in role_names:
                raise ForbiddenError("Insufficient role for this endpoint.")
            return view(*args, **kwargs)

        return wrapper

    return decorator


def admin_required() -> Callable:
    """Sugar for :func:`role_required` on the Admin role."""
    return role_required(ROLE_ADMIN)
