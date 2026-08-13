"""Dashboard aggregate schemas (§7). All values are computed from the database."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.generation import GenerationSummary


class ChannelInfo(BaseModel):
    value: str
    label: str
    description: str
    fields: list[str]


class DashboardSummary(BaseModel):
    copies_generated_this_month: int
    copies_generated_total: int
    audience_segments_configured: int
    channels_supported: int
    average_generation_time_ms: int | None
    success_rate: float
    channels: list[ChannelInfo]
    generations_by_channel: dict[str, int]
    generations_by_status: dict[str, int]


class DashboardRecent(BaseModel):
    items: list[GenerationSummary]
