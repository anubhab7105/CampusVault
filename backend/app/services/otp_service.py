"""OTP issue/verify for teacher login.

Flow (docs/features/AUTH.md):
1. POST /auth/teachers/otp/request  → 6-digit code (hashed) into Redis,
   10-minute TTL, 3 attempt limit, 60s resend lock. Email queued via Celery.
2. POST /auth/teachers/otp/verify   → code exchange → tokens.

Codes never touch the database in plaintext.
"""

from __future__ import annotations

import secrets

from app.utils.redis_utils import get_redis

OTP_TTL_SECONDS = 600
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_LOCK_SECONDS = 60


class OTPService:
    prefix = "otp:"

    @staticmethod
    def generate_code(length: int = 6) -> str:
        return "".join(secrets.choice("1234567890") for _ in range(length))

    @classmethod
    def issue(cls, email: str) -> str:
        """Store a hashed code for ``email`` or raise when locked out."""
        redis = get_redis()
        email_key = f"{cls.prefix}{email}"
        if redis.ttl(f"{email_key}:resend") > 0:
            from app.errors.exceptions import RateLimitedError

            raise RateLimitedError("Please wait before requesting another code.")

        code = cls.generate_code()
        from passlib.hash import sha256_crypt  # one-way hash for codes at rest

        redis.hset(email_key, mapping={"hash": sha256_crypt.hash(code), "attempts": 0})
        redis.expire(email_key, OTP_TTL_SECONDS)
        redis.setex(f"{email_key}:resend", OTP_RESEND_LOCK_SECONDS, "1")
        return code

    @classmethod
    def verify(cls, email: str, code: str) -> bool:
        """One attempt decrements; exhausted attempts invalidate."""
        from passlib.hash import sha256_crypt

        redis = get_redis()
        email_key = f"{cls.prefix}{email}"
        record = redis.hgetall(email_key)
        if not record or "hash" not in record:
            return False

        attempts = int(record.get("attempts", "0"))
        if attempts >= OTP_MAX_ATTEMPTS:
            redis.delete(email_key)
            return False

        if not sha256_crypt.verify(code, record["hash"]):
            redis.hincrby(email_key, "attempts", 1)
            return False

        redis.delete(email_key)
        return True

    @classmethod
    def delete(cls, email: str) -> None:
        redis = get_redis()
        redis.delete(f"{cls.prefix}{email}", f"{cls.prefix}{email}:resend")


otp_service = OTPService()
