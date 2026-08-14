"""Plain data passed between workflow stages.

These types used to live in ``app/services/ai/provider.py`` alongside the bespoke
``AIProvider`` protocol. That protocol is gone -- Pydantic AI owns the model
abstraction now -- but the shapes themselves are still the contract between the
agents, the grounding providers and the persistence layer, so they live here where
the agents can own them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import Channel


@dataclass(slots=True)
class ExtractedBrief:
    """Structured result of the data extraction stage."""

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
class GroundingSourceData:
    title: str
    url: str
    source_type: str = "web"
    snippet: str | None = None


@dataclass(slots=True)
class GroundingResult:
    """Result of the web search grounding stage."""

    grounded: bool = False
    sources: list[GroundingSourceData] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RuleData:
    """An admin-managed content rule, detached from the ORM."""

    id: int
    name: str
    rule_type: str
    value: str
    severity: str
    channel: str | None = None
    field_name: str | None = None
    brand_id: int | None = None
    audience_segment_id: int | None = None
    description: str | None = None
    priority: int = 0

    @property
    def is_deterministic(self) -> bool:
        """True when the rule can be checked in code rather than by the judge."""
        from app.models.enums import RuleType

        return self.rule_type != RuleType.GUIDELINE


@dataclass(slots=True)
class CopyRequest:
    """Everything the copy generation and revision stages need."""

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
    prompt_template: str | None = None
    rules: list[RuleData] = field(default_factory=list)
    # Copy previously produced for other audience segments, used to steer the
    # model away from repeating itself.
    previous_copy: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GeneratedImage:
    """Raw bytes produced by the image generation stage, before storage."""

    data: bytes
    media_type: str


@dataclass(slots=True)
class ModelInfo:
    """Which models the current runtime is wired to, for logging and display."""

    name: str
    fast_model: str | None = None
    quality_model: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"fast": self.fast_model, "quality": self.quality_model}
