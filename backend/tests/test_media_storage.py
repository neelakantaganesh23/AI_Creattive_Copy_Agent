"""Tests for generated image storage.

Regression coverage for a real bug: passing ``filename`` in ``extra=`` to the
standard library logger raises ``KeyError`` because it collides with a reserved
``LogRecord`` attribute. The suite normally runs at ``LOG_LEVEL=WARNING``, which
short-circuits ``logger.info`` before that attribute check ever runs -- so this
test sets the level to INFO explicitly to actually exercise the code path.
"""

from __future__ import annotations

import logging

from app.services.media.storage import LocalMediaStorage


def test_save_writes_the_file_and_returns_its_url(tmp_path, monkeypatch) -> None:
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "media_dir", str(tmp_path))
    monkeypatch.setattr(app_settings, "media_url_prefix", "/media")

    url = LocalMediaStorage().save(
        b"<svg></svg>", media_type="image/svg+xml", filename_hint="AeroFlex Hero"
    )

    assert url.startswith("/media/aeroflex-hero-")
    assert url.endswith(".svg")
    saved = tmp_path / url.removeprefix("/media/")
    assert saved.read_bytes() == b"<svg></svg>"


def test_save_logs_at_info_level_without_crashing(tmp_path, monkeypatch, caplog) -> None:
    """Exercises the logger.info(..., extra=...) call with INFO enabled."""
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "media_dir", str(tmp_path))

    with caplog.at_level(logging.INFO, logger="app.media"):
        LocalMediaStorage().save(b"data", media_type="image/png", filename_hint="test")

    assert any("saved generated image" in record.message for record in caplog.records)
