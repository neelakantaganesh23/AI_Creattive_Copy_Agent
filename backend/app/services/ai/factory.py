"""Provider selection. The only place that decides mock vs. Gemini."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.grounding import GroundingProvider, build_grounding_provider
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.provider import AIProvider

logger = get_logger("app.ai.factory")


@lru_cache
def get_ai_provider() -> AIProvider:
    """Return the configured AI provider (cached for the process lifetime)."""
    if settings.ai_provider == "gemini":
        # Imported lazily so the mock path never pulls in the SDK.
        from app.services.ai.gemini_provider import GeminiAIProvider

        logger.info("using Gemini AI provider")
        return GeminiAIProvider()

    logger.warning(
        "using the MOCK AI provider - generated copy is simulated, not model output",
        extra={"ai_provider": "mock"},
    )
    return MockAIProvider()


@lru_cache
def get_grounding_provider() -> GroundingProvider:
    provider = build_grounding_provider()
    logger.info(
        "grounding provider selected",
        extra={"grounding_provider": provider.name, "enabled": settings.grounding_enabled},
    )
    return provider


def reset_provider_cache() -> None:
    """Clear cached providers. Used by tests that swap configuration."""
    get_ai_provider.cache_clear()
    get_grounding_provider.cache_clear()
