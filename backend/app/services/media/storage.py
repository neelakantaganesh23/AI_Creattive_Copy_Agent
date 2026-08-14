"""Generated image storage.

Images are written to local disk and served as static files. Storage sits behind
an interface, mirroring ``app.services.email.sender``, so a future deployment can
swap in object storage without touching the agent that produces the bytes.
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.media")

_EXTENSION_BY_MEDIA_TYPE: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(hint: str) -> str:
    slug = _SLUG_RE.sub("-", hint.lower()).strip("-")
    return slug or "image"


class MediaStorage(Protocol):
    name: str

    def save(self, data: bytes, *, media_type: str, filename_hint: str) -> str:
        """Persist ``data`` and return the URL path clients can load it from."""
        ...


class LocalMediaStorage:
    """Writes generated images to ``settings.media_dir``.

    The suitable default for a single-instance deployment; the ``media_dir``
    contents must be on a volume shared with whatever serves ``/media`` when
    running more than one backend instance.
    """

    name = "local"

    def __init__(self) -> None:
        self._root = Path(settings.media_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, *, media_type: str, filename_hint: str) -> str:
        extension = _EXTENSION_BY_MEDIA_TYPE.get(media_type, "bin")
        # A random suffix, not just the hint, so retries never collide or overwrite.
        filename = f"{_slugify(filename_hint)}-{secrets.token_hex(4)}.{extension}"
        path = self._root / filename
        path.write_bytes(data)
        # "filename" collides with a reserved LogRecord attribute; "media_filename" doesn't.
        logger.info(
            "saved generated image", extra={"media_filename": filename, "bytes": len(data)}
        )
        return f"{settings.media_url_prefix.rstrip('/')}/{filename}"
