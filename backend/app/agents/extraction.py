"""Agent 1: data extraction."""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents import mock_content, prompts, runtime
from app.agents.base import WorkflowContext, WorkflowRecorder
from app.agents.types import ExtractedBrief
from app.core.logging import get_logger
from app.models.enums import AgentName

logger = get_logger("app.agents.extraction")


class ExtractionOutput(BaseModel):
    """Structured facts pulled from the raw brief."""

    brand: str | None = Field(default=None, description="Brand named in the brief, if any.")
    products: list[str] = Field(default_factory=list)
    skus: list[str] = Field(default_factory=list)
    athletes: list[str] = Field(
        default_factory=list,
        description="People the brief explicitly names as athlete, ambassador or endorser.",
    )
    campaign_goal: str | None = None
    features: list[str] = Field(default_factory=list)
    tone: str | None = None
    key_message: str | None = None

    def to_brief(self) -> ExtractedBrief:
        return ExtractedBrief(**self.model_dump())


@lru_cache
def _agent() -> Agent[None, ExtractionOutput]:
    return runtime.build_agent(
        output_type=ExtractionOutput,
        instructions=prompts.EXTRACTION_INSTRUCTIONS,
        name="data_extraction",
        # Extraction is a reading task; sampling variety only invites invention.
        temperature=0.0,
    )


class DataExtractionAgent:
    """Pulls brand, products, SKUs, features, tone and goal out of the raw brief."""

    name = AgentName.DATA_EXTRACTION

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        prompt = prompts.build_extraction_prompt(context.brief, context.language)
        # The full prompt sent to the model, so an admin can see exactly what
        # was asked -- not the truncated summary this used to be.
        recorder.start(
            self.name,
            input_summary=prompts.full_prompt_for_display(
                prompts.EXTRACTION_INSTRUCTIONS, prompt
            ),
        )

        output = await runtime.run_agent(
            _agent(),
            prompt,
            tier="fast",
            request=(context.brief, context.language),
            mock_builder=mock_content.extraction_fixture,
        )
        extracted = output.to_brief()

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
            model_name=runtime.model_name("fast"),
        )
