"""Unit tests for app.utils.security — no DB required."""
import time
import uuid

import jwt as pyjwt
import pytest

from app.utils import security


class TestAccessToken:
    def test_create_and_decode_round_trip(self):
        user_id = uuid.uuid4()
        token, expires_in = security.create_access_token(user_id, "student", ["student"])

        payload = security.decode_access_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["user_type"] == "student"
        assert payload["roles"] == ["student"]
        assert expires_in == security.ACCESS_TOKEN_TTL_SECONDS

    def test_expired_token_raises(self):
        user_id = uuid.uuid4()
        expired = pyjwt.encode(
            {"sub": str(user_id), "exp": int(time.time()) - 5},
            security.JWT_SECRET,
            algorithm=security.JWT_ALGORITHM,
        )
        with pytest.raises(pyjwt.ExpiredSignatureError):
            security.decode_access_token(expired)

    def test_tampered_token_raises(self):
        user_id = uuid.uuid4()
        token, _ = security.create_access_token(user_id, "teacher", [])
        tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
        with pytest.raises(pyjwt.InvalidTokenError):
            security.decode_access_token(tampered)

    def test_wrong_secret_rejected(self):
        user_id = uuid.uuid4()
        token = pyjwt.encode(
            {"sub": str(user_id), "exp": int(time.time()) + 60},
            "a-different-secret",
            algorithm=security.JWT_ALGORITHM,
        )
        with pytest.raises(pyjwt.InvalidTokenError):
            security.decode_access_token(token)


class TestOTP:
    def test_generate_otp_code_default_length_and_digits(self):
        code = security.generate_otp_code()
        assert len(code) == security.OTP_LENGTH
        assert code.isdigit()

    def test_generate_otp_code_custom_length(self):
        code = security.generate_otp_code(length=4)
        assert len(code) == 4

    def test_codes_are_not_trivially_predictable(self):
        codes = {security.generate_otp_code() for _ in range(20)}
        # Not a strict randomness proof, but catches an obviously broken/static generator.
        assert len(codes) > 1


class TestHashing:
    def test_hash_is_deterministic(self):
        assert security.hash_secret("abc123") == security.hash_secret("abc123")

    def test_hash_differs_for_different_input(self):
        assert security.hash_secret("abc123") != security.hash_secret("abc124")

    def test_never_stores_plaintext_shape(self):
        # The hash should not simply echo the input back.
        value = "482913"
        assert security.hash_secret(value) != value
        assert len(security.hash_secret(value)) == 64  # sha256 hex digest length

    def test_constant_time_compare_matches(self):
        h = security.hash_secret("same-value")
        assert security.constant_time_compare(h, security.hash_secret("same-value"))

    def test_constant_time_compare_mismatches(self):
        assert not security.constant_time_compare(
            security.hash_secret("a"), security.hash_secret("b")
        )


class TestOpaqueToken:
    def test_generate_opaque_token_is_unique_and_reasonably_long(self):
        a = security.generate_opaque_token()
        b = security.generate_opaque_token()
        assert a != b
        assert len(a) > 32
