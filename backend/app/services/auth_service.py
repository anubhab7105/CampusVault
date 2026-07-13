"""
Auth domain service. Implements the service logic specified in
API_SPEC_AUTH.md. Blueprints call these methods; repositories are the only
things this file talks to for persistence (04_BACKEND_GUIDE.md: "Business
logic belongs in services").

Config values (OTP length/expiry, token TTLs) come from OPEN_DECISIONS.md
defaults via app.utils.security.
"""
import logging
import uuid
from datetime import timedelta

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.models.auth import UserType
from app.repositories.auth_repository import AuthRepository
from app.repositories.rbac_repository import RBACRepository
from app.utils.exceptions import ForbiddenError, RateLimitedError, UnauthorizedError
from app.utils.security import (
    OTP_MAX_ATTEMPTS,
    OTP_TTL_SECONDS,
    REFRESH_TOKEN_TTL_SECONDS,
    constant_time_compare,
    create_access_token,
    generate_opaque_token,
    generate_otp_code,
    hash_secret,
    now_utc,
)

logger = logging.getLogger("campusvault.auth")

GOOGLE_CLIENT_ID = None  # set via config/env at app factory init; injected for testability


class AuthService:
    def __init__(self, db: Session, google_client_id: str | None = None):
        self.db = db
        self.repo = AuthRepository(db)
        self.rbac_repo = RBACRepository(db)
        self.google_client_id = google_client_id or GOOGLE_CLIENT_ID

    # ---------- Shared token issuance ----------

    def _issue_tokens(self, user, device_info: str | None = None) -> dict:
        roles = self.rbac_repo.get_role_names_for_user(user.id)
        access_token, expires_in = create_access_token(user.id, user.user_type.value, roles)

        raw_refresh = generate_opaque_token()
        now = now_utc()
        self.repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_secret(raw_refresh),
            issued_at=now,
            expires_at=now + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS),
            device_info=device_info,
        )

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "expires_in": expires_in,
            "user": user,
        }

    # ---------- Student: Google OAuth ----------

    def login_student_google(self, id_token_str: str, device_info: str | None = None) -> dict:
        try:
            claims = google_id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), self.google_client_id
            )
        except ValueError:
            raise UnauthorizedError("Invalid Google token.", code="INVALID_GOOGLE_TOKEN")

        google_sub = claims["sub"]
        google_email = claims["email"]

        identity = self.repo.get_student_identity_by_google_sub(google_sub)
        if identity is None:
            # First login for this student — create User + StudentIdentity together.
            user = self.repo.create_user(
                email=google_email,
                full_name=claims.get("name", google_email),
                user_type=UserType.STUDENT,
            )
            self.repo.create_student_identity(user.id, google_sub, google_email)
        else:
            user = self.repo.get_user_by_id(identity.user_id)

        if user is None or not user.is_active:
            raise ForbiddenError("Account is deactivated.", code="ACCOUNT_DEACTIVATED")

        self.db.commit()
        return self._issue_tokens(user, device_info)

    # ---------- Teacher: OTP ----------

    def request_teacher_otp(self, email: str) -> None:
        """
        Always succeeds from the caller's perspective (per API_SPEC_AUTH.md:
        never reveal whether an account exists). Only actually sends/creates
        a code if a matching teacher_identity is found.
        """
        identity = self.repo.get_teacher_identity_by_email(email)
        if identity is None:
            logger.info("OTP requested for unknown email (no-op, not revealed to caller)")
            return

        recent_count = self.repo.count_recent_otp_requests(identity.id, since=now_utc() - timedelta(hours=1))
        if recent_count >= 5:  # OPEN_DECISIONS.md default: 5 requests/hour
            raise RateLimitedError("Too many OTP requests. Try again later.")

        code = generate_otp_code()
        self.repo.create_otp_code(
            teacher_identity_id=identity.id,
            code_hash=hash_secret(code),
            expires_at=now_utc() + timedelta(seconds=OTP_TTL_SECONDS),
        )
        self.db.commit()

        # Async send — Celery task per 04_BACKEND_GUIDE.md / Deployment Guide.
        from app.tasks.email_tasks import send_otp_email  # local import avoids circular import at module load
        send_otp_email.delay(email, code)

    def verify_teacher_otp(self, email: str, code: str, device_info: str | None = None) -> dict:
        identity = self.repo.get_teacher_identity_by_email(email)
        if identity is None:
            raise UnauthorizedError("Invalid or expired code.", code="INVALID_OR_EXPIRED_CODE")

        otp = self.repo.get_latest_active_otp(identity.id)
        if otp is None:
            raise UnauthorizedError("Invalid or expired code.", code="INVALID_OR_EXPIRED_CODE")

        if otp.attempts >= OTP_MAX_ATTEMPTS:
            raise RateLimitedError("Too many attempts on this code.", code="TOO_MANY_ATTEMPTS")

        if not constant_time_compare(hash_secret(code), otp.code_hash):
            otp.attempts += 1
            self.db.commit()
            raise UnauthorizedError("Invalid or expired code.", code="INVALID_OR_EXPIRED_CODE")

        otp.consumed_at = now_utc()
        self.repo.mark_teacher_verified(identity)

        user = self.repo.get_user_by_id(identity.user_id)
        if user is None or not user.is_active:
            raise ForbiddenError("Account is deactivated.", code="ACCOUNT_DEACTIVATED")

        self.db.commit()
        return self._issue_tokens(user, device_info)

    # ---------- Token lifecycle ----------

    def refresh(self, raw_refresh_token: str, device_info: str | None = None) -> dict:
        token_hash = hash_secret(raw_refresh_token)
        token = self.repo.get_refresh_token_by_hash(token_hash)

        if token is None:
            raise UnauthorizedError("Invalid refresh token.", code="INVALID_REFRESH_TOKEN")

        if token.revoked_at is not None:
            # Reuse of a revoked token — treat as possible theft (Security Guide reuse detection).
            self.repo.revoke_all_refresh_tokens_for_user(token.user_id)
            self.db.commit()
            raise UnauthorizedError("Token reuse detected. All sessions revoked.", code="TOKEN_REUSE_DETECTED")

        if token.expires_at < now_utc():
            raise UnauthorizedError("Refresh token expired.", code="INVALID_REFRESH_TOKEN")

        self.repo.revoke_refresh_token(token)
        user = self.repo.get_user_by_id(token.user_id)
        if user is None or not user.is_active:
            raise ForbiddenError("Account is deactivated.", code="ACCOUNT_DEACTIVATED")

        self.db.commit()
        return self._issue_tokens(user, device_info)

    def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_secret(raw_refresh_token)
        token = self.repo.get_refresh_token_by_hash(token_hash)
        if token is not None and token.revoked_at is None:
            self.repo.revoke_refresh_token(token)
            self.db.commit()

    def get_current_user_profile(self, user_id: uuid.UUID) -> dict:
        user = self.repo.get_user_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found.")
        roles = self.rbac_repo.get_role_names_for_user(user.id)
        return {"user": user, "roles": roles}
