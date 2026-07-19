from __future__ import annotations

import os
from pathlib import Path

import aiofiles

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.base import StorageBackend

logger = get_logger(__name__)


class LocalStorage(StorageBackend):
    """
    Local filesystem storage implementation.

    Stores files under UPLOAD_DIR (default: /app/uploads).
    Suitable for:
    - Development
    - Single-server deployments
    - When S3 is not configured

    File organization:
    /app/uploads/
    └── {user_id}/
        └── {stored_filename}    ← UUID-based, prevents path traversal

    Security:
    - File paths are UUID-based (never use original filename as path)
    - Upload directory is outside web root (not directly served by web server)
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, file_path: str) -> Path:
        """
        Resolves relative path to absolute path within the upload directory.
        Validates the resolved path stays within base_dir (path traversal guard).
        """
        resolved = (self._base_dir / file_path).resolve()
        if not str(resolved).startswith(str(self._base_dir.resolve())):
            raise ValueError(f"Path traversal detected: {file_path}")
        return resolved

    async def save(self, file_path: str, content: bytes) -> str:
        """
        Writes file bytes to disk using async I/O (aiofiles).

        Why aiofiles?
        - Regular file I/O blocks the event loop
        - aiofiles runs I/O in a thread pool → keeps FastAPI non-blocking
        """
        full_path = self._resolve(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)

        logger.debug("file_saved", path=str(full_path), size=len(content))
        return str(full_path)

    async def delete(self, file_path: str) -> None:
        """Removes file from disk. No error if already gone."""
        full_path = self._resolve(file_path)
        if full_path.exists():
            full_path.unlink()
            logger.debug("file_deleted", path=str(full_path))

    async def exists(self, file_path: str) -> bool:
        full_path = self._resolve(file_path)
        return full_path.exists()

    async def read(self, file_path: str) -> bytes:
        """Reads file content asynchronously."""
        full_path = self._resolve(file_path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def get_url(self, file_path: str) -> str:
        """
        Returns accessible path for local storage.
        In production this would be behind an authenticated download endpoint.
        """
        return f"/api/v1/documents/download/{Path(file_path).name}"
