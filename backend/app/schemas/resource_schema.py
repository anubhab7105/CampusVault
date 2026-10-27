"""Library resource/query schemas."""

from __future__ import annotations

from marshmallow import Schema, fields, validate

from app.constants import RESOURCE_TYPES, VISIBILITY_CHOICES


class ListResourcesQuerySchema(Schema):
    """Hierarchical browse + search + sort for the Library module."""

    department_id = fields.UUID(load_default=None, allow_none=True)
    program_id = fields.UUID(load_default=None, allow_none=True)
    semester_id = fields.UUID(load_default=None, allow_none=True)
    section_id = fields.UUID(load_default=None, allow_none=True)
    subject_id = fields.UUID(load_default=None, allow_none=True)

    resource_type = fields.Str(
        load_default=None, allow_none=True, validate=validate.OneOf(sorted(RESOURCE_TYPES))
    )
    visibility = fields.Str(
        load_default=None, allow_none=True, validate=validate.OneOf(sorted(VISIBILITY_CHOICES))
    )

    q = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=128))
    sort = fields.Str(
        load_default="created_at",
        validate=validate.OneOf(["created_at", "title", "download_count"]),
    )
    order = fields.Str(load_default="desc", validate=validate.OneOf(["asc", "desc"]))

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))


class CreateResourceSchema(Schema):
    subject_id = fields.UUID(required=True)
    file_id = fields.UUID(load_default=None, allow_none=True)
    external_url = fields.Url(load_default=None, allow_none=True, validate=validate.Length(max=2048))

    title = fields.Str(required=True, validate=validate.Length(min=3, max=160))
    description = fields.Str(load_default="", validate=validate.Length(max=2000))
    resource_type = fields.Str(required=True, validate=validate.OneOf(sorted(RESOURCE_TYPES)))
    visibility = fields.Str(load_default="college", validate=validate.OneOf(sorted(VISIBILITY_CHOICES)))
