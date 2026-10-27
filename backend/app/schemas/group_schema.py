"""Group schemas (chat rooms tied into the academic hierarchy)."""

from __future__ import annotations

from marshmallow import Schema, fields, validate


class CreateGroupSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=3, max=120))
    description = fields.Str(load_default="", validate=validate.Length(max=1000))
    group_type = fields.Str(
        load_default="subject_group",
        validate=validate.OneOf(["subject_group", "section", "team", "club"]),
    )
    subject_id = fields.UUID(load_default=None, allow_none=True)
    section_id = fields.UUID(load_default=None, allow_none=True)


class JoinGroupSchema(Schema):
    invite_code = fields.Str(load_default=None, allow_none=True)


class AddMemberSchema(Schema):
    user_id = fields.UUID(required=True)
