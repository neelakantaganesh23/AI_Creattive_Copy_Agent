"""Generation orchestration: persistence, workflow execution and status reporting."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agents.base import (
    AudienceData,
    BrandData,
    CTARuleData,
    ProductData,
    WorkflowContext,
)
from app.agents.orchestrator import GenerationWorkflow
from app.core.config import settings
from app.core.errors import (
    AppError,
    ErrorCode,
    GenerationFailedError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.logging import get_logger
from app.database.session import session_scope
from app.models.enums import (
    AGENT_METADATA,
    AGENT_SEQUENCE,
    AgentName,
    AgentStatus,
    Channel,
    GenerationStatus,
    Role,
)
from app.models.generation import Generation
from app.models.user import User
from app.repositories.generation_repository import (
    AgentExecutionRepository,
    GenerationRepository,
    GroundingSourceRepository,
)
from app.repositories.taxonomy_repository import (
    AudienceSegmentRepository,
    BrandRepository,
    CTARuleRepository,
    ProductRepository,
    TemplateRepository,
)
from app.schemas.copy_output import GenerationOutput
from app.schemas.generation import (
    AgentExecutionResponse,
    GenerationCreate,
    GenerationDetail,
    GenerationStatusResponse,
    GenerationSummary,
    GroundingSourceResponse,
)
from app.services.ai.factory import get_ai_provider, get_grounding_provider
from app.utils.text import slugify_title

logger = get_logger("app.generation")

# Roles allowed to read every user's generations; marketers see only their own.
_READ_ALL_ROLES = frozenset({Role.ADMIN, Role.VIEWER})


class DatabaseRecorder:
    """Persists agent progress so ``GET /generations/{id}/status`` can report it."""

    def __init__(self, session: Session, generation_id: int) -> None:
        self._session = session
        self._repo = AgentExecutionRepository(session)
        self._generation_id = generation_id

    def _row(self, agent: AgentName):
        row = self._repo.get_for_agent(self._generation_id, agent)
        if row is None:  # pragma: no cover - rows are created up front
            raise NotFoundError(f"Agent execution row missing for {agent.value}.")
        return row

    def start(self, agent: AgentName, *, input_summary: str | None = None) -> None:
        row = self._row(agent)
        row.status = AgentStatus.IN_PROGRESS
        row.started_at = datetime.now(UTC)
        row.input_summary = input_summary
        self._session.commit()

    def complete(
        self,
        agent: AgentName,
        *,
        output: dict[str, Any] | None = None,
        model_name: str | None = None,
    ) -> None:
        row = self._row(agent)
        completed_at = datetime.now(UTC)
        row.status = AgentStatus.COMPLETED
        row.completed_at = completed_at
        row.output_json = output
        row.model_name = model_name
        row.duration_ms = _duration_ms(row.started_at, completed_at)
        self._session.commit()

    def fail(self, agent: AgentName, *, error: str) -> None:
        row = self._row(agent)
        completed_at = datetime.now(UTC)
        row.status = AgentStatus.FAILED
        row.completed_at = completed_at
        row.error_message = error
        row.duration_ms = _duration_ms(row.started_at, completed_at)
        self._session.commit()

    def skip(self, agent: AgentName, *, reason: str) -> None:
        row = self._row(agent)
        row.status = AgentStatus.SKIPPED
        row.completed_at = datetime.now(UTC)
        row.input_summary = reason
        row.duration_ms = 0
        self._session.commit()


class GenerationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.generations = GenerationRepository(session)
        self.agent_executions = AgentExecutionRepository(session)
        self.grounding_sources = GroundingSourceRepository(session)
        self.brands = BrandRepository(session)
        self.products = ProductRepository(session)
        self.segments = AudienceSegmentRepository(session)
        self.cta_rules = CTARuleRepository(session)
        self.templates = TemplateRepository(session)

    # -- Creation ------------------------------------------------------------
    def create(self, payload: GenerationCreate, user: User) -> Generation:
        """Persist a queued generation together with its six pending stages."""
        brand = self._require_brand(payload.brand_id)
        product = self._require_product(payload.product_id, brand_id=payload.brand_id)
        segment = self._require_segment(payload.audience_segment_id)

        generation = self.generations.create(
            user_id=user.id,
            title=payload.title or slugify_title(payload.brief),
            brief=payload.brief,
            brand_id=brand.id if brand else None,
            product_id=product.id if product else None,
            audience_segment_id=segment.id if segment else None,
            channel=payload.channel.value,
            language=payload.language,
            status=GenerationStatus.PENDING,
            grounded=False,
            provider=get_ai_provider().name,
        )
        for index, agent in enumerate(AGENT_SEQUENCE, start=1):
            self.agent_executions.create(
                generation_id=generation.id,
                agent_name=agent.value,
                sequence=index,
                status=AgentStatus.PENDING,
            )
        self.session.commit()
        logger.info(
            "generation queued",
            extra={
                "generation_id": generation.id,
                "user_id": user.id,
                "channel": generation.channel,
            },
        )
        return generation

    def regenerate(self, generation_id: int, user: User) -> Generation:
        """Create a fresh generation from an existing one's inputs."""
        source = self.get_for_user(generation_id, user)
        payload = GenerationCreate(
            brief=source.brief,
            channel=Channel(source.channel),
            brand_id=source.brand_id,
            product_id=source.product_id,
            audience_segment_id=source.audience_segment_id,
            language=source.language,
            title=source.title,
        )
        return self.create(payload, user)

    # -- Execution -----------------------------------------------------------
    async def run_workflow(self, generation_id: int) -> None:
        """Execute the workflow on its own session (runs as a background task)."""
        context = self._load_context(generation_id)

        with session_scope() as session:
            recorder = DatabaseRecorder(session, generation_id)
            repo = GenerationRepository(session)
            generation = repo.get(generation_id)
            if generation is None:  # pragma: no cover - defensive
                return
            generation.status = GenerationStatus.RUNNING
            session.commit()

            workflow = GenerationWorkflow(get_ai_provider(), get_grounding_provider())
            try:
                output, duration_ms = await asyncio.wait_for(
                    workflow.run(context, recorder),
                    timeout=settings.generation_timeout_seconds,
                )
            except TimeoutError:
                self._mark_failed(
                    session,
                    generation_id,
                    code=ErrorCode.AI_PROVIDER_TIMEOUT,
                    message="The generation timed out. Please try again.",
                )
                return
            except AppError as exc:
                self._mark_failed(session, generation_id, code=exc.code, message=exc.message)
                return
            except Exception:
                logger.exception("generation crashed", extra={"generation_id": generation_id})
                self._mark_failed(
                    session,
                    generation_id,
                    code=ErrorCode.GENERATION_FAILED,
                    message=GenerationFailedError.message,
                )
                return

            self._persist_success(session, generation_id, context, output, duration_ms)

    def _persist_success(
        self,
        session: Session,
        generation_id: int,
        context: WorkflowContext,
        output: GenerationOutput,
        duration_ms: int,
    ) -> None:
        repo = GenerationRepository(session)
        sources_repo = GroundingSourceRepository(session)
        generation = repo.get(generation_id)
        if generation is None:  # pragma: no cover - defensive
            return

        generation.output_json = output.model_dump(mode="json")
        generation.grounded = output.grounded
        generation.execution_time_ms = duration_ms
        # A stage that failed but was recovered from (grounding, typically) leaves
        # the run usable but incomplete.
        stage_failed = any(
            row.status == AgentStatus.FAILED
            for row in AgentExecutionRepository(session).list_for_generation(generation_id)
        )
        generation.status = (
            GenerationStatus.PARTIAL if stage_failed else GenerationStatus.COMPLETED
        )
        generation.error_code = None
        generation.error_message = None

        if context.grounding:
            for source in context.grounding.sources:
                sources_repo.create(
                    generation_id=generation_id,
                    title=source.title[:300],
                    url=source.url[:1000],
                    source_type=source.source_type,
                    snippet=source.snippet,
                    retrieved_at=datetime.now(UTC),
                )
        session.commit()
        logger.info(
            "generation completed",
            extra={
                "generation_id": generation_id,
                "duration_ms": duration_ms,
                "status": generation.status,
                "grounded": generation.grounded,
            },
        )

    @staticmethod
    def _mark_failed(session: Session, generation_id: int, *, code: str, message: str) -> None:
        repo = GenerationRepository(session)
        generation = repo.get(generation_id)
        if generation is None:  # pragma: no cover - defensive
            return
        generation.status = GenerationStatus.FAILED
        generation.error_code = code
        generation.error_message = message
        session.commit()
        logger.error(
            "generation failed",
            extra={"generation_id": generation_id, "error_code": code},
        )

    def _load_context(self, generation_id: int) -> WorkflowContext:
        """Build a detached workflow context from the stored generation.

        Everything is copied into plain dataclasses so the workflow never holds an
        ORM object across the background task's lifetime.
        """
        with session_scope() as session:
            return self._build_context(session, generation_id)

    def _build_context(self, session: Session, generation_id: int) -> WorkflowContext:
        repo = GenerationRepository(session)
        generation = repo.get_with_relations(generation_id)
        if generation is None:
            raise NotFoundError("Generation not found.")

        brand = (
            BrandData(
                id=generation.brand.id,
                name=generation.brand.name,
                guidelines=generation.brand.guidelines,
            )
            if generation.brand
            else None
        )
        product = (
            ProductData(
                id=generation.product.id,
                name=generation.product.name,
                features=generation.product.feature_list,
                sku=generation.product.sku,
            )
            if generation.product
            else None
        )
        audience = (
            AudienceData(
                id=generation.audience_segment.id,
                name=generation.audience_segment.name,
                description=generation.audience_segment.description,
                tone_guidance=generation.audience_segment.tone_guidance,
            )
            if generation.audience_segment
            else None
        )

        rules = [
            CTARuleData(
                id=rule.id,
                template=rule.template,
                priority=rule.priority,
                brand_id=rule.brand_id,
                product_id=rule.product_id,
                channel=rule.channel,
            )
            for rule in CTARuleRepository(session).list_active()
        ]
        template = TemplateRepository(session).get_active_for_channel(generation.channel)
        previous_copy = self._recent_copy_texts(
            session,
            brand_id=generation.brand_id,
            product_id=generation.product_id,
            exclude_generation_id=generation.id,
        )

        return WorkflowContext(
            generation_id=generation.id,
            brief=generation.brief,
            channel=Channel(generation.channel),
            language=generation.language,
            brand=brand,
            product=product,
            audience=audience,
            cta_rules=rules,
            prompt_template=template.prompt_template if template else None,
            previous_copy=previous_copy,
        )

    @staticmethod
    def _recent_copy_texts(
        session: Session,
        *,
        brand_id: int | None,
        product_id: int | None,
        exclude_generation_id: int | None,
    ) -> list[str]:
        outputs = GenerationRepository(session).recent_outputs_for_repetition(
            limit=settings.repetition_history_size,
            brand_id=brand_id,
            product_id=product_id,
            exclude_generation_id=exclude_generation_id,
        )
        texts: list[str] = []
        for payload in outputs:
            try:
                output = GenerationOutput.model_validate(payload)
            except Exception:
                logger.warning("skipping unparsable historical output for repetition analysis")
                continue
            texts.extend(output.bundle.text_fields())
        return texts

    # -- Reads ---------------------------------------------------------------
    def get_for_user(self, generation_id: int, user: User) -> Generation:
        generation = self.generations.get_with_relations(generation_id)
        if generation is None:
            raise NotFoundError("Generation not found.")
        if generation.user_id != user.id and Role(user.role) not in _READ_ALL_ROLES:
            raise PermissionDeniedError("You do not have access to this generation.")
        return generation

    def list_for_user(
        self,
        user: User,
        *,
        offset: int,
        limit: int,
        channel: str | None = None,
        status: str | None = None,
        audience_segment_id: int | None = None,
        brand_id: int | None = None,
        search: str | None = None,
    ) -> tuple[list[Generation], int]:
        scope_user_id = None if Role(user.role) in _READ_ALL_ROLES else user.id
        return self.generations.list_generations(
            offset=offset,
            limit=limit,
            user_id=scope_user_id,
            channel=channel,
            status=status,
            audience_segment_id=audience_segment_id,
            brand_id=brand_id,
            search=search,
        )

    def delete(self, generation_id: int, user: User) -> None:
        generation = self.generations.get(generation_id)
        if generation is None:
            raise NotFoundError("Generation not found.")
        if generation.user_id != user.id and Role(user.role) is not Role.ADMIN:
            raise PermissionDeniedError("You can only delete your own generations.")
        self.generations.delete(generation)
        self.session.commit()
        logger.info("generation deleted", extra={"generation_id": generation_id})

    def status(self, generation_id: int, user: User) -> GenerationStatusResponse:
        generation = self.get_for_user(generation_id, user)
        steps = [
            to_agent_response(row)
            for row in self.agent_executions.list_for_generation(generation_id)
        ]
        finished = sum(
            1
            for step in steps
            if step.status in (AgentStatus.COMPLETED, AgentStatus.SKIPPED, AgentStatus.FAILED)
        )
        progress = finished / len(steps) if steps else 0.0
        return GenerationStatusResponse(
            id=generation.id,
            status=GenerationStatus(generation.status),
            progress=round(progress, 4),
            execution_time_ms=generation.execution_time_ms,
            error_code=generation.error_code,
            error_message=generation.error_message,
            steps=steps,
            output=_parse_output(generation.output_json),
        )

    # -- Validation helpers --------------------------------------------------
    def _require_brand(self, brand_id: int | None):
        if brand_id is None:
            return None
        brand = self.brands.get(brand_id)
        if brand is None:
            raise NotFoundError("The selected brand does not exist.")
        if not brand.is_active:
            raise ValidationError("The selected brand is inactive.")
        return brand

    def _require_product(self, product_id: int | None, *, brand_id: int | None):
        if product_id is None:
            return None
        product = self.products.get(product_id)
        if product is None:
            raise NotFoundError("The selected product does not exist.")
        if not product.is_active:
            raise ValidationError("The selected product is inactive.")
        if brand_id is not None and product.brand_id != brand_id:
            raise ValidationError("The selected product does not belong to the selected brand.")
        return product

    def _require_segment(self, segment_id: int | None):
        if segment_id is None:
            return None
        segment = self.segments.get(segment_id)
        if segment is None:
            raise ValidationError(
                "The selected audience segment does not exist.",
                code=ErrorCode.INVALID_AUDIENCE_SEGMENT,
            )
        if not segment.is_active:
            raise ValidationError(
                "The selected audience segment is inactive.",
                code=ErrorCode.INVALID_AUDIENCE_SEGMENT,
            )
        return segment


