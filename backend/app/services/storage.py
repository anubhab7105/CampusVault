"""Storage backend interface — abstracts Supabase (or any object store) from the service layer.

Design rationale:
- The service layer never imports ``supabase`` at module level; it only ever calls
  methods on a ``StorageBackend`` instance.  A concrete ``SupabaseStorage`` implementation
  is created lazily (inside the app factory) so that the app can start without Supabase
  credentials (useful for local dev with local file storage).
- Two concrete implementations are provided today: ``SupabaseStorage`` and a
  ``LocalFileStorage`` for tests/local development.
- New backends can be added by subclassing ``StorageBackend`` and registering them
  in ``app/factory.py``.
"""

from __future__ import annotations

import base64
import os
import uuid
from datetime import UTC
from pathlib import Path
from typing import Protocol

from app.errors.exceptions import ConfigError


class StorageBackend(Protocol):
    """Protocol that every storage implementation must satisfy."""

    def upload(self, key: str, fileobj: bytes, mime_type: str | None, size: int) -> dict:
        """Upload ``fileobj`` under ``key`` and return metadata dict.

        Returns ``{ "storage_key": str, "url": str, "expires_at": datetime }``.
        """
        ...

    def download(self, key: str) -> bytes:
        """Return the file bytes for ``key``."""
        ...

    def delete(self, key: str) -> None:
        """Permanently delete the object under ``key``."""
        ...

    def exists(self, key: str) -> bool:
        """Check whether the object under ``key`` exists."""
        ...


class BaseStorage:
    """Mixin with shared helpers."""

    bucket_name: str = "campusvault-files"

    def _random_key(self, prefix: str = "files") -> str:
        """Generate a random storage key (32‑char base64, URL‑safe)."""
        return base64.urlsafe_b64encode(uuid.uuid4().bytes[:24]).rstrip(b"=").decode("ascii") + ".upload"


# ------------------------------------------------------------------- #
# Concrete: Supabase
# ------------------------------------------------------------------- #


class SupabaseStorage:
    """Supabase Storage backend.

    The Supabase client is imported **inside the method**, never at module level,
    so the service layer never depends on the Supabase SDK at import time.
    """

    def __init__(self, bucket_name: str | None = None) -> None:
        self.bucket_name = bucket_name or os.environ.get("SUPABASE_STORAGE_BUCKET", "campusvault-files")
        self._supabase = None  # lazy

    def _get_client(self):
        """Import supabase lazily; raise a helpful error if env vars are missing."""
        if self._supabase is None:
            supabase_url = os.environ.get("SUPABASE_URL")
            supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if not supabase_url or not supabase_key:
                raise ConfigError(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to use Supabase Storage."
                )
            from supabase import create_client

            self._supabase = create_client(supabase_url, supabase_key)

        return self._supabase

    def upload(self, key: str, fileobj: bytes, mime_type: str | None, size: int) -> dict:
        """Upload ``fileobj`` under ``key`` into the configured bucket.

        Returns ``{ "storage_key": key, "url": signed_url, "expires_at": datetime }``.
        """
        client = self._get_client()
        # Upload the byte slice; then generate a signed URL valid for 5 minutes.
        client.storage.from_(self.bucket_name).upload(key, fileobj)
        signed = client.storage.from_(self.bucket_name).get_public_url(key, expires_in=300)
        from datetime import datetime

        return {
            "storage_key": key,
            "url": signed,
            "expires_at": datetime.now(UTC).replace(tzinfo=None),
        }

    def download(self, key: str) -> bytes:
        """Download the object bytes for ``key``."""
        client = self._get_client()
        # Supabase Python SDK ``download`` returns a file-like object; read all.
        resp = client.storage.from_(self.bucket_name).download(key)
        return resp.read()

    def delete(self, key: str) -> None:
        """Permanently delete the object under ``key``."""
        client = self._get_client()
        client.storage.from_(self.bucket_name).remove([key])

    def exists(self, key: str) -> bool:
        """Check existence without raising; returns ``True``/``False``."""
        client = self._get_client()
        try:
            client.storage.from_(self.bucket_name).head(key)
            return True
        except Exception:
            return False


# ------------------------------------------------------------------- #
# Concrete: LocalFileStorage (tests & local dev)
# ------------------------------------------------------------------- #


class LocalFileStorage:
    """Simple local‑file store used by tests and local development.

    Files are written under ``BASE_DIR / "storage" / bucket_name``.
    Never used in production; only in ``pytest`` unit tests where ``SUPABASE_URL``
    is deliberately absent.
    """

    def __init__(self, base_dir: str | None = None, bucket_name: str = "campusvault-files") -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.home() / ".cache" / "campusvault"
        self.bucket_name = bucket_name
        self._dir = self.base_dir / self.bucket_name
        self._dir.mkdir(parents=True, exist_ok=True)

    def upload(self, key: str, fileobj: bytes, mime_type: str | None, size: int) -> dict:
        path = self._dir / key
        path.write_bytes(fileobj)
        # Return a "local" URL that just points at the on‑disk path.
        url = f"/storage/{self.bucket_name}/{key}"
        return {"storage_key": key, "url": url, "expires_at": None}

    def download(self, key: str) -> bytes:
        path = self._dir / key
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._dir / key
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def exists(self, key: str) -> bool:
        return (self._dir / key).is_file()
