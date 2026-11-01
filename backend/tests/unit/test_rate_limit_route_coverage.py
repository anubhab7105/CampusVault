"""Route-coverage test for rate limiting.

Fails when any route in ``REQUIRED_RATE_LIMITED_ROUTES`` lacks a
``@cv_rate_limit`` decorator.  Adding a new sensitive endpoint without a
limiter must make this test fail.

Routes in ``EXEMPT_ROUTES`` are intentionally excluded.
"""

from __future__ import annotations

from app.utils.rate_limit import (
    EXEMPT_ROUTES,
    REQUIRED_RATE_LIMITED_ROUTES,
    is_rate_limited,
)


def test_all_required_routes_are_rate_limited(app):
    """Every route in REQUIRED_RATE_LIMITED_ROUTES must carry @cv_rate_limit."""
    missing = []
    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint
        if endpoint in EXEMPT_ROUTES:
            continue
        if endpoint in REQUIRED_RATE_LIMITED_ROUTES:
            view_func = app.view_functions.get(endpoint)
            if view_func is None:
                missing.append(f"{endpoint} ({rule.rule}): no view function registered")
                continue
            if not is_rate_limited(view_func):
                missing.append(
                    f"{endpoint} ({rule.rule}): missing @cv_rate_limit decorator"
                )

    assert not missing, (
        "The following required routes are not rate limited:\n" + "\n".join(missing)
    )


def test_exempt_routes_are_not_required(app):
    """Exempt routes must not appear in the required set (no overlap)."""
    overlap = EXEMPT_ROUTES & REQUIRED_RATE_LIMITED_ROUTES
    assert not overlap, f"Routes in both EXEMPT and REQUIRED: {overlap}"


def test_required_routes_have_limit_strings(app):
    """Every rate-limited required route must have a non-empty limit string."""
    from app.utils.rate_limit import limit_string_for

    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint
        if endpoint in REQUIRED_RATE_LIMITED_ROUTES:
            view_func = app.view_functions.get(endpoint)
            assert view_func is not None, f"{endpoint}: no view function"
            assert is_rate_limited(view_func), f"{endpoint}: not rate limited"
            limit_str = limit_string_for(view_func)
            assert limit_str, f"{endpoint}: empty limit string"
