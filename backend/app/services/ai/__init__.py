"""Web search grounding: interface, backends and selection."""

from app.services.ai.factory import get_grounding_provider, reset_provider_cache
from app.services.ai.grounding import GroundingProvider

__all__ = [
    "GroundingProvider",
    "get_grounding_provider",
    "reset_provider_cache",
]
