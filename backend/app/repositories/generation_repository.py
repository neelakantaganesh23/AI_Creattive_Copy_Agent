"""Queries for generations, agent executions and grounding sources."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models.enums import AgentName, GenerationStatus
from app.models.generation import AgentExecution, Generation, GroundingSource
from app.repositories.base import BaseRepository


class GenerationRepository(BaseRepository[Generation]):
    model = Generation

    def get_with_relations(self, generation_id: int) -> Generation | None:
        return self.session.scalar(
            select(Generation)
            .options(
                joinedload(Generation.brand),
                joinedload(Generation.product),
                joinedload(Generation.audience_segment),
                joinedload(Generation.agent_executions),
                joinedload(Generation.grounding_sources),
            )
            .where(Generation.id == generation_id)
        )

    def list_generations(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        user_id: int | None = None,
        channel: str | None = None,
        status: str | None = None,
        audience_segment_id: int | None = None,
        brand_id: int | None = None,
        search: str | None = None,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> tuple[list[Generation], int]:
        statement = select(Generation).options(
            joinedload(Generation.brand),
            joinedload(Generation.product),
            joinedload(Generation.audience_segment),
        )
        count_statement = select(func.count()).select_from(Generation)

        conditions = []
        if user_id is not None:
            conditions.append(Generation.user_id == user_id)
        if channel:
            conditions.append(Generation.channel == channel)
        if status:
            conditions.append(Generation.status == status)
        if audience_segment_id is not None:
            conditions.append(Generation.audience_segment_id == audience_segment_id)
        if brand_id is not None:
            conditions.append(Generation.brand_id == brand_id)
        if search:
            pattern = f"%{search.lower()}%"
            conditions.append(
                func.lower(Generation.title).like(pattern)
                | func.lower(Generation.brief).like(pattern)
            )
        for condition in conditions:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        column = getattr(Generation, order_by, Generation.created_at)
        statement = statement.order_by(column.desc() if descending else column.asc())
        statement = statement.offset(offset).limit(limit)

        items = list(self.session.scalars(statement).unique().all())
        total = self.session.scalar(count_statement) or 0
        return items, total

    def list_unfinished(self) -> list[Generation]:
        """Generations still queued or mid-run, oldest first."""
        return list(
            self.session.scalars(
                select(Generation)
                .where(
                    Generation.status.in_(
                        (GenerationStatus.PENDING, GenerationStatus.RUNNING)
                    )
                )
                .order_by(Generation.id)
            ).all()
        )

    def recent_completed(
        self, *, limit: int = 5, user_id: int | None = None
    ) -> list[Generation]:
        statement = (
            select(Generation)
            .options(
                joinedload(Generation.brand),
                joinedload(Generation.product),
                joinedload(Generation.audience_segment),
            )
            .order_by(Generation.created_at.desc())
            .limit(limit)
        )
        if user_id is not None:
            statement = statement.where(Generation.user_id == user_id)
        return list(self.session.scalars(statement).unique().all())

    def recent_outputs_for_repetition(
        self,
        *,
        limit: int,
        brand_id: int | None,
        product_id: int | None,
        exclude_generation_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Recent successful outputs for the same brand/product (§12, Agent 4)."""
        statement = (
            select(Generation.output_json)
            .where(
                Generation.status == GenerationStatus.COMPLETED,
                Generation.output_json.is_not(None),
            )
            .order_by(Generation.created_at.desc())
            .limit(limit)
        )
        if brand_id is not None:
            statement = statement.where(Generation.brand_id == brand_id)
        if product_id is not None:
            statement = statement.where(Generation.product_id == product_id)
        if exclude_generation_id is not None:
            statement = statement.where(Generation.id != exclude_generation_id)
        return [row for row in self.session.scalars(statement).all() if row]

    # -- Dashboard aggregates ------------------------------------------------
    def count_since(self, since: datetime, *, user_id: int | None = None) -> int:
        statement = select(func.count()).select_from(Generation).where(
            Generation.created_at >= since
        )
        if user_id is not None:
            statement = statement.where(Generation.user_id == user_id)
        return self.session.scalar(statement) or 0

    def count_all(self, *, user_id: int | None = None) -> int:
        statement = select(func.count()).select_from(Generation)
        if user_id is not None:
            statement = statement.where(Generation.user_id == user_id)
        return self.session.scalar(statement) or 0

    def average_execution_time_ms(self, *, user_id: int | None = None) -> int | None:
        statement = select(func.avg(Generation.execution_time_ms)).where(
            Generation.execution_time_ms.is_not(None)
        )
        if user_id is not None:
            statement = statement.where(Generation.user_id == user_id)
        value = self.session.scalar(statement)
        return int(value) if value is not None else None

    def count_by(self, column_name: str, *, user_id: int | None = None) -> dict[str, int]:
        column = getattr(Generation, column_name)
        statement = select(column, func.count()).group_by(column)
        if user_id is not None:
            statement = statement.where(Generation.user_id == user_id)
        return {str(key): count for key, count in self.session.execute(statement).all() if key}

    @staticmethod
    def month_start(now: datetime | None = None) -> datetime:
        current = now or datetime.now(UTC)
        return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def days_ago(days: int) -> datetime:
        return datetime.now(UTC) - timedelta(days=days)


class AgentExecutionRepository(BaseRepository[AgentExecution]):
    model = AgentExecution

    def list_for_generation(self, generation_id: int) -> list[AgentExecution]:
        return list(
            self.session.scalars(
                select(AgentExecution)
                .where(AgentExecution.generation_id == generation_id)
                .order_by(AgentExecution.sequence)
            ).all()
        )

    def get_for_agent(self, generation_id: int, agent_name: AgentName) -> AgentExecution | None:
        return self.session.scalar(
            select(AgentExecution).where(
                AgentExecution.generation_id == generation_id,
                AgentExecution.agent_name == agent_name.value,
            )
        )

    def list_logs(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        generation_id: int | None = None,
        agent_name: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AgentExecution], int]:
        statement = select(AgentExecution)
        count_statement = select(func.count()).select_from(AgentExecution)

        conditions = []
        if generation_id is not None:
            conditions.append(AgentExecution.generation_id == generation_id)
        if agent_name:
            conditions.append(AgentExecution.agent_name == agent_name)
        if status:
            conditions.append(AgentExecution.status == status)
        for condition in conditions:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        statement = statement.order_by(AgentExecution.id.desc()).offset(offset).limit(limit)
        items = list(self.session.scalars(statement).all())
        total = self.session.scalar(count_statement) or 0
        return items, total


class GroundingSourceRepository(BaseRepository[GroundingSource]):
    model = GroundingSource
