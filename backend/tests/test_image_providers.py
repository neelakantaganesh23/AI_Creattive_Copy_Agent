"""Tests for the pluggable image generation providers (§18)."""

from __future__ import annotations

import httpx
import pytest

from app.core.errors import AINotConfiguredError, AIProviderError, AIQuotaExceededError
from app.services.ai.image_generation import (
    GeminiImageProvider,
    MockImageProvider,
    StabilityImageProvider,
    build_image_provider,
)


async def test_mock_provider_returns_a_placeholder() -> None:
    image = await MockImageProvider().generate("A running shoe hero image")
    assert image.media_type == "image/svg+xml"
    assert image.data.startswith(b"<svg")


def test_build_image_provider_selects_by_setting(monkeypatch) -> None:
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "image_provider", "mock")
    assert isinstance(build_image_provider(), MockImageProvider)

    monkeypatch.setattr(app_settings, "image_provider", "gemini")
    assert isinstance(build_image_provider(), GeminiImageProvider)


def test_stability_requires_an_api_key(monkeypatch) -> None:
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "stability_api_key", None)
    with pytest.raises(AINotConfiguredError, match="STABILITY_API_KEY"):
        StabilityImageProvider()


def test_a_provider_missing_its_key_fails_the_generation(
    client, marketer_headers, taxonomy, monkeypatch
) -> None:
    """A provider that cannot be constructed must not strand the run at 'running'.

    The provider is built for each run, so a missing credential raises before the
    workflow starts. That has to be reported as a failed generation.
    """
    from app.core.config import settings as app_settings
    from app.services.ai.factory import reset_provider_cache
    from tests.conftest import generation_payload

    monkeypatch.setattr(app_settings, "image_provider", "stability")
    monkeypatch.setattr(app_settings, "stability_api_key", None)
    reset_provider_cache()

    response = client.post(
        "/api/v1/generations", headers=marketer_headers, json=generation_payload(taxonomy)
    )
    assert response.status_code == 202, response.text

    detail = client.get(
        f"/api/v1/generations/{response.json()['id']}", headers=marketer_headers
    ).json()
    assert detail["status"] == "failed"
    assert detail["error_code"] == "AI_NOT_CONFIGURED"
    assert "STABILITY_API_KEY" in detail["error_message"]

    reset_provider_cache()


def _stability_provider(monkeypatch, handler):
    """Build a Stability provider whose HTTP calls hit a mock transport."""
    from app.core.config import settings as app_settings
    from app.services.ai import image_generation as image_module

    monkeypatch.setattr(app_settings, "stability_api_key", "sk-test-key")

    real_client = httpx.AsyncClient

    def fake_client(*_args, **kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(image_module.httpx, "AsyncClient", fake_client)
    return image_module.StabilityImageProvider()


async def test_stability_returns_the_generated_image(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        captured["accept"] = request.headers.get("accept")
        return httpx.Response(200, content=b"\x89PNG fake-bytes")

    provider = _stability_provider(monkeypatch, handler)
    image = await provider.generate("A running shoe hero image")

    assert image.data == b"\x89PNG fake-bytes"
    assert image.media_type == "image/png"
    assert captured["auth"] == "Bearer sk-test-key"
    assert captured["accept"] == "image/*"


async def test_stability_reports_quota_exhaustion(monkeypatch) -> None:
    provider = _stability_provider(
        monkeypatch, lambda _request: httpx.Response(429, json={"errors": ["quota"]})
    )
    with pytest.raises(AIQuotaExceededError):
        await provider.generate("A running shoe hero image")


async def test_stability_reports_bad_key(monkeypatch) -> None:
    provider = _stability_provider(monkeypatch, lambda _request: httpx.Response(401, json={}))
    with pytest.raises(AINotConfiguredError, match="key was rejected"):
        await provider.generate("A running shoe hero image")


async def test_stability_reports_other_failures(monkeypatch) -> None:
    provider = _stability_provider(monkeypatch, lambda _request: httpx.Response(500, json={}))
    with pytest.raises(AIProviderError):
        await provider.generate("A running shoe hero image")
