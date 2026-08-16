"""Local filesystem storage for uploads."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.core.errors import raise_error

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


def _detect_image(data: bytes, content_type: str) -> str:
    if content_type not in ALLOWED_MIME:
        raise_error(
            400,
            "INVALID_MIME",
            "Only JPEG, PNG, and WebP images are allowed.",
        )
    if content_type == "image/jpeg" and data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content_type == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content_type == "image/webp" and data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
        return ".webp"
    raise_error(400, "INVALID_IMAGE", "File is not a valid image.")


class LocalStorageService:
    def __init__(self, upload_dir: str | Path | None = None) -> None:
        settings = get_settings()
        self.upload_dir = Path(upload_dir or settings.local_upload_dir)
        self.max_bytes = settings.max_upload_bytes

    def _validate(self, data: bytes, content_type: str) -> str:
        if len(data) > self.max_bytes:
            raise_error(
                400,
                "FILE_TOO_LARGE",
                f"Image exceeds maximum size of {self.max_bytes} bytes.",
            )
        return _detect_image(data, content_type)

    def save(
        self,
        *,
        file: BinaryIO,
        filename: str,
        content_type: str,
        prefix: str = "",
    ) -> tuple[str, str]:
        data = file.read()
        ext = self._validate(data, content_type)
        key = f"{prefix}{uuid.uuid4().hex}{ext}".lstrip("/")
        dest = self.upload_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        url = f"/uploads/{key}"
        return url, key

    def delete(self, key: str) -> None:
        path = self.upload_dir / key
        if path.is_file():
            path.unlink(missing_ok=True)
