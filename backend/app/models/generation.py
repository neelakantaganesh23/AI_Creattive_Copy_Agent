"""Generation, agent execution and grounding source models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import AgentStatus, GenerationStatus
from app.models.taxonomy import AudienceSegment, Brand, Product

if TYPE_CHECKING:
    from app.models.user import User


class Generation(Base, TimestampMixin):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Untitled campaign")
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    audience_segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("audience_segments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(40), nullable=False, default="English")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GenerationStatus.PENDING, index=True
    )
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    grounded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)

    user: Mapped[User] = relationship(back_populates="generations")
    brand: Mapped[Brand | None] = relationship()
    product: Mapped[Product | None] = relationship()
    audience_segment: Mapped[AudienceSegment | None] = relationship()
    agent_executions: Mapped[list[AgentExecution]] = relationship(
        back_populates="generation",
        cascade="all, delete-orphan",
        order_by="AgentExecution.sequence",
    )
    grounding_sources: Mapped[list[GroundingSource]] = relationship(
        back_populates="generation", cascade="all, delete-orphan"
    )


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    generation_id: Mapped[int] = mapped_column(
        ForeignKey("generations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AgentStatus.PENDING, index=True
    )
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    generation: Mapped[Generation] = relationship(back_populates="agent_executions")


class GroundingSource(Base):
    __tablename__ = "grounding_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    generation_id: Mapped[int] = mapped_column(
        ForeignKey("generations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="web")
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    generation: Mapped[Generation] = relationship(back_populates="grounding_sources")
