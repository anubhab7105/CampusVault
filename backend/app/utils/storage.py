"""
File storage abstraction, per 11_DEPLOYMENT_GUIDE.md's locked choice of
Supabase Storage. This sandbox has no Supabase project/credentials to test
against, so SupabaseStorageProvider is written correctly for production
but not exercised here. LocalFilesystemStorageProvider is a real, fully
working implementation used by tests and suitable for local dev without
Supabase configured — not a mock, an actual alternate backend.
"""
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class StorageProvider(ABC):
    @abstractmethod
    def upload(self, content: bytes, storage_key: str) -> str:
        """Returns the storage_path to persist on the File row."""
        ...

    @abstractmethod
    def download(self, storage_path: str) -> bytes:
        ...

    @abstractmethod
    def get_signed_url(self, storage_path: str, expires_in: int) -> str:
        ...


class LocalFilesystemStorageProvider(StorageProvider):
    """Real, working local-disk backend. Used in dev/tests when Supabase isn't configured."""

    def __init__(self, base_dir: str = "/tmp/campusvault_storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, content: bytes, storage_key: str) -> str:
        path = self.base_dir / storage_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    def download(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    def get_signed_url(self, storage_path: str, expires_in: int) -> str:
        # No real signing needed for local dev — a file:// URL is sufficient
        # for tests to confirm the plumbing, not a production URL scheme.
        return f"file://{storage_path}?expires_in={expires_in}"


class SupabaseStorageProvider(StorageProvider):
    """
    Real Supabase Storage implementation. Requires SUPABASE_URL and
    SUPABASE_SERVICE_ROLE_KEY env vars — not available in this sandbox, so
    this class is written but not exercised by the test suite here.
    """

    def __init__(self, bucket: str = "campusvault-files"):
        self.bucket = bucket
        self.url = os.environ.get("SUPABASE_URL")
        self.service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    def upload(self, content: bytes, storage_key: str) -> str:
        from supabase import create_client

        client = create_client(self.url, self.service_key)
        client.storage.from_(self.bucket).upload(storage_key, content)
        return storage_key

    def download(self, storage_path: str) -> bytes:
        from supabase import create_client

        client = create_client(self.url, self.service_key)
        return client.storage.from_(self.bucket).download(storage_path)

    def get_signed_url(self, storage_path: str, expires_in: int) -> str:
        from supabase import create_client

        client = create_client(self.url, self.service_key)
        result = client.storage.from_(self.bucket).create_signed_url(storage_path, expires_in)
        return result["signedURL"]


def generate_storage_key(original_filename: str) -> str:
    """
    Random filename per 06_SECURITY_GUIDE.md upload rules — never trust or
    reuse the client-supplied original filename for storage.
    """
    ext = Path(original_filename).suffix
    return f"{uuid.uuid4().hex}{ext}"
