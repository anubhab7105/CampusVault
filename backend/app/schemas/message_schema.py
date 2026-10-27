"""Chat message request schemas."""

from __future__ import annotations

from marshmallow import Schema, fields, validate


class SendGroupMessageSchema(Schema):
    conversation_id = fields.UUID(required=True)
    content = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=4000),
        ],
    )
    reply_to_id = fields.UUID(load_default=None, allow_none=True)


class EditGroupMessageSchema(Schema):
    content = fields.Str(required=True, validate=validate.Length(min=1, max=4000))


class MessageListQuerySchema(Schema):
    """Cursor pagination for chat history (newest first)."""

    before_id = fields.UUID(load_default=None, allow_none=True)
    limit = fields.Int(load_default=50, validate=validate.Range(min=1, max=100))
