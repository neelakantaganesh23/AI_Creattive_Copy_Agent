"""Shared response envelopes and query models."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """Standard paginated payload."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """The single error shape returned by every endpoint (§16)."""

    error: ErrorDetail


class MessageResponse(BaseModel):
    message: str


class SystemInfo(BaseModel):
    app_name: str
    app_version: str
    environment: str
    ai_provider: str
    grounding_enabled: bool
    grounding_provider: str
    models: dict[str, str | None]
    channel_limits: dict[str, dict[str, int]]
