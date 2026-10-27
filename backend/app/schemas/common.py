"""Schemas shared across every list endpoint."""

from __future__ import annotations

from marshmallow import Schema, fields, validate

from app.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class PaginationQuerySchema(Schema):
    """Standard page/page_size query parameters."""

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Int(
        load_default=DEFAULT_PAGE_SIZE,
        validate=validate.Range(min=1, max=MAX_PAGE_SIZE),
    )


class SearchSortQuerySchema(PaginationQuerySchema):
    """Pagination + search + sort contract used by collection endpoints."""

    q = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=128))
    sort = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=64))
    order = fields.Str(
        load_default="desc",
        validate=validate.OneOf(["asc", "desc"]),
    )
