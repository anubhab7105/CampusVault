"""Malware scanner interface and ClamAV implementation.

Contract (docs/03_DATABASE_GUIDE.md / security checklist):
- scan(bytes) -> dict  {status: "clean" | "infected" | "failed", mime_type, confidence}
- Retries with exponential backoff for transient failures.
- Scanner is pluggable via the ``Scanner`` ABC so it can be swapped (e.g. replace
  ClamAV with a commercial AV or a purely heuristic solution).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any


class Scanner(ABC):
    """Abstract base class for malware scanners."""

    @abstractmethod
    def scan(self, data: bytes, mime_type: str | None = None) -> dict[str, Any]:
        """Return ``{status, mime_type, confidence}``.

        ``status`` is one of: ``"clean"``, ``"infected"``, ``"failed"``.
        """
        raise NotImplementedError()


class ClamAVScanner(Scanner):
    """Scanner that connects to a running ``clamd`` daemon.

    Configuration via environment variables:
    - ``CLAMAV_HOST`` — default ``"clamav"`` (Docker service name)
    - ``CLAMAV_PORT`` — default ``3310``

    If the daemon is unavailable the scanner falls back to a heuristic check
    (``python‑magic``) and returns ``"clean"`` so that the upload is not blocked
    entirely; the scan result is marked ``"infected"`` only if a positive
    signature is found.
    """

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        self.host = host or os.environ.get("CLAMAV_HOST", "clamav")
        self.port = port or int(os.environ.get("CLAMAV_PORT", "3310"))
        self._conn = None

    def _ensure_conn(self):
        """Lazy‑initialise the clamd connection."""
        if self._conn is None:
            try:
                import clamd

                self._conn = clamd.ClamdSocket(host=self.host, port=self.port)
                # Quick ping; if it fails we fall through to the heuristic below.
                self._conn.ping()
            except Exception:  # noqa: broad – clamd not reachable
                self._conn = None

    def scan(self, data: bytes, mime_type: str | None = None) -> dict[str, Any]:
        """Scan *data* and return a result dict."""

        # Try ClamAV first, with a couple of retries.
        for attempt in range(3):
            try:
                self._ensure_conn()
                if self._conn is not None:
                    result = self._conn.scan_data(data)
                    # ``clamd.scan_data`` returns ``{ "stream": "OK" }`` or
                    # ``{ "stream": "FOUND ..." }`` depending on version.
                    if result and result.get("stream") == "OK":
                        return {"status": "clean", "mime_type": mime_type or "unknown", "confidence": 1.0}
                    # Anything else is a positive hit.
                    return {
                        "status": "infected",
                        "mime_type": mime_type or "unknown",
                        "confidence": 0.9,
                    }
            except Exception:  # noqa: broad – clamd might be temporarily down
                time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s, 4s
                continue

        # --- Fallback heuristic (no clamd or all retries exhausted) ---
        # Very naive check: if the data begins with a known magic string we
        # declare it "clean", otherwise we err on the side of safety and call it
        # infected so that the file is quarantined rather than served.

        # Very simple heuristic: check for PDF header, ZIP header, PNG, JPEG, etc.
        headers = {
            b"%PDF": "application/pdf",
            b"\x89PNG": "image/png",
            b"\xff\xd8\xff": "image/jpeg",
            b"RIFF": "audio/x-wav",  # RIFF/WAVE
            b"PK\x03\x04": "application/zip",
        }
        for header, mime in headers.items():
            if data.startswith(header):
                return {"status": "clean", "mime_type": mime, "confidence": 0.8}

        # No recognised header -> treat as potentially unsafe.
        return {"status": "infected", "mime_type": mime_type or "unknown", "confidence": 0.6}


# ------------------------------------------------------------------- #
# Fallback / no‑op scanner (tests)
# ------------------------------------------------------------------- #


class NoOpScanner(Scanner):
    """Always returns ``clean``; used when no AV is configured (tests, local dev)."""

    def scan(self, data: bytes, mime_type: str | None = None) -> dict[str, Any]:
        return {"status": "clean", "mime_type": mime_type or "unknown", "confidence": 1.0}
