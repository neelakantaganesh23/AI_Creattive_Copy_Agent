"""Schemas for admin-managed content rules."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import RULE_FIELD_NAMES, Channel, RuleType, Severity


def validate_rule_value(rule_type: RuleType | str, value: str) -> str:
    """Reject a value the engine could never apply, at the API boundary."""
    # Callers may pass the raw column value, which is a plain string.
    rule_type = RuleType(rule_type)
    value = value.strip()
    if not value:
        raise ValueError("A rule value is required.")

    if rule_type in (
        RuleType.MAX_CHARS,
        RuleType.MIN_CHARS,
        RuleType.MAX_WORDS,
        RuleType.MIN_WORDS,
    ):
        try:
            number = int(value)
        except ValueError:
            raise ValueError(f"{rule_type.value} requires a whole number.") from None
        if number < 1:
            raise ValueError(f"{rule_type.value} must be at least 1.")
        return str(number)

    if rule_type in (RuleType.FORBIDDEN_TERMS, RuleType.REQUIRED_TERMS):
        terms = [term.strip() for term in value.split(",") if term.strip()]
        if not terms:
            raise ValueError("Provide at least one comma separated term.")
        return ", ".join(terms)

    if rule_type is RuleType.REGEX:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"Invalid regular expression: {exc}") from None

    return value


class RuleBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    rule_type: RuleType
    value: str = Field(min_length=1, max_length=2000)
    severity: Severity = Severity.ERROR
    channel: Channel | None = None
    field_name: str | None = Field(default=None, max_length=40)
    brand_id: int | None = None
    audience_segment_id: int | None = None
    priority: int = Field(default=0, ge=0, le=1000)
    is_active: bool = True

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.field_name is not None and self.field_name not in RULE_FIELD_NAMES:
            raise ValueError(
                "field_name must be one of: " + ", ".join(sorted(RULE_FIELD_NAMES))
            )
        object.__setattr__(self, "value", validate_rule_value(self.rule_type, self.value))
        return self


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    """Partial update. ``value`` is re-validated against the effective rule type."""

    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    rule_type: RuleType | None = None
    value: str | None = Field(default=None, min_length=1, max_length=2000)
    severity: Severity | None = None
    channel: Channel | None = None
    field_name: str | None = Field(default=None, max_length=40)
    brand_id: int | None = None
    audience_segment_id: int | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    is_active: bool | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.field_name is not None and self.field_name not in RULE_FIELD_NAMES:
            raise ValueError(
                "field_name must be one of: " + ", ".join(sorted(RULE_FIELD_NAMES))
            )
        return self


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    rule_type: RuleType
    value: str
    severity: Severity
    channel: Channel | None
    field_name: str | None
    brand_id: int | None
    audience_segment_id: int | None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
