"""
Auth domain repository. Per 04_BACKEND_GUIDE.md: "Database access goes
through repositories" — services never issue raw queries themselves.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import OTPCode, RefreshToken, StudentIdentity, TeacherIdentity, User, UserType


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Users ----------

    def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )

    def create_user(self, email: str, full_name: str, user_type: UserType) -> User:
        user = User(email=email, full_name=full_name, user_type=user_type)
        self.db.add(user)
        self.db.flush()  # populate user.id without committing yet — caller controls the transaction
        return user

    # ---------- Student identity (Google OAuth) ----------

    def get_student_identity_by_google_sub(self, google_sub: str) -> StudentIdentity | None:
        return self.db.scalar(
            select(StudentIdentity).where(StudentIdentity.google_sub == google_sub)
        )

    def create_student_identity(self, user_id: uuid.UUID, google_sub: str, google_email: str) -> StudentIdentity:
        identity = StudentIdentity(
            user_id=user_id, google_sub=google_sub, google_email=google_email, created_at=datetime.now(timezone.utc)
        )
        self.db.add(identity)
        self.db.flush()
        return identity

    # ---------- Teacher identity (OTP) ----------

    def get_teacher_identity_by_email(self, otp_email: str) -> TeacherIdentity | None:
        return self.db.scalar(
            select(TeacherIdentity).where(TeacherIdentity.otp_email == otp_email)
        )

    def create_teacher_identity(self, user_id: uuid.UUID, otp_email: str) -> TeacherIdentity:
        identity = TeacherIdentity(user_id=user_id, otp_email=otp_email, created_at=datetime.now(timezone.utc))
        self.db.add(identity)
        self.db.flush()
        return identity

    def mark_teacher_verified(self, teacher_identity: TeacherIdentity) -> None:
        teacher_identity.last_verified_at = datetime.now(timezone.utc)

    # ---------- OTP codes ----------

    def create_otp_code(self, teacher_identity_id: uuid.UUID, code_hash: str, expires_at: datetime) -> OTPCode:
        otp = OTPCode(teacher_identity_id=teacher_identity_id, code_hash=code_hash, expires_at=expires_at)
        self.db.add(otp)
        self.db.flush()
        return otp

    def get_latest_active_otp(self, teacher_identity_id: uuid.UUID) -> OTPCode | None:
        """Latest unconsumed, unexpired code for this teacher identity."""
        return self.db.scalar(
            select(OTPCode)
            .where(
                OTPCode.teacher_identity_id == teacher_identity_id,
                OTPCode.consumed_at.is_(None),
                OTPCode.expires_at > datetime.now(timezone.utc),
            )
            .order_by(OTPCode.created_at.desc())
            .limit(1)
        )

    def count_recent_otp_requests(self, teacher_identity_id: uuid.UUID, since: datetime) -> int:
        """Used for rate limiting (max N OTP requests per hour per OPEN_DECISIONS.md)."""
        from sqlalchemy import func

        return self.db.scalar(
            select(func.count(OTPCode.id)).where(
                OTPCode.teacher_identity_id == teacher_identity_id,
                OTPCode.created_at >= since,
            )
        ) or 0

    # ---------- Refresh tokens ----------

    def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def create_refresh_token(
        self, user_id: uuid.UUID, token_hash: str, issued_at: datetime, expires_at: datetime,
        device_info: str | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id, token_hash=token_hash, issued_at=issued_at,
            expires_at=expires_at, device_info=device_info,
        )
        self.db.add(token)
        self.db.flush()
        return token

    def revoke_refresh_token(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(timezone.utc)

    def revoke_all_refresh_tokens_for_user(self, user_id: uuid.UUID) -> None:
        """Used for reuse-detection response — revoke every active session."""
        tokens = self.db.scalars(
            select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        )
        for t in tokens:
            t.revoked_at = datetime.now(timezone.utc)
