"""HTTP security headers applied to every response (defense in depth)."""

from __future__ import annotations

from flask import Flask, Response

HEADER_X_CONTENT_TYPE = ("X-Content-Type-Options", "nosniff")
HEADER_X_FRAME = ("X-Frame-Options", "DENY")
HEADER_REFERRER = ("Referrer-Policy", "strict-origin-when-cross-origin")
HEADER_CSP = (
    "Content-Security-Policy",
    "default-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'",
)
HEADER_CROSS_ORIGIN_OPENER = ("Cross-Origin-Opener-Policy", "same-origin")
HEADER_PERMISSIONS = (
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=(), payment=()",
)
HEADER_CACHE = ("Cache-Control", "no-store")

SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    HEADER_X_CONTENT_TYPE,
    HEADER_X_FRAME,
    HEADER_REFERRER,
    HEADER_CSP,
    HEADER_CROSS_ORIGIN_OPENER,
    HEADER_PERMISSIONS,
    HEADER_CACHE,
)


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def _apply(response: Response) -> Response:
        for name, value in SECURITY_HEADERS:
            response.headers[name] = value
        return response
