"""resources — library catalog entries.

A resource is the library-facing entity (a note, past paper, slide, …). It
references at most one file row *or* an external URL. Soft delete: yes.
Usage counters (download_count/view_count) are updated atomically in the
repository, not via naive read-modify-write.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.models.base import BaseModel, SoftDeleteMixin, UUIDType


class Resource(BaseModel, SoftDeleteMixin):
    __tablename__ = "resources"

    subject_id = sa.Column(
        UUIDType,
        sa.ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    file_id = sa.Column(
        UUIDType,
        sa.ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    uploaded_by = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title = sa.Column(sa.String(160), nullable=False)
    description = sa.Column(sa.String(2000), nullable=True)
    resource_type = sa.Column(sa.String(24), nullable=False, index=True)
    visibility = sa.Column(sa.String(16), nullable=False, default="college", index=True)
    external_url = sa.Column(sa.String(2048), nullable=True)

    share_token = sa.Column(sa.String(64), nullable=True, unique=True, index=True)
    is_published = sa.Column(sa.Boolean, nullable=False, default=True, server_default=sa.text("true"))
    download_count = sa.Column(sa.Integer, nullable=False, default=0, server_default=sa.text("0"))
    view_count = sa.Column(sa.Integer, nullable=False, default=0, server_default=sa.text("0"))

    __table_args__ = (
        # Primary browse path: filter by subject, order by recency.
        sa.Index("ix_resources_subject_created", "subject_id", "created_at"),
        sa.Index("ix_resources_type_published", "resource_type", "is_published"),
        sa.CheckConstraint("length(title) >= 3", name="ck_resources_title_min_length"),
    )
