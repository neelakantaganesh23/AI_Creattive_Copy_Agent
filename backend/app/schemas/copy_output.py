"""Structured AI output schemas (§13).

Content rules are enforced during generation: a violation is fed back to the model
as a correction request rather than being reported after the fact. When the model
cannot satisfy every rule, the best attempt is kept, the quality status is
downgraded to ``warning``, and the surviving violations are surfaced in the UI --
an otherwise valid generation is never discarded.

The field length bounds below are structural sanity limits, not the marketing
rules; those live in the ``rules`` table and are applied by ``app.agents.rules``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Channel, QualityStatus, Severity


def _clean(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip()


class EmailCopy(BaseModel):
    headline: str = Field(min_length=1, max_length=400)
    sub_heading: str = Field(min_length=1, max_length=600)
    cta: str = Field(min_length=1, max_length=200)

    _normalise = field_validator("headline", "sub_heading", "cta", mode="before")(
        lambda value: _clean(value) if isinstance(value, str) else value
    )


class MobileCopy(BaseModel):
    superline: str = Field(min_length=1, max_length=200)
    pre_heading: str = Field(min_length=1, max_length=300)
    headline: str = Field(min_length=1, max_length=400)
    sub_heading: str = Field(min_length=1, max_length=600)
    cta: str = Field(min_length=1, max_length=200)

    _normalise = field_validator(
        "superline", "pre_heading", "headline", "sub_heading", "cta", mode="before"
    )(lambda value: _clean(value) if isinstance(value, str) else value)


class SMSCopy(BaseModel):
    description: str = Field(min_length=1, max_length=600)

    _normalise = field_validator("description", mode="before")(
        lambda value: _clean(value) if isinstance(value, str) else value
    )


class CopyBundle(BaseModel):
    """All three channels produced by one generation run."""

    email: EmailCopy
    mobile: MobileCopy
    sms: SMSCopy

    def channel_payload(self, channel: Channel) -> dict[str, str]:
        return {
            Channel.EMAIL: self.email,
            Channel.MOBILE: self.mobile,
            Channel.SMS: self.sms,
        }[channel].model_dump()

    def text_fields(self) -> list[str]:
        """Every generated string, used for repetition analysis."""
        return [
            self.email.headline,
            self.email.sub_heading,
            self.mobile.superline,
            self.mobile.pre_heading,
            self.mobile.headline,
            self.mobile.sub_heading,
            self.sms.description,
        ]


class RuleViolation(BaseModel):
    """One content rule the copy failed, from either the rules engine or the judge."""

    field: str
    severity: Severity = Severity.ERROR
    explanation: str
    rule_id: int | None = None
    rule_name: str | None = None
    suggestion: str | None = None

    def as_warning(self) -> str:
        label = self.field.replace("_", " ")
        return f"{label}: {self.explanation}"


class JudgeVerdict(BaseModel):
    """The LLM judge's assessment of a generated bundle."""

    passed: bool = True
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    naturalness: float = Field(default=1.0, ge=0.0, le=1.0)
    violations: list[RuleViolation] = Field(default_factory=list)
    reasoning: str = ""


class QualityCheck(BaseModel):
    status: QualityStatus = QualityStatus.PASSED
    warnings: list[str] = Field(default_factory=list)
    repetition_score: float = 0.0
    repetition_fixed: bool = False
    violations: list[RuleViolation] = Field(default_factory=list)
    judge_score: float | None = None
    naturalness: float | None = None
    revisions: int = 0


class GenerationOutput(BaseModel):
    """The persisted ``output_json`` payload."""

    channel: Channel
    language: str
    email: EmailCopy
    mobile: MobileCopy
    sms: SMSCopy
    quality: QualityCheck = Field(default_factory=QualityCheck)
    grounded: bool = False
    provider: str = "mock"
    models: dict[str, str | None] = Field(default_factory=dict)

    @property
    def bundle(self) -> CopyBundle:
        return CopyBundle(email=self.email, mobile=self.mobile, sms=self.sms)
