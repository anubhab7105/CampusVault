"""
Library domain repository. Per 04_BACKEND_GUIDE.md: "Database access goes
through repositories." Covers files and resources per API_SPEC_LIBRARY.md.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.library import File, Resource, ScanStatus


class LibraryRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Files ----------

    def create_file(
        self, uploader_id: uuid.UUID, original_filename: str, stored_filename: str,
        mime_type: str, size_bytes: int, storage_path: str,
    ) -> File:
        file = File(
            uploader_id=uploader_id, original_filename=original_filename, stored_filename=stored_filename,
            mime_type=mime_type, size_bytes=size_bytes, storage_path=storage_path,
            scan_status=ScanStatus.PENDING,
        )
        self.db.add(file)
        self.db.flush()
        return file

    def get_file_by_id(self, file_id: uuid.UUID) -> File | None:
        return self.db.scalar(select(File).where(File.id == file_id, File.deleted_at.is_(None)))

    def update_scan_status(self, file: File, status: ScanStatus) -> File:
        file.scan_status = status
        file.scanned_at = datetime.now(timezone.utc)
        self.db.flush()
        return file

    # ---------- Resources ----------

    def create_resource(
        self, file_id: uuid.UUID, title: str, description: str | None, uploaded_by: uuid.UUID,
        department_id: uuid.UUID | None, program_id: uuid.UUID | None, subject_id: uuid.UUID | None,
    ) -> Resource:
        resource = Resource(
            file_id=file_id, title=title, description=description, uploaded_by=uploaded_by,
            department_id=department_id, program_id=program_id, subject_id=subject_id,
        )
        self.db.add(resource)
        self.db.flush()
        return resource

    def get_resource_by_id(self, resource_id: uuid.UUID) -> Resource | None:
        return self.db.scalar(select(Resource).where(Resource.id == resource_id, Resource.deleted_at.is_(None)))

    def update_resource(
        self, resource: Resource, title: str | None, description: str | None,
        department_id: uuid.UUID | None, program_id: uuid.UUID | None, subject_id: uuid.UUID | None,
    ) -> Resource:
        if title is not None:
            resource.title = title
        if description is not None:
            resource.description = description
        if department_id is not None:
            resource.department_id = department_id
        if program_id is not None:
            resource.program_id = program_id
        if subject_id is not None:
            resource.subject_id = subject_id
        self.db.flush()
        return resource

    def soft_delete_resource(self, resource: Resource) -> None:
        resource.deleted_at = datetime.now(timezone.utc)
        self.db.flush()

    def list_resources(
        self, department_id: uuid.UUID | None, program_id: uuid.UUID | None, subject_id: uuid.UUID | None,
        query: str | None, only_clean: bool, uploader_id: uuid.UUID | None,
    ) -> list[Resource]:
        stmt = select(Resource).join(File, File.id == Resource.file_id).where(Resource.deleted_at.is_(None))
        if only_clean:
            stmt = stmt.where(File.scan_status == ScanStatus.CLEAN)
        if department_id is not None:
            stmt = stmt.where(Resource.department_id == department_id)
        if program_id is not None:
            stmt = stmt.where(Resource.program_id == program_id)
        if subject_id is not None:
            stmt = stmt.where(Resource.subject_id == subject_id)
        if uploader_id is not None:
            stmt = stmt.where(Resource.uploaded_by == uploader_id)
        if query:
            like = f"%{query}%"
            from sqlalchemy import or_
            stmt = stmt.where(or_(Resource.title.ilike(like), Resource.description.ilike(like)))
        return list(self.db.scalars(stmt.order_by(Resource.title)))
