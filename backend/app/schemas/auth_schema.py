"""Auth request schemas (students: Google OAuth; teachers: email OTP)."""

from __future__ import annotations

from marshmallow import Schema, fields, validate


class OAuthExchangeSchema(Schema):
    """Code handed back from the Google consent screen."""

    code = fields.Str(required=True, validate=validate.Length(min=8, max=512))


class TeacherRequestOtpSchema(Schema):
    """Phase 1 of teacher login: request a one-time passcode."""

    email = fields.Email(required=True, validate=validate.Length(max=255))


class TeacherVerifyOtpSchema(Schema):
    """Phase 2 of teacher login: exchange the OTP for tokens."""

    email = fields.Email(required=True, validate=validate.Length(max=255))
    code = fields.Str(required=True, validate=validate.Length(min=6, max=6))


class RefreshTokenSchema(Schema):
    """Refresh token comes as a body token or an httpOnly cookie."""

    refresh_token = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=2048))


class LogoutSchema(Schema):
    refresh_token = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=2048))