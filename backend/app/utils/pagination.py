"""Pagination helpers shared by all list endpoints.

Inputs come in as ``page`` and ``page_size`` query parameters; outputs are a
normalized ``(page, page_size, offset)`` tuple plus a ``paging`` metadata
block that wraps the RFC-style links used by the frontend tables.
"""

from __future__ import annotations

from typing import Any

from marshmallow import ValidationError

from app.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class PagingMeta:
    """Computed metadata for a single paginated response."""

    __slots__ = ("page", "page_size", "total", "total_pages")

    def __init__(self, page: int, page_size: int, total: int) -> None:
        self.page = page
        self.page_size = page_size
        self.total = total
        self.total_pages = (total + page_size - 1) // page_size if page_size else 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total": self.total,
            "total_pages": self.total_pages,
            "has_next": self.page < self.total_pages,
            "has_prev": self.page > 1,
        }


def parse_pagination_args(
    page: Any,
    page_size: Any,
    *,
    default_size: int = DEFAULT_PAGE_SIZE,
    max_size: int = MAX_PAGE_SIZE,
) -> tuple[int, int, int]:
    """Normalize and bound-check pagination parameters.

    Raises:
        ValidationError: when values are not positive integers.
    """
    try:
        page_number = int(page) if page is not None else 1
        size = int(page_size) if page_size is not None else default_size
    except (TypeError, ValueError) as exc:
        raise ValidationError({"page": ["page and page_size must be integers."]}) from exc

    if page_number < 1:
        raise ValidationError({"page": ["page must be >= 1."]})
    size = min(max(size, 1), max_size)

    offset = (page_number - 1) * size
    return page_number, size, offset
