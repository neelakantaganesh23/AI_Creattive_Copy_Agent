"""Image generation stage.

Runs after CTA optimisation so the prompt can use the final headline and brand
CTA. A failure here is recoverable: the workflow continues without an image and
the generation is not downgraded below `warning` for it alone -- copy is never
held back by an image that could not be produced.
"""

from __future__ import annotations

from app.agents import prompts
from app.agents.base import WorkflowContext, WorkflowRecorder
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.models.enums import AgentName
from app.services.ai.image_generation import ImageProvider
from app.services.media import MediaStorage

logger = get_logger("app.agents.image_generation")


class ImageGenerationAgent:
    """Generates one campaign visual from the finished copy and brief."""

    name = AgentName.IMAGE_GENERATION

    def __init__(self, storage: MediaStorage, provider: ImageProvider) -> None:
        self._storage = storage
        self._provider = provider

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        assert context.bundle is not None, "copy generation must run before image generation"

        if not settings.image_generation_enabled:
            recorder.skip(self.name, reason="Image generation is disabled by configuration.")
            return

        prompt = prompts.build_image_prompt(
            headline=context.bundle.email.headline,
            brand_name=context.brand.name if context.brand else None,
            product_name=context.product.name if context.product else None,
            features=context.extracted.features if context.extracted else [],
            tone=context.extracted.tone if context.extracted else None,
            brand_guidelines=context.brand.guidelines if context.brand else None,
        )
        # The full prompt, not a truncated summary: admins can see exactly what
        # was sent to the model for this run.
        recorder.start(self.name, input_summary=prompt)

        try:
            image = await self._provider.generate(prompt)
        except AppError as exc:
            logger.warning(
                "image generation unavailable; continuing without an image",
                extra={"generation_id": context.generation_id, "error_code": exc.code},
            )
            context.warnings.append("Image generation was unavailable for this generation.")
            recorder.fail(self.name, error=exc.message)
            return

        url = self._storage.save(
            image.data,
            media_type=image.media_type,
            filename_hint=f"generation-{context.generation_id}",
        )
        context.image_url = url
        context.image_prompt = prompt

        logger.info(
            "image generated",
            extra={"generation_id": context.generation_id, "media_type": image.media_type},
        )
        recorder.complete(
            self.name,
            output={"image_url": url, "prompt": prompt},
            model_name=self._provider.name,
        )
