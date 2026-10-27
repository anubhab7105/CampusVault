"""Auth blueprint — student Google OAuth + teacher OTP + token lifecycle."""

from __future__ import annotations

import secrets
import uuid

from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.constants import DEFAULT_AUTH_RATE_LIMIT
from app.extensions import limiter
from app.middleware.auth import ensure_authenticated, require_csrf_token
from app.schemas.auth_schema import (
    LogoutSchema,
    OAuthExchangeSchema,
    RefreshTokenSchema,
    TeacherRequestOtpSchema,
    TeacherVerifyOtpSchema,
)
from app.services.auth_service import auth_service
from app.services.token_service import TokenService
from app.utils.responses import success_response
from app.utils.validation import get_json_body, load_schema

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.get("/google/authorize")
@limiter.limit(DEFAULT_AUTH_RATE_LIMIT)
def google_authorize():
    """Return the Google consent-screen URL for the SPA to open."""
    state = secrets.token_urlsafe(16)
    return success_response(
        data={"authorize_url": auth_service.build_google_authorize_url(state), "state": state},
        message="Open the authorize_url in a browser context.",
    )


@bp.post("/google")
@limiter.limit(DEFAULT_AUTH_RATE_LIMIT)
def google_callback():
    """Exchange the consent-screen code for CampusVault tokens."""
    body = load_schema(OAuthExchangeSchema(), get_json_body())
    result = auth_service.login_student_with_code(code=body["code"])
    return success_response(data=result, message="Signed in with Google.")


@bp.post("/teachers/otp/request")
@limiter.limit(DEFAULT_AUTH_RATE_LIMIT)
def teacher_request_otp():
    """Phase 1 — queue the OTP email (same response shape for all emails)."""
    body = load_schema(TeacherRequestOtpSchema(), get_json_body())
    ttl = auth_service.request_teacher_otp(email=body["email"])
    return success_response(
        data={"expires_in_seconds": ttl}, message="Verification code sent if the account exists."
    )


@bp.post("/teachers/otp/verify")
@limiter.limit(DEFAULT_AUTH_RATE_LIMIT)
def teacher_verify_otp():
    """Phase 2 — exchange the OTP for a token pair."""
    body = load_schema(TeacherVerifyOtpSchema(), get_json_body())
    result = auth_service.verify_teacher_otp(email=body["email"], code=body["code"])
    return success_response(data=result, message="Signed in.")


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """Rotate the refresh token; returns a fresh access + refresh pair."""
    # CSRF protection for state-changing refresh endpoint.
    require_csrf_token()
    tokens = TokenService.rotate()
    return success_response(data={"tokens": tokens}, message="Session refreshed.")


@bp.post("/logout")
@jwt_required(refresh=True)
def logout():
    """Revoke the presented refresh token (jti blocklist)."""
    TokenService.revoke_current_refresh()
    return success_response(message="Signed out.")


@bp.get("/me")
def me():
    """Echo the authenticated identity + role claims from the access token."""
    user_id = ensure_authenticated()
    from app.services.role_service import role_service

    role, permissions = role_service.load_user_role_bundle(uuid.UUID(user_id))
    return success_response(
        data={"id": user_id, "role": role, "permissions": permissions},
        message="Identity loaded.",
    )
