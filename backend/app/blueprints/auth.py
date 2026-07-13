"""
Auth blueprint. Routes stay thin per 04_BACKEND_GUIDE.md: "Controllers
remain thin. Business logic belongs in services." Every handler here does
only: parse+validate request -> call service -> format response.
"""
from flask import Blueprint, g, request

from app.schemas.auth import (
    GoogleLoginRequest,
    LogoutRequest,
    OTPRequestSchema,
    OTPVerifySchema,
    RefreshTokenRequest,
    TokenPair,
    UserProfile,
    UserPublic,
)
from app.services.auth_service import AuthService
from app.middleware.auth_middleware import require_auth
from app.utils.responses import success

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _get_service() -> AuthService:
    from flask import current_app
    return AuthService(db=current_app.extensions["db_session"]())


def _device_info() -> str:
    return request.headers.get("User-Agent", "")[:255]


def _token_response(result: dict) -> dict:
    return TokenPair(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=result["expires_in"],
        user=UserPublic.model_validate(result["user"]),
    ).model_dump(mode="json")


@auth_bp.post("/student/google")
def student_google_login():
    payload = GoogleLoginRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    result = service.login_student_google(payload.id_token, device_info=_device_info())
    return success(_token_response(result), message="Login successful.")


@auth_bp.post("/teacher/otp/request")
def teacher_otp_request():
    payload = OTPRequestSchema.model_validate(request.get_json(force=True))
    service = _get_service()
    service.request_teacher_otp(payload.email)
    # Always the same message regardless of whether the account exists — API_SPEC_AUTH.md.
    return success({}, message="If an account exists, a code has been sent.")


@auth_bp.post("/teacher/otp/verify")
def teacher_otp_verify():
    payload = OTPVerifySchema.model_validate(request.get_json(force=True))
    service = _get_service()
    result = service.verify_teacher_otp(payload.email, payload.code, device_info=_device_info())
    return success(_token_response(result), message="Login successful.")


@auth_bp.post("/refresh")
def refresh_token():
    payload = RefreshTokenRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    result = service.refresh(payload.refresh_token, device_info=_device_info())
    return success(_token_response(result), message="Token refreshed.")


@auth_bp.post("/logout")
@require_auth
def logout():
    payload = LogoutRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    service.logout(payload.refresh_token)
    return success({}, message="Logged out.")


@auth_bp.get("/me")
@require_auth
def me():
    service = _get_service()
    result = service.get_current_user_profile(g.user_id)
    profile = UserProfile(
        **UserPublic.model_validate(result["user"]).model_dump(),
        roles=result["roles"],
    )
    return success(profile.model_dump(mode="json"))
