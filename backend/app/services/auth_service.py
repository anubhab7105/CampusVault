"""Authentication service.

Student: Google OAuth (userinfo + verified email required).
Teacher: email OTP (two-phase; delivery queued via Celery).

Both paths converge on ``_authorize_user`` which
- upserts the user row
- assigns the system role (Student/Teacher) when missing
- emits an audit event
- returns the JWT pair
"""

from __future__ import annotations

from urllib.parse import urlencode

from authlib.integrations.requests_client import OAuth2Session
from flask import current_app

from app.constants import (
    AUTH_PROVIDER_GOOGLE,
    AUTH_PROVIDER_OTP,
    ROLE_STUDENT,
)
from app.errors.exceptions import (
    ConflictError,
    ForbiddenError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.extensions import db
from app.models import TeacherAllowlist, User
from app.repositories import UserRepository
from app.services.otp_service import OTP_TTL_SECONDS, otp_service
from app.services.token_service import TokenService
from app.utils.datetime_utils import utcnow


class AuthService:
    def __init__(self) -> None:
        self.users = UserRepository()

    # --- Students: Google OAuth ---------------------------------------------- #

    def build_google_authorize_url(self, state: str) -> str:
        cfg = current_app.config
        params = urlencode(
            {
                "client_id": cfg["GOOGLE_CLIENT_ID"],
                "redirect_uri": cfg["GOOGLE_OAUTH_REDIRECT_URI"],
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
            }
        )
        return f"{cfg['GOOGLE_OAUTH_AUTHORIZATION_ENDPOINT']}?{params}"

    def _exchange_google_code(self, code: str) -> dict:
        cfg = current_app.config
        try:
            session = OAuth2Session(
                client_id=cfg["GOOGLE_CLIENT_ID"],
                client_secret=cfg["GOOGLE_CLIENT_SECRET"],
                redirect_uri=cfg["GOOGLE_OAUTH_REDIRECT_URI"],
            )
            session.fetch_token(
                cfg["GOOGLE_OAUTH_TOKEN_ENDPOINT"], code=code, grant_type="authorization_code"
            )
            response = session.get(cfg["GOOGLE_OAUTH_USERINFO_ENDPOINT"])
            response.raise_for_status()
            return response.json()
        except Exception as err:  # upstream OAuth errors are opaque to the client
            current_app.logger.warning("google_oauth_exchange_failed %s", type(err).__name__)
            raise ServiceUnavailableError("Could not verify Google sign-in.") from err

    def login_student_with_code(self, code: str) -> dict:
        info = self._exchange_google_code(code)
        email = info.get("email")
        google_sub = info.get("sub")
        if not email or not google_sub or not info.get("email_verified", False):
            raise UnauthorizedError("Google account is not eligible for CampusVault.")
        # Domain restriction — only allowed domains may sign in.
        allowed_domains = current_app.config.get("GOOGLE_ALLOWED_DOMAINS", "")
        if allowed_domains:
            domain = email.split("@")[-1]
            if domain not in [d.strip() for d in allowed_domains.split(",")]:
                raise UnauthorizedError("Google email domain is not authorised for CampusVault.")
        return self._authorize_user(
            email=email,
            full_name=info.get("name") or email.split("@")[0],
            avatar_url=info.get("picture"),
            provider=AUTH_PROVIDER_GOOGLE,
            google_sub=google_sub,
            role_name=ROLE_STUDENT,
        )

    # --- Teachers: email OTP --------------------------------------------------- #

    def request_teacher_otp(self, email: str) -> str:
        """Issue an OTP for an existing teacher account; delivery is async.

        Unknown emails return the same shape (anti-enumeration) but nothing
        is issued.  Only pre-approved teacher emails (teacher allowlist) may
        complete the OTP flow.  Rate limits are enforced per-email in Redis.
        """
        # Check allowlist — same shape response whether approved or not.
        allowlisted = self.is_teacher_allowlisted(email)

        # Rate limit per email: 3 attempts per 5 minutes stored in Redis.
        attempt_key = f"otp_attempts:{email.strip().lower()}"
        current_attempts = get_redis().get(attempt_key)
        if current_attempts is not None and int(current_attempts) >= 3:
            lockout_until = int(get_redis().get(f"otp_lockout_until:{email.strip().lower()}") or "0")
            now = int(utcnow().timestamp())
            if now < lockout_until:
                raise UnauthorizedError("Too many OTP attempts. Try again later.")
            # Reset after lockout window.
            get_redis().delete(attempt_key, f"otp_lockout_until:{email.strip().lower()}")

        user = self.users.get_by_email(email)
        if user is None:
            # Anti-enumeration: always return the TTL, never confirm existence.
            return OTP_TTL_SECONDS
        if user.auth_provider != AUTH_PROVIDER_OTP:
            raise ConflictError("This account signs in with a different method.")

        # If the account exists but is not allowlisted, still issue OTP but
        # the verification step will reject it.  This preserves the anti-enumeration
        # contract while still allowing admins to manage the allowlist.
        code = otp_service.issue(email)
        from app.tasks.emails import send_otp_email

        send_otp_email.delay(to=email, code=code, ttl_minutes=10)
        return OTP_TTL_SECONDS

    def is_teacher_allowlisted(self, email: str) -> bool:
        """Check whether ``email`` is on the teacher allowlist."""
        stmt = (
            db.select(TeacherAllowlist)
            .where(TeacherAllowlist.email == email.strip().lower())
            .where(TeacherAllowlist.is_approved == True)
        )
        allowlist_entry = db.session.scalar(stmt)
        return allowlist_entry is not None

    # --- shared ----------------------------------------------------------------- #

    def _authorize_user(
        self,
        *,
        email: str,
        full_name: str,
        avatar_url: str | None,
        provider: str,
        google_sub: str | None,
        role_name: str,
    ) -> dict:
        user = self.users.get_by_google_sub(google_sub) if google_sub else None
        if user is None:
            user = self.users.get_by_email(email)
        if user is None:
            user = self._provision_new_user(
                email=email,
                full_name=full_name,
                avatar_url=avatar_url,
                provider=provider,
                google_sub=google_sub,
                role_name=role_name,
            )
        elif not user.is_active:
            raise ForbiddenError("This account has been deactivated.")

        user.last_login_at = utcnow()
        self._audit_login(user, role_name)

        from app.services.role_service import role_service

        role, permissions = role_service.load_user_role_bundle(user.id)
        tokens = TokenService.issue_for_user(user.id, role, permissions)
        db.session.commit()
        return {"user": self.serialize_user(user, role), "tokens": tokens}

    def _provision_new_user(
        self,
        *,
        email: str,
        full_name: str,
        avatar_url: str | None,
        provider: str,
        google_sub: str | None,
        role_name: str,
    ) -> User:
        from app.services.role_service import role_service

        system_role = role_service.roles.get_system_role_by_name(role_name)
        if system_role is None:
            raise ServiceUnavailableError("Role provisioning pending. Try again soon.")

        user = self.users.create(
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            auth_provider=provider,
            google_sub=google_sub,
            email_verified_at=utcnow(),
        )
        db.session.add(UserRole(user_id=user.id, role_id=system_role.id))
        return user

    def _audit_login(self, user: User, role_name: str) -> None:
        from app.services.audit_service import audit_service

        audit_service.record(
            action=f"auth.login.{role_name.lower()}",
            entity_type="user",
            entity_id=user.id,
        )

    @staticmethod
    def serialize_user(user: User, role: str | None = None) -> dict:
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "auth_provider": user.auth_provider,
            "department_id": str(user.department_id) if user.department_id else None,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "role": role,
        }


auth_service = AuthService()
