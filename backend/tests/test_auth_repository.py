"""Integration tests for AuthRepository — real Postgres, per Testing Guide."""
from datetime import datetime, timedelta, timezone

from app.models.auth import UserType
from app.repositories.auth_repository import AuthRepository


class TestUserRepository:
    def test_create_and_get_user_by_id(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("student1@college.edu", "Jane Doe", UserType.STUDENT)
        db.flush()

        fetched = repo.get_user_by_id(user.id)
        assert fetched is not None
        assert fetched.email == "student1@college.edu"
        assert fetched.user_type == UserType.STUDENT

    def test_get_user_by_email_case_insensitive(self, db):
        repo = AuthRepository(db)
        repo.create_user("Mixed.Case@college.edu", "Jane", UserType.STUDENT)
        db.flush()

        fetched = repo.get_user_by_email("mixed.case@college.edu")
        assert fetched is not None  # CITEXT column — case-insensitive by design

    def test_soft_deleted_user_not_returned(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("gone@college.edu", "Ghost", UserType.STUDENT)
        db.flush()
        user.deleted_at = datetime.now(timezone.utc)
        db.flush()

        assert repo.get_user_by_id(user.id) is None


class TestStudentIdentityRepository:
    def test_create_and_lookup_by_google_sub(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("student2@college.edu", "Jane", UserType.STUDENT)
        db.flush()
        repo.create_student_identity(user.id, "google-sub-123", "student2@college.edu")
        db.flush()

        found = repo.get_student_identity_by_google_sub("google-sub-123")
        assert found is not None
        assert found.user_id == user.id

    def test_unknown_google_sub_returns_none(self, db):
        repo = AuthRepository(db)
        assert repo.get_student_identity_by_google_sub("does-not-exist") is None


class TestTeacherIdentityAndOTP:
    def test_create_teacher_identity_and_lookup(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("teacher1@college.edu", "Mr. Smith", UserType.TEACHER)
        db.flush()
        repo.create_teacher_identity(user.id, "teacher1@college.edu")
        db.flush()

        found = repo.get_teacher_identity_by_email("teacher1@college.edu")
        assert found is not None
        assert found.user_id == user.id

    def test_latest_active_otp_excludes_expired_and_consumed(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("teacher2@college.edu", "Ms. Lee", UserType.TEACHER)
        db.flush()
        identity = repo.create_teacher_identity(user.id, "teacher2@college.edu")
        db.flush()

        # Expired code — should not be returned.
        repo.create_otp_code(identity.id, "hash-expired", datetime.now(timezone.utc) - timedelta(minutes=1))
        # Valid code — should be returned.
        active = repo.create_otp_code(identity.id, "hash-active", datetime.now(timezone.utc) + timedelta(minutes=10))
        db.flush()

        latest = repo.get_latest_active_otp(identity.id)
        assert latest is not None
        assert latest.id == active.id

    def test_consumed_otp_not_returned_as_active(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("teacher3@college.edu", "Mx. Rao", UserType.TEACHER)
        db.flush()
        identity = repo.create_teacher_identity(user.id, "teacher3@college.edu")
        db.flush()

        otp = repo.create_otp_code(identity.id, "hash", datetime.now(timezone.utc) + timedelta(minutes=10))
        db.flush()
        otp.consumed_at = datetime.now(timezone.utc)
        db.flush()

        assert repo.get_latest_active_otp(identity.id) is None

    def test_count_recent_otp_requests(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("teacher4@college.edu", "Dr. Nair", UserType.TEACHER)
        db.flush()
        identity = repo.create_teacher_identity(user.id, "teacher4@college.edu")
        db.flush()

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        assert repo.count_recent_otp_requests(identity.id, since) == 0

        repo.create_otp_code(identity.id, "h1", datetime.now(timezone.utc) + timedelta(minutes=10))
        repo.create_otp_code(identity.id, "h2", datetime.now(timezone.utc) + timedelta(minutes=10))
        db.flush()

        assert repo.count_recent_otp_requests(identity.id, since) == 2


class TestRefreshTokenRepository:
    def test_create_and_lookup_by_hash(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("student3@college.edu", "Jane", UserType.STUDENT)
        db.flush()

        now = datetime.now(timezone.utc)
        repo.create_refresh_token(user.id, "token-hash-abc", now, now + timedelta(days=30))
        db.flush()

        found = repo.get_refresh_token_by_hash("token-hash-abc")
        assert found is not None
        assert found.user_id == user.id
        assert found.revoked_at is None

    def test_revoke_all_refresh_tokens_for_user(self, db):
        repo = AuthRepository(db)
        user = repo.create_user("student4@college.edu", "Jane", UserType.STUDENT)
        db.flush()
        now = datetime.now(timezone.utc)
        t1 = repo.create_refresh_token(user.id, "hash-1", now, now + timedelta(days=30))
        t2 = repo.create_refresh_token(user.id, "hash-2", now, now + timedelta(days=30))
        db.flush()

        repo.revoke_all_refresh_tokens_for_user(user.id)
        db.flush()

        assert t1.revoked_at is not None
        assert t2.revoked_at is not None
