"""Opik integration internals.

Design mirrors the rest of the codebase: a single config-selected seam with a
credential-free default. ``traced`` is applied at import time, so when
``OPIK_ENABLED`` is false at process start the decorated functions are returned
unchanged and carry zero overhead for the whole process lifetime.

Observability must never break a generation: every call into the Opik SDK is
wrapped so a tracing fault degrades to a log line, not a failed request.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeVar

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.observability.opik")

F = TypeVar("F", bound=Callable[..., Any])
SpanType = Literal["general", "tool", "llm", "guardrail"]

_configured = False


def configure_opik() -> None:
    """Point the Opik SDK at Comet cloud or a self-hosted instance.

    No-op when tracing is inactive. Safe to call more than once. A configuration
    failure is logged and swallowed -- it must never stop the app from starting.
    """
    global _configured
    if not settings.opik_active or _configured:
        return
    try:
        import opik

        opik.configure(
            api_key=settings.opik_api_key,
            workspace=settings.opik_workspace,
            url=settings.opik_url_override,
            use_local=bool(settings.opik_url_override),
            force=True,
        )
        _configured = True
        logger.info(
            "opik tracing enabled",
            extra={
                "project": settings.opik_project_name,
                "self_hosted": bool(settings.opik_url_override),
            },
        )
    except Exception:
        logger.exception("failed to configure opik; continuing without tracing")


def traced(
    name: str | None = None,
    *,
    span_type: SpanType = "general",
    tags: list[str] | None = None,
    ignore_arguments: list[str] | None = None,
    capture_input: bool = True,
    capture_output: bool = True,
) -> Callable[[F], F]:
    """Decorator that records a span, or does nothing when tracing is inactive.

    Evaluated once at import time. When inactive it returns the function
    unchanged, so there is no per-call cost and no dependency on the Opik SDK on
    the default path.
    """
    if not settings.opik_active:
        return lambda fn: fn

    try:
        import opik

        return opik.track(  # type: ignore[return-value]
            name=name,
            type=span_type,
            tags=tags,
            ignore_arguments=ignore_arguments,
            capture_input=capture_input,
            capture_output=capture_output,
            project_name=settings.opik_project_name,
        )
    except Exception:
        logger.exception("failed to build opik span decorator; leaving function untraced")
        return lambda fn: fn


def annotate_current_span(**fields: Any) -> None:
    """Attach data (name, usage, model, provider, cost, metadata) to the active
    span. No-op when tracing is inactive; never raises."""
    if not settings.opik_active:
        return
    try:
        from opik import opik_context

        opik_context.update_current_span(**fields)
    except Exception:
        logger.debug("opik span annotation failed", exc_info=True)


def annotate_current_trace(**fields: Any) -> None:
    """Attach data to the active trace root. No-op when inactive; never raises."""
    if not settings.opik_active:
        return
    try:
        from opik import opik_context

        opik_context.update_current_trace(**fields)
    except Exception:
        logger.debug("opik trace annotation failed", exc_info=True)


def flush_opik() -> None:
    """Flush buffered traces on shutdown so nothing is lost. No-op when inactive."""
    if not settings.opik_active:
        return
    try:
        import opik

        opik.flush_tracker()
    except Exception:
        logger.debug("opik flush failed", exc_info=True)
