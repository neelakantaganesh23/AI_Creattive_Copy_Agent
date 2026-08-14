"""Runs the generation workflow stages in order."""

from __future__ import annotations

import time

from app.agents.base import WorkflowContext, WorkflowRecorder
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
from app.schemas.copy_output import GenerationOutput
from app.services.ai.grounding import GroundingProvider
from app.services.ai.image_generation import ImageProvider
from app.services.media import MediaStorage

logger = get_logger("app.agents.orchestrator")


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

    async def run(
        self, context: WorkflowContext, recorder: WorkflowRecorder
    ) -> tuple[GenerationOutput, int]:
        """Execute every stage. Returns the validated output and elapsed milliseconds."""
        started = time.perf_counter()
        for agent in self._agents:
            try:
                await agent.run(context, recorder)
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
