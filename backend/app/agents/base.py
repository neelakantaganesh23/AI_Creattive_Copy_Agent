"""Shared types for the multi-stage generation workflow (§12).

Agents never touch the ORM. They read a plain :class:`WorkflowContext` and report
progress through a :class:`WorkflowRecorder`, which the generation service
implements against the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.agents.types import ExtractedBrief, GroundingResult, RuleData
from app.models.enums import AgentName, Channel
from app.schemas.copy_output import CopyBundle, GenerationOutput, JudgeVerdict, QualityCheck


@dataclass(slots=True)
class BrandData:
    id: int
    name: str
    guidelines: str | None = None


@dataclass(slots=True)
class ProductData:
    id: int
    name: str
    features: list[str] = field(default_factory=list)
    sku: str | None = None


@dataclass(slots=True)
class AudienceData:
    id: int
    name: str
    description: str | None = None
    tone_guidance: str | None = None


@dataclass(slots=True)
class CTARuleData:
    id: int
    template: str
    priority: int
    brand_id: int | None = None
    product_id: int | None = None
    channel: str | None = None


@dataclass
class WorkflowContext:
    """Input state plus the results each agent contributes."""

    generation_id: int
    brief: str
    channel: Channel
    language: str
    brand: BrandData | None = None
    product: ProductData | None = None
    audience: AudienceData | None = None
    cta_rules: list[CTARuleData] = field(default_factory=list)
    # Admin-managed content rules already narrowed to this generation's scope.
    rules: list[RuleData] = field(default_factory=list)
    prompt_template: str | None = None
    previous_copy: list[str] = field(default_factory=list)

    # Results, populated as the workflow proceeds.
    extracted: ExtractedBrief | None = None
    grounding: GroundingResult | None = None
    bundle: CopyBundle | None = None
    output: GenerationOutput | None = None
    quality: QualityCheck = field(default_factory=QualityCheck)
    judge: JudgeVerdict | None = None
    applied_cta_rule_id: int | None = None
    # Populated by the image generation stage. Null when disabled or unavailable
    # for this run -- the stage failing never fails the whole generation.
    image_url: str | None = None
    image_prompt: str | None = None
    warnings: list[str] = field(default_factory=list)


class WorkflowRecorder(Protocol):
    """Persists per-agent progress so the frontend can poll it."""

    def start(self, agent: AgentName, *, input_summary: str | None = None) -> None: ...

    def complete(
        self,
        agent: AgentName,
        *,
        output: dict[str, Any] | None = None,
        model_name: str | None = None,
    ) -> None: ...

    def fail(self, agent: AgentName, *, error: str) -> None: ...

    def skip(self, agent: AgentName, *, reason: str) -> None: ...


class NullRecorder:
    """No-op recorder, used in unit tests that only exercise agent logic."""

    def start(self, agent: AgentName, *, input_summary: str | None = None) -> None:
        return None

    def complete(
        self,
        agent: AgentName,
        *,
        output: dict[str, Any] | None = None,
        model_name: str | None = None,
    ) -> None:
        return None

    def fail(self, agent: AgentName, *, error: str) -> None:
        return None

    def skip(self, agent: AgentName, *, reason: str) -> None:
        return None


class Agent(Protocol):
    name: AgentName

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None: ...
