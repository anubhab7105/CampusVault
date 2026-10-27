"""Request-body validation helpers shared by every blueprint.

Rule: **never** read ``request.get_json`` without trying it, and **never** feed
API payloads into services without a marshmallow schema.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import request
from marshmallow import Schema
from marshmallow import ValidationError as MarshmallowValidationError

from app.errors.exceptions import ValidationError


class APIValidationError(ValidationError):
    """Domain-level, schema-shaped, HTTP-422-safe validation failure."""


def build_validation_error(errors: Mapping[str, Any]) -> ValidationError:
    """Convert marshmallow errors into a normalized ValidationError."""
    normalized = {"fields": errors} if errors else {"body": ["Invalid payload."]}
    return ValidationError(msg=normalized)


def load_schema(schema: Schema, data: Any) -> dict:
    """Validate a payload with a marshmallow schema; raise on failure."""
    try:
        result = schema.load(data if isinstance(data, dict) else {})
    except MarshmallowValidationError as exc:
        raise build_validation_error(exc.messages) from exc
    return result


def get_json_body(*, silent: bool = True) -> dict[str, Any]:
    """Read and return the JSON body, raising on malformed/missing payloads."""
    body = request.get_json(silent=silent, force=True)
    if body is None:
        raise ValidationError(msg={"body": ["A valid JSON request body is required."]})
    if not isinstance(body, dict):
        raise ValidationError(msg={"body": ["JSON body must be an object."]})
    return body
