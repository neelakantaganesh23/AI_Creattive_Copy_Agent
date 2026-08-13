"""Data-access layer. Route handlers and services depend on these, not on queries."""

from app.repositories.base import BaseRepository
from app.repositories.generation_repository import (
    AgentExecutionRepository,
    GenerationRepository,
    GroundingSourceRepository,
)
from app.repositories.taxonomy_repository import (
    AudienceSegmentRepository,
    BrandRepository,
    CTARuleRepository,
    ProductRepository,
    TemplateRepository,
)
from app.repositories.user_repository import RefreshTokenRepository, UserRepository

__all__ = [
    "AgentExecutionRepository",
    "AudienceSegmentRepository",
    "BaseRepository",
    "BrandRepository",
    "CTARuleRepository",
    "GenerationRepository",
    "GroundingSourceRepository",
    "ProductRepository",
    "RefreshTokenRepository",
    "TemplateRepository",
    "UserRepository",
]
