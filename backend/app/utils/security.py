"""
Core security utilities shared across domains.

Config values here match the defaults locked in docs/OPEN_DECISIONS.md.
Change via environment variables (per Anubhab's .env-only preference where
possible) rather than editing these constants directly in most cases.
"""
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

# ---------- Config (env-overridable) ----------

JWT_SECRET = os.environ.get("JWT_SECRET", "CHANGE_ME_IN_ENV")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_SECONDS = int(os.environ.get("ACCESS_TOKEN_TTL_SECONDS", 15 * 60))       # 15 min
REFRESH_TOKEN_TTL_SECONDS = int(os.environ.get("REFRESH_TOKEN_TTL_SECONDS", 30 * 24 * 3600))  # 30 days

OTP_LENGTH = int(os.environ.get("OTP_LENGTH", 6))
OTP_TTL_SECONDS = int(os.environ.get("OTP_TTL_SECONDS", 10 * 60))  # 10 min
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", 5))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Hashing (OTP codes, refresh tokens — never store either as plaintext) ----------

def hash_secret(value: str) -> str:
    """SHA-256 hash for values we need to compare-but-never-reveal (OTP codes, refresh tokens).

    NOTE: this is deliberately not a slow password hash (bcrypt/argon2) because these are
    high-entropy random values (tokens) or short-lived rate-limited codes (OTP), not
    user-chosen passwords — SHA-256 is appropriate and fast enough for the token-lookup path.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def generate_otp_code(length: int = OTP_LENGTH) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def generate_opaque_token() -> str:
    """Used for refresh tokens — random, unguessable, stored only as a hash."""
    return secrets.token_urlsafe(48)


# ---------- JWT (access tokens) ----------

def create_access_token(user_id: uuid.UUID, user_type: str, roles: list[str]) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    now = now_utc()
    expires_at = now + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "user_type": user_type,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, ACCESS_TOKEN_TTL_SECONDS


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jwt.InvalidTokenError (or subclasses) on any failure — caller maps to 401."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
