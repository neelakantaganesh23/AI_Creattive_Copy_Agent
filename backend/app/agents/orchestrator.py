"""Runs the six-stage generation workflow in order."""

from __future__ import annotations

import time

from app.agents.base import WorkflowContext, WorkflowRecorder
from app.agents.copy_generation import CopyGenerationAgent
from app.agents.cta import CTAOptimizationAgent
from app.agents.extraction import DataExtractionAgent
from app.agents.grounding import WebSearchGroundingAgent
from app.agents.output_parsing import OutputParsingAgent
from app.agents.repetition import RepetitionFixAgent
from app.core.errors import AppError, GenerationFailedError
from app.core.logging import get_logger
from app.schemas.copy_output import GenerationOutput
from app.services.ai.grounding import GroundingProvider
from app.services.ai.provider import AIProvider

logger = get_logger("app.agents.orchestrator")


class GenerationWorkflow:
    """Sequences the agents and reports progress through the recorder."""

    def __init__(self, provider: AIProvider, grounding_provider: GroundingProvider) -> None:
        self._provider = provider
        self._agents = (
            DataExtractionAgent(provider),
            WebSearchGroundingAgent(grounding_provider),
            CopyGenerationAgent(provider),
            RepetitionFixAgent(provider),
            CTAOptimizationAgent(),
            OutputParsingAgent(provider),
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
                "provider": self._provider.name,
                "grounded": context.output.grounded,
            },
        )
        return context.output, duration_ms
