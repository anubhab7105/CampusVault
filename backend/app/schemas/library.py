"""Library domain request/response schemas (Pydantic v2)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.library import ScanStatus


# ---------- Files ----------

class FileOut(BaseModel):
    id: uuid.UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    scan_status: ScanStatus

    model_config = {"from_attributes": True}


class FileDownloadOut(BaseModel):
    download_url: str
    expires_in: int


# ---------- Resources ----------

class ResourceCreateRequest(BaseModel):
    file_id: uuid.UUID
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    department_id: uuid.UUID | None = None
    program_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None


class ResourceUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    department_id: uuid.UUID | None = None
    program_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None


class SubjectRef(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    model_config = {"from_attributes": True}


class UploaderRef(BaseModel):
    id: uuid.UUID
    full_name: str

    model_config = {"from_attributes": True}


class ResourceOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    file: FileOut
    subject: SubjectRef | None = None
    uploaded_by: UploaderRef
    created_at: datetime

    model_config = {"from_attributes": True}
