"""Opik tracing seam tests (§18). Never touches Comet or the network.

The suite pins ``OPIK_ENABLED=false`` (see conftest), so these tests exercise
both the disabled path directly and the active path with the SDK stubbed.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.observability import opik_tracing


def test_opik_active_requires_a_destination(monkeypatch) -> None:
    monkeypatch.setattr(settings, "opik_enabled", False)
    assert settings.opik_active is False

    # Enabled but with nowhere to send data is still inactive.
    monkeypatch.setattr(settings, "opik_enabled", True)
    monkeypatch.setattr(settings, "opik_api_key", None)
    monkeypatch.setattr(settings, "opik_url_override", None)
    assert settings.opik_active is False

    # A cloud key is a destination.
    monkeypatch.setattr(settings, "opik_api_key", "key")
    assert settings.opik_active is True

    # So is a self-hosted URL, without a key.
    monkeypatch.setattr(settings, "opik_api_key", None)
    monkeypatch.setattr(settings, "opik_url_override", "http://localhost:5173/api/")
    assert settings.opik_active is True


def test_traced_is_identity_when_disabled() -> None:
    assert settings.opik_active is False

    calls: list[int] = []

    @opik_tracing.traced("noop", span_type="llm")
    async def work(x: int) -> int:
        calls.append(x)
        return x * 2

    # The decorator returned the function unchanged -- same object, no wrapper.
    assert asyncio.run(work(21)) == 42
    assert calls == [21]


def test_annotators_and_lifecycle_are_no_ops_when_disabled() -> None:
    assert settings.opik_active is False
    # None of these may raise or require the SDK.
    opik_tracing.configure_opik()
    opik_tracing.annotate_current_span(name="x", usage={"total_tokens": 1})
    opik_tracing.annotate_current_trace(metadata={"generation_id": 1})
    opik_tracing.flush_opik()


def test_traced_builds_a_real_decorator_when_active(monkeypatch) -> None:
    """When active, ``traced`` delegates to ``opik.track`` with our project."""
    import opik

    monkeypatch.setattr(settings, "opik_enabled", True)
    monkeypatch.setattr(settings, "opik_api_key", "test-key")
    monkeypatch.setattr(settings, "opik_url_override", None)

    seen: dict[str, object] = {}

    def fake_track(**kwargs):
        seen.update(kwargs)
        return lambda fn: fn  # identity, so no network is touched

    monkeypatch.setattr(opik, "track", fake_track)

    @opik_tracing.traced("copy_generation", span_type="llm", capture_output=False)
    async def work() -> str:
        return "ok"

    assert asyncio.run(work()) == "ok"
    assert seen["name"] == "copy_generation"
    assert seen["type"] == "llm"
    assert seen["capture_output"] is False
    assert seen["project_name"] == settings.opik_project_name


def test_annotate_routes_to_opik_context_when_active(monkeypatch) -> None:
    from opik import opik_context

    monkeypatch.setattr(settings, "opik_enabled", True)
    monkeypatch.setattr(settings, "opik_api_key", "test-key")

    captured: dict[str, object] = {}
    monkeypatch.setattr(opik_context, "update_current_span", lambda **kw: captured.update(kw))

    opik_tracing.annotate_current_span(name="data_extraction", model="gemini-x")
    assert captured == {"name": "data_extraction", "model": "gemini-x"}


def test_annotate_swallows_sdk_errors_when_active(monkeypatch) -> None:
    """A tracing fault must degrade to a log line, never break a generation."""
    from opik import opik_context

    monkeypatch.setattr(settings, "opik_enabled", True)
    monkeypatch.setattr(settings, "opik_api_key", "test-key")

    def boom(**_kw):
        raise RuntimeError("opik backend unreachable")

    monkeypatch.setattr(opik_context, "update_current_span", boom)
    monkeypatch.setattr(opik_context, "update_current_trace", boom)

    # Must not raise.
    opik_tracing.annotate_current_span(name="x")
    opik_tracing.annotate_current_trace(metadata={"a": 1})
