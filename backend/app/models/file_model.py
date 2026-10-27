"""files — Supabase Storage object metadata.

Files are stored in Supabase Storage; rows here are the metadata + scan
pipeline state. Soft delete: yes, so shared links 404 cleanly (services must
check ``is_active_status``) while admin/audit keep history.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.constants import SCAN_STATUS_PENDING
from app.models.base import BaseModel, SoftDeleteMixin, UUIDType


class FileRecord(BaseModel, SoftDeleteMixin):
    __tablename__ = "files"

    uploader_id = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Hierarchy placement (nullable: not every file is subject-bound).
    subject_id = sa.Column(
        UUIDType,
        sa.ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    original_filename = sa.Column(sa.String(255), nullable=False)
    # Random-generated storage name inside the bucket; never the user's name.
    storage_key = sa.Column(sa.String(512), nullable=False, unique=True)
    bucket = sa.Column(sa.String(120), nullable=False)
    mime_type = sa.Column(sa.String(127), nullable=False)
    file_size = sa.Column(sa.BigInteger, nullable=False)
    sha256_checksum = sa.Column(sa.String(64), nullable=True, index=True)

    scan_status = sa.Column(
        sa.String(16),
        nullable=False,
        default=SCAN_STATUS_PENDING,
        server_default=sa.text("'pending'"),
        index=True,
    )
    scanned_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    scan_pipeline_version = sa.Column(sa.String(32), nullable=True)

    __table_args__ = (
        sa.Index("ix_files_uploader_created", "uploader_id", "created_at"),
        sa.Index("ix_files_subject_created", "subject_id", "created_at"),
    )

    def to_dict(self) -> dict:
        data = super().to_dict()
        # Hide storage internals from public serialization.
        data.pop("storage_key", None)
        data.pop("bucket", None)
        return data
