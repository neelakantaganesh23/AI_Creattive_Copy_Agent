"""Runs the generation workflow stages in order."""

from __future__ import annotations

import time

from app.agents.base import Agent, WorkflowContext, WorkflowRecorder
from app.agents.copy_generation import CopyGenerationAgent
from app.agents.cta import CTAOptimizationAgent
from app.agents.extraction import DataExtractionAgent
from app.agents.grounding import WebSearchGroundingAgent
from app.agents.image_generation import ImageGenerationAgent
from app.agents.output_parsing import OutputParsingAgent
from app.agents.repetition import RepetitionFixAgent
from app.agents.runtime import model_info
from app.agents.validation import ContentValidationAgent
from app.core.errors import AppError, GenerationFailedError
from app.core.logging import get_logger
from app.observability import annotate_current_span, annotate_current_trace, traced
from app.schemas.copy_output import GenerationOutput
from app.services.ai.grounding import GroundingProvider
from app.services.ai.image_generation import ImageProvider
from app.services.media import MediaStorage

logger = get_logger("app.agents.orchestrator")


@traced(name="stage", ignore_arguments=["agent", "context", "recorder"], capture_output=False)
async def _run_stage(agent: Agent, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
    """Run one stage inside its own span, renamed to the agent.

    A thin wrapper so all eight stages become named child spans without touching
    each agent module. A no-op passthrough when tracing is inactive.
    """
    annotate_current_span(name=agent.name.value)
    await agent.run(context, recorder)


class GenerationWorkflow:
    """Sequences the agents and reports progress through the recorder.

    The order matches ``AGENT_SEQUENCE``; content validation deliberately runs
    after CTA optimisation so the deterministic CTA is judged too.
    """

    def __init__(
        self,
        grounding_provider: GroundingProvider,
        media_storage: MediaStorage,
        image_provider: ImageProvider,
    ) -> None:
        self._agents = (
            DataExtractionAgent(),
            WebSearchGroundingAgent(grounding_provider),
            CopyGenerationAgent(),
            RepetitionFixAgent(),
            CTAOptimizationAgent(),
            ImageGenerationAgent(media_storage, image_provider),
            ContentValidationAgent(),
            OutputParsingAgent(),
        )

    @traced(
        name="generation",
        ignore_arguments=["self", "context", "recorder"],
        capture_output=False,
    )
    async def run(
        self, context: WorkflowContext, recorder: WorkflowRecorder
    ) -> tuple[GenerationOutput, int]:
        """Execute every stage. Returns the validated output and elapsed milliseconds.

        When Opik tracing is active this method is the trace root -- one trace per
        generation -- with a child span per stage and per model call.
        """
        annotate_current_trace(
            metadata={
                "generation_id": context.generation_id,
                "channel": str(context.channel),
                "language": context.language,
                "provider": model_info().name,
            }
        )
        started = time.perf_counter()
        for agent in self._agents:
            try:
                await _run_stage(agent, context, recorder)
            except AppError as exc:
                recorder.fail(agent.name, error=exc.message)
                logger.error(
                    "workflow stage failed",
                    extra={
                        "generation_id": context.generation_id,
                        "agent": agent.name.value,
                        "error_code": exc.code,
                    },
                )
                raise
            except Exception as exc:
                recorder.fail(agent.name, error="An unexpected error occurred in this stage.")
                logger.exception(
                    "workflow stage crashed",
                    extra={
                        "generation_id": context.generation_id,
                        "agent": agent.name.value,
                    },
                )
                raise GenerationFailedError() from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        if context.output is None:  # pragma: no cover - guarded by the parsing agent
            raise GenerationFailedError()

        logger.info(
            "workflow completed",
            extra={
                "generation_id": context.generation_id,
                "duration_ms": duration_ms,
                "provider": model_info().name,
                "grounded": context.output.grounded,
            },
        )
        return context.output, duration_ms
