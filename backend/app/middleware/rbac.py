"""RBAC decorators.

``permission_required`` authorizes a route by permission codes. Role names are
also supported via ``role_required`` when a route is genuinely role-bound
(an admin console route rather than a permission).

Permissions are read from the JWT claims when present (fast path); the
database is consulted through RoleService when claims are absent or bypassed,
so permissions stay authoritative.
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

            # Fast path: if the JWT carries role + permissions, use them directly.
            role_name = claims.get(CLAIMS_ROLE)
            if role_name == ROLE_ADMIN:
                # Admin implicitly holds all permissions — skip further checks.
                return view(*args, **kwargs)

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


def last_admin_protected() -> Callable:
    """Decorator for admin-only actions that must not demote the last admin.

    Usage::

        @bp.post("/admin/users/<user_id>/deactivate")
        @last_admin_protected()
        def deactivate_user(user_id): ...

    The view function receives ``user_id`` as a keyword argument and should
    check ``request.current_user_id`` (or equivalent) before proceeding.
    """
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            verify_jwt_in_request(optional=False)
            # Identify the user to be acted upon and the acting admin.
            target_user_id = kwargs.get("user_id")
            if not target_user_id:
                raise ForbiddenError("user_id is required for this decorator.")

            # Check if the target user is an Admin.
            from app.models import Role, UserRole

            target_is_admin = (
                db.session.query(UserRole)
                .join(Role, UserRole.role_id == Role.id)
                .filter(UserRole.user_id == target_user_id, Role.name == "Admin")
                .count()
                > 0
            )

            # Count total admins in the system.
            total_admins = (
                db.session.query(UserRole)
                .join(Role, UserRole.role_id == Role.id)
                .filter(Role.name == "Admin")
                .count()
            )

            # If the target is an admin and they are the last one, block the action.
            if target_is_admin and total_admins <= 1:
                raise ForbiddenError("The last admin cannot be demoted or deactivated.")

            return view(*args, **kwargs)

        return wrapper

    return decorator
