"""AI provider interface (§21).

Everything the workflow needs from a model lives behind this protocol so the mock
and Gemini implementations never mix. Concrete providers live in
``mock_provider.py`` and ``gemini_provider.py``; selection happens in ``factory.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.models.enums import Channel
from app.schemas.copy_output import CopyBundle


@dataclass(slots=True)
class ExtractedBrief:
    """Structured result of Agent 1 (data extraction)."""

    brand: str | None = None
    products: list[str] = field(default_factory=list)
    skus: list[str] = field(default_factory=list)
    # Only populated when a public figure is explicitly named in the brief.
    athletes: list[str] = field(default_factory=list)
    campaign_goal: str | None = None
    features: list[str] = field(default_factory=list)
    tone: str | None = None
    key_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "brand": self.brand,
            "products": self.products,
            "skus": self.skus,
            "athletes": self.athletes,
            "campaign_goal": self.campaign_goal,
            "features": self.features,
            "tone": self.tone,
            "key_message": self.key_message,
        }


@dataclass(slots=True)
class GroundingResult:
    """Result of Agent 2 (web search grounding)."""

    grounded: bool = False
    sources: list[GroundingSourceData] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GroundingSourceData:
    title: str
    url: str
    source_type: str = "web"
    snippet: str | None = None


@dataclass(slots=True)
class CopyRequest:
    """Everything Agent 3 needs to write the copy."""

    brief: str
    channel: Channel
    language: str
    extracted: ExtractedBrief
    grounding: GroundingResult
    audience_name: str | None = None
    audience_description: str | None = None
    audience_tone: str | None = None
    brand_name: str | None = None
    brand_guidelines: str | None = None
    product_name: str | None = None
    product_features: list[str] = field(default_factory=list)
    channel_limits: dict[str, dict[str, int]] = field(default_factory=dict)
    prompt_template: str | None = None
    # Copy previously produced for other audience segments, used to steer the
    # model away from repeating itself.
    previous_copy: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProviderInfo:
    name: str
    fast_model: str | None = None
    quality_model: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"fast": self.fast_model, "quality": self.quality_model}


@runtime_checkable
class AIProvider(Protocol):
    """Contract every provider implements."""

    name: str

    def info(self) -> ProviderInfo: ...

    async def extract_brief(self, brief: str, *, language: str) -> ExtractedBrief:
        """Agent 1: pull structured campaign data out of the raw brief."""
        ...

    async def generate_copy(self, request: CopyRequest) -> CopyBundle:
        """Agent 3: produce Email, Mobile and SMS copy."""
        ...

    async def rewrite_for_variety(
        self, request: CopyRequest, bundle: CopyBundle, repeated_phrases: list[str]
    ) -> CopyBundle:
        """Agent 4: rewrite copy that overlaps previous generations."""
        ...
