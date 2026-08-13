"""Agent 3: copy generation."""

from __future__ import annotations

from app.agents.base import WorkflowContext, WorkflowRecorder
from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import AgentName
from app.services.ai.provider import AIProvider, CopyRequest, GroundingResult

logger = get_logger("app.agents.copy_generation")


def build_copy_request(context: WorkflowContext) -> CopyRequest:
    """Assemble the provider request from the workflow context."""
    assert context.extracted is not None, "extraction must run before copy generation"
    return CopyRequest(
        brief=context.brief,
        channel=context.channel,
        language=context.language,
        extracted=context.extracted,
        grounding=context.grounding or GroundingResult(),
        audience_name=context.audience.name if context.audience else None,
        audience_description=context.audience.description if context.audience else None,
        audience_tone=context.audience.tone_guidance if context.audience else None,
        brand_name=context.brand.name if context.brand else None,
        brand_guidelines=context.brand.guidelines if context.brand else None,
        product_name=context.product.name if context.product else None,
        product_features=context.product.features if context.product else [],
        channel_limits=settings.channel_limits,
        prompt_template=context.prompt_template,
        previous_copy=context.previous_copy,
    )


class CopyGenerationAgent:
    """Produces Email, Mobile and SMS copy in one structured call."""

    name = AgentName.COPY_GENERATION

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        recorder.start(
            self.name,
            input_summary=(
                f"channel={context.channel.value} "
                f"audience={context.audience.name if context.audience else 'unspecified'} "
                f"language={context.language}"
            ),
        )
        request = build_copy_request(context)
        bundle = await self._provider.generate_copy(request)
        context.bundle = bundle
        logger.info(
            "copy generated",
            extra={
                "generation_id": context.generation_id,
                "channel": context.channel.value,
                "provider": self._provider.name,
            },
        )
        recorder.complete(
            self.name,
            output=bundle.model_dump(),
            model_name=self._provider.info().quality_model,
        )
