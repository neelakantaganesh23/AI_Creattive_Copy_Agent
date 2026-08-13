"""Structured AI output schemas (§13).

Character limits are *recommended* rather than hard: exceeding one downgrades the
quality status to ``warning`` and is surfaced in the UI, but does not discard an
otherwise valid generation. Limits come from settings so they stay configurable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.models.enums import Channel, QualityStatus


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


class QualityCheck(BaseModel):
    status: QualityStatus = QualityStatus.PASSED
    warnings: list[str] = Field(default_factory=list)
    repetition_score: float = 0.0
    repetition_fixed: bool = False


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


def check_channel_limits(bundle: CopyBundle) -> list[str]:
    """Return a human-readable warning per field over its configured limit."""
    limits = settings.channel_limits
    warnings: list[str] = []
    for channel, payload in (
        ("email", bundle.email.model_dump()),
        ("mobile", bundle.mobile.model_dump()),
        ("sms", bundle.sms.model_dump()),
    ):
        for field, value in payload.items():
            limit = limits[channel].get(field)
            if limit is not None and len(value) > limit:
                label = field.replace("_", " ")
                warnings.append(
                    f"{channel.upper()} {label} is {len(value)} characters "
                    f"(recommended maximum {limit})."
                )
    return warnings
