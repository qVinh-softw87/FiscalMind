from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageBackend


@lru_cache
def get_storage() -> StorageBackend:
    """
    Storage factory — returns the configured backend as a singleton.

    Switching from local → S3:
    1. Set STORAGE_BACKEND=s3 in .env
    2. Fill AWS credentials
    3. Restart → S3Storage is injected everywhere automatically

    DocumentService never imports LocalStorage or S3Storage directly —
    it only depends on the StorageBackend interface. This is the
    Dependency Inversion Principle in action.
    """
    if settings.STORAGE_BACKEND == "s3":
        from app.storage.s3 import S3Storage  # type: ignore[import]
        return S3Storage()

    from app.storage.local import LocalStorage
    return LocalStorage()
