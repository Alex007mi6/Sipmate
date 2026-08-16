"""Storage service protocol."""

from __future__ import annotations

from typing import BinaryIO, Protocol


class StorageService(Protocol):
    def save(
        self,
        *,
        file: BinaryIO,
        filename: str,
        content_type: str,
        prefix: str = "",
    ) -> tuple[str, str]:
        """Persist file; return (public_url, storage_key)."""
        ...

    def delete(self, key: str) -> None:
        """Best-effort delete of stored object."""
        ...
