"""Generated image storage."""

from functools import lru_cache

from app.services.media.storage import LocalMediaStorage, MediaStorage


@lru_cache
def get_media_storage() -> MediaStorage:
    return LocalMediaStorage()


def reset_media_storage_cache() -> None:
    """Clear the cached storage backend. Used by tests that swap configuration."""
    get_media_storage.cache_clear()


__all__ = [
    "LocalMediaStorage",
    "MediaStorage",
    "get_media_storage",
    "reset_media_storage_cache",
]
