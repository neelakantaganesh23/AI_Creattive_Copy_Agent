"""Generation request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AgentStatus, Channel, GenerationStatus
from app.schemas.copy_output import GenerationOutput

BRIEF_MIN_LENGTH = 20
BRIEF_MAX_LENGTH = 4000


class GenerationCreate(BaseModel):
    brief: str = Field(min_length=BRIEF_MIN_LENGTH, max_length=BRIEF_MAX_LENGTH)
    channel: Channel
    brand_id: int | None = None
    product_id: int | None = None
    audience_segment_id: int | None = None
    language: str = Field(default="English", min_length=2, max_length=40)
    title: str | None = Field(default=None, max_length=200)

    @field_validator("brief")
    @classmethod
    def _brief_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < BRIEF_MIN_LENGTH:
            raise ValueError(
                f"The campaign brief must contain at least {BRIEF_MIN_LENGTH} characters."
            )
        return stripped


class AgentExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    generation_id: int
    agent_name: str
    title: str = ""
    description: str = ""
    sequence: int
    status: AgentStatus
    input_summary: str | None = None
    output_json: dict | None = None
    error_message: str | None = None
    model_name: str | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class GroundingSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    source_type: str
    snippet: str | None = None
    retrieved_at: datetime | None = None


class GenerationSummary(BaseModel):
    """Row shape for history and dashboard tables."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    brief: str
    channel: Channel
    language: str
    status: GenerationStatus
    grounded: bool
    execution_time_ms: int | None = None
    brand_name: str | None = None
    product_name: str | None = None
    audience_segment_name: str | None = None
    created_at: datetime
    updated_at: datetime


class GenerationDetail(GenerationSummary):
    user_id: int
    brand_id: int | None = None
    product_id: int | None = None
    audience_segment_id: int | None = None
    output: GenerationOutput | None = None
    provider: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    agent_executions: list[AgentExecutionResponse] = Field(default_factory=list)
    grounding_sources: list[GroundingSourceResponse] = Field(default_factory=list)


class GenerationStatusResponse(BaseModel):
    """Lightweight polling payload for the workflow stepper."""

    id: int
    status: GenerationStatus
    progress: float = Field(ge=0.0, le=1.0)
    execution_time_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    steps: list[AgentExecutionResponse] = Field(default_factory=list)
    output: GenerationOutput | None = None