def _duration_ms(started_at: datetime | None, completed_at: datetime) -> int:
    if started_at is None:
        return 0
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    return max(int((completed_at - started_at).total_seconds() * 1000), 0)


def _parse_output(payload: dict[str, Any] | None) -> GenerationOutput | None:
    if not payload:
        return None
    try:
        return GenerationOutput.model_validate(payload)
    except Exception:
        logger.warning("stored generation output could not be parsed")
        return None


def to_agent_response(row) -> AgentExecutionResponse:
    metadata = AGENT_METADATA.get(AgentName(row.agent_name), {})
    return AgentExecutionResponse(
        id=row.id,
        generation_id=row.generation_id,
        agent_name=row.agent_name,
        title=metadata.get("title", row.agent_name),
        description=metadata.get("description", ""),
        sequence=row.sequence,
        status=AgentStatus(row.status),
        input_summary=row.input_summary,
        output_json=row.output_json,
        error_message=row.error_message,
        model_name=row.model_name,
        duration_ms=row.duration_ms,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


def to_summary(generation: Generation) -> GenerationSummary:
    return GenerationSummary(
        id=generation.id,
        title=generation.title,
        brief=generation.brief,
        channel=Channel(generation.channel),
        language=generation.language,
        status=GenerationStatus(generation.status),
        grounded=generation.grounded,
        execution_time_ms=generation.execution_time_ms,
        brand_name=generation.brand.name if generation.brand else None,
        product_name=generation.product.name if generation.product else None,
        audience_segment_name=(
            generation.audience_segment.name if generation.audience_segment else None
        ),
        created_at=generation.created_at,
        updated_at=generation.updated_at,
    )


def to_detail(generation: Generation) -> GenerationDetail:
    summary = to_summary(generation)
    return GenerationDetail(
        **summary.model_dump(),
        user_id=generation.user_id,
        brand_id=generation.brand_id,
        product_id=generation.product_id,
        audience_segment_id=generation.audience_segment_id,
        output=_parse_output(generation.output_json),
        provider=generation.provider,
        error_code=generation.error_code,
        error_message=generation.error_message,
        agent_executions=[to_agent_response(row) for row in generation.agent_executions],
        grounding_sources=[
            GroundingSourceResponse.model_validate(source)
            for source in generation.grounding_sources
        ],
    )
