"""Grounding provider selection.

Model selection used to live here too. It now belongs to ``app.agents.runtime``,
which builds the Pydantic AI model directly; grounding is a plain HTTP search
backend and keeps its own factory.
"""

from __future__ import annotations

from functools import lru_cache

from app.agents.runtime import reset_model_cache
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.grounding import GroundingProvider, build_grounding_provider

logger = get_logger("app.ai.factory")


@lru_cache
def get_grounding_provider() -> GroundingProvider:
    provider = build_grounding_provider()
    logger.info(
        "grounding provider selected",
        extra={"grounding_provider": provider.name, "enabled": settings.grounding_enabled},
    )
    return provider


def reset_provider_cache() -> None:
    """Clear cached providers and models. Used by tests that swap configuration."""
    get_grounding_provider.cache_clear()
    reset_model_cache()
