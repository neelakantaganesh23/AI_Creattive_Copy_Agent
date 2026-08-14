"""Agent 2: web search grounding."""

from __future__ import annotations

from app.agents.base import WorkflowContext, WorkflowRecorder
from app.agents.types import GroundingResult
from app.core.config import settings
from app.core.errors import GroundingError
from app.core.logging import get_logger
from app.models.enums import AgentName
from app.services.ai.grounding import GroundingProvider

logger = get_logger("app.agents.grounding")


class WebSearchGroundingAgent:
    """Searches only for entities the extraction step identified.

    A grounding failure is recoverable: the workflow continues from the brief
    alone and the generation is marked as not externally grounded.
    """

    name = AgentName.WEB_SEARCH_GROUNDING

    def __init__(self, provider: GroundingProvider) -> None:
        self._provider = provider

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        if not settings.grounding_enabled:
            context.grounding = GroundingResult(
                grounded=False,
                notes=["Grounding is disabled; copy is based on the supplied brief only."],
            )
            recorder.skip(self.name, reason="Grounding is disabled by configuration.")
            return

        recorder.start(self.name, input_summary="Searching for extracted entities")
        assert context.extracted is not None, "extraction must run before grounding"

        try:
            result = await self._provider.search(context.extracted, brief=context.brief)
        except GroundingError as exc:
            logger.warning(
                "grounding failed; continuing without external context",
                extra={"generation_id": context.generation_id},
            )
            context.grounding = GroundingResult(
                grounded=False, notes=["Grounding failed; the copy is not externally grounded."]
            )
            context.warnings.append("Web search grounding was unavailable for this generation.")
            recorder.fail(self.name, error=str(exc))
            return

        context.grounding = result
        recorder.complete(
            self.name,
            output={
                "grounded": result.grounded,
                "source_count": len(result.sources),
                "sources": [
                    {"title": source.title, "url": source.url} for source in result.sources
                ],
                "notes": result.notes,
            },
        )
