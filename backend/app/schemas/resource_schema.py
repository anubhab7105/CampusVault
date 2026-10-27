"""Resource request/response schemas."""

from __future__ import annotations

from marshmallow import Schema, fields, validate


class ResourceQuerySchema(Schema):
    """Query parameters for the library browse endpoint."""

    department_id = fields.UUID(allow_none=True)
    program_id = fields.UUID(allow_none=True)
    semester_id = fields.UUID(allow_none=True)
    section_id = fields.UUID(allow_none=True)
    subject_id = fields.UUID(allow_none=True)
    resource_type = fields.Str(allow_none=True)
    visibility = fields.Str(allow_none=True)
    q = fields.Str(allow_none=True, validate=validate.Length(max=255))
    sort = fields.Str(validate=validate.OneOf(["title", "download_count", "view_count", "created_at"]))
    order = fields.Str(validate=validate.OneOf(["asc", "desc"]))
    page = fields.Int(load_default=1, validate=lambda n: 0 < n <= 1000)
    page_size = fields.Int(load_default=20, validate=lambda n: 0 < n <= 100)


class ResourceUploadSchema(Schema):
    """Schema for the upload-request phase A payload."""

    extension = fields.Str(required=True, validate=validate.Length(max=10))
    mime_type = fields.Str(allow_none=True)
    size = fields.Int(allow_none=True)
    subject_id = fields.UUID(required=True)


class ResourceResponseSchema(Schema):
    """Schema for a resource in the browse/list response."""

    id = fields.UUID()
    title = fields.Str()
    description = fields.Str()
    resource_type = fields.Str()
    visibility = fields.Str()
    uploader_name = fields.Str()
    download_count = fields.Int()
    view_count = fields.Int()
    scan_status = fields.Str()
    created_at = fields.DateTime()
    is_published = fields.Bool()