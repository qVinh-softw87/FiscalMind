from __future__ import annotations

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """
    Abstract storage interface — Adapter Pattern.

    Why Abstract Base Class?
    - Defines the CONTRACT that all storage backends must fulfill
    - Business logic only depends on this interface, not concrete implementations
    - Swapping LocalStorage → S3Storage requires zero changes to DocumentService

    Implementations:
    - LocalStorage: saves to local filesystem (development + single-server)
    - S3Storage: saves to AWS S3 (production, Phase 12)
    """

    @abstractmethod
    async def save(self, file_path: str, content: bytes) -> str:
        """
        Persists file content to storage.

        Args:
            file_path: relative path within storage (e.g. "uploads/user-id/file.pdf")
            content: raw file bytes

        Returns:
            Absolute or URL path to the stored file
        """
        ...

    @abstractmethod
    async def delete(self, file_path: str) -> None:
        """Removes a file from storage. Silently ignores if not found."""
        ...

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Returns True if the file exists in storage."""
        ...

    @abstractmethod
    async def read(self, file_path: str) -> bytes:
        """Reads and returns full file content."""
        ...

    @abstractmethod
    async def get_url(self, file_path: str) -> str:
        """Returns a URL or accessible path to the file."""
        ...
