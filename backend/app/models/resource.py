"""resources — library catalog entries.

A resource is the library-facing entity (a note, past paper, slide, …). It
references at most one file row *or* an external URL. Soft delete: yes.
Usage counters (download_count/view_count) are updated atomically in the
repository, not via naive read-modify-write.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models.base import BaseModel, SoftDeleteMixin, UUIDType


class Resource(BaseModel, SoftDeleteMixin):
    __tablename__ = "resources"

    subject_id = sa.Column(
        UUIDType,
        sa.ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Academic hierarchy denormalization.
    # department_id / program_id / semester_id are derived from subject_id on
    # write (subject -> semester -> program -> department). section_id is stored
    # independently (not derivable from subject). All nullable to keep existing
    # resources valid and to allow college-wide scoping.
    department_id = sa.Column(
        UUIDType,
        sa.ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    program_id = sa.Column(
        UUIDType,
        sa.ForeignKey("programs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    semester_id = sa.Column(
        UUIDType,
        sa.ForeignKey("semesters.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    section_id = sa.Column(
        UUIDType,
        sa.ForeignKey("sections.id", ondelete="RESTRICT"),
        nullable=True,
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

    # --- ORM relationships (academic hierarchy) --------------------------- #

    department = db.relationship(
        "Department", foreign_keys=[department_id], lazy="select"
    )
    program = db.relationship(
        "Program", foreign_keys=[program_id], lazy="select"
    )
    semester = db.relationship(
        "Semester", foreign_keys=[semester_id], lazy="select"
    )
    section = db.relationship(
        "Section", foreign_keys=[section_id], lazy="select"
    )
    subject = db.relationship(
        "Subject", foreign_keys=[subject_id], lazy="select"
    )

    __table_args__ = (
        # Primary browse path: filter by subject, order by recency.
        sa.Index("ix_resources_subject_created", "subject_id", "created_at"),
        sa.Index("ix_resources_type_published", "resource_type", "is_published"),
        sa.CheckConstraint("length(title) >= 3", name="ck_resources_title_min_length"),
    )
