"""Utility validators for upload and file type validation."""

from __future__ import annotations

import mimetypes
from urllib.parse import urlparse

from app.extensions import db
from app.models.file_model import FileRecord


ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "ppt",
    "pptx",
    "xls",
    "xlsx",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "txt",
    "csv",
    "md",
}


def allowed_extension(extension: str) -> bool:
    """Check if the file extension is in the allowed list."""
    return extension.lower() in ALLOWED_EXTENSIONS


def validate_mime_type(mime_type: str, extension: str) -> bool:
    """Validate that the MIME type matches the extension.

    Falls back to extension-based check; mimetypes as last resort.
    """
    if not mime_type:
        return True  # MIME optional; extension is required

    # Quick extension-based check first
    ext_to_mime = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "txt": "text/plain",
        "csv": "text/csv",
        "md": "text/markdown",
    }

    expected = ext_to_mime.get(extension.lower())
    if expected and mime_type != expected:
        return False

    # mimetypes fallback
    guessed = mimetypes.guess_type(f"file.{extension.lower()}")[0]
    return guessed == mime_type if guessed else True