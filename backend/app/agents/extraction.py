"""Agent 1: data extraction."""

from __future__ import annotations

from app.agents.base import WorkflowContext, WorkflowRecorder
from app.core.logging import get_logger
from app.models.enums import AgentName
from app.services.ai.provider import AIProvider
from app.utils.text import truncate

logger = get_logger("app.agents.extraction")


class DataExtractionAgent:
    """Pulls brand, products, SKUs, features, tone and goal out of the raw brief."""

    name = AgentName.DATA_EXTRACTION

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        recorder.start(self.name, input_summary=truncate(context.brief, 240))
        extracted = await self._provider.extract_brief(
            context.brief, language=context.language
        )

        # Selections made in the UI are authoritative over anything inferred.
        if context.brand and not extracted.brand:
            extracted.brand = context.brand.name
        if context.product and context.product.name not in extracted.products:
            extracted.products.insert(0, context.product.name)
        if context.product and context.product.features:
            for feature in context.product.features:
                if feature not in extracted.features:
                    extracted.features.append(feature)
        if context.product and context.product.sku and context.product.sku not in extracted.skus:
            extracted.skus.append(context.product.sku)

        context.extracted = extracted
        logger.info(
            "brief extracted",
            extra={
                "generation_id": context.generation_id,
                "products": len(extracted.products),
                "features": len(extracted.features),
            },
        )
        recorder.complete(
            self.name,
            output=extracted.to_dict(),
            model_name=self._provider.info().fast_model,
        )
