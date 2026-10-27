"""Files blueprint — upload metadata + status polling."""

from __future__ import annotations

import hashlib
import uuid

from flask import Blueprint, request

from app.middleware.auth import ensure_authenticated
from app.services.file_service import file_service
from app.utils.responses import success_response
from app.utils.validation import ValidationError

bp = Blueprint("files", __name__, url_prefix="/api/v1/files")


@bp.post("")
def register_upload():
    """Register file metadata; the bytes go to Supabase Storage with the
    returned storage_key. The malware pipeline then flips scan_status."""
    user_id = uuid.UUID(ensure_authenticated())
    upload = request.files.get("file")
    if upload is None:
        raise ValidationError("A multipart 'file' part is required.")

    filename = upload.filename or ""
    content_type = upload.mimetype or ""
    upload.stream.seek(0, 2)
    size_bytes = upload.stream.tell()
    upload.stream.seek(0)

    file_service.validate_upload(filename, content_type, size_bytes)
    checksum = hashlib.sha256()
    for chunk in upload.stream:
        checksum.update(chunk)
    upload.stream.seek(0)

    subject_raw = request.form.get("subject_id")
    subject_id = uuid.UUID(subject_raw) if subject_raw else None
    row = file_service.create(
        uploader_id=user_id,
        original_filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        subject_id=subject_id,
        checksum_hex=checksum.hexdigest(),
    )
    return success_response(
        data={**row.to_dict(), "id": str(row.id)},
        status_code=201,
        message="File registered; scan queued.",
    )


@bp.get("/<uuid:file_id>")
def get_file(file_id: uuid.UUID):
    ensure_authenticated()
    row = file_service.files.get_active_by_id(file_id)
    if row is None:
        from app.errors.exceptions import NotFoundError

        raise NotFoundError("File not found.")
    data = row.to_dict()
    data["id"] = str(row.id)
    data["scan_status"] = row.scan_status
    return success_response(data=data, message="File loaded.")
