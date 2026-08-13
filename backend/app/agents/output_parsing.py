"""Agent 6: output parsing, validation and logging."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from app.agents.base import WorkflowContext, WorkflowRecorder
from app.core.errors import AIInvalidOutputError
from app.core.logging import get_logger
from app.models.enums import AgentName, QualityStatus
from app.schemas.copy_output import GenerationOutput, check_channel_limits
from app.services.ai.provider import AIProvider

logger = get_logger("app.agents.output_parsing")


class OutputParsingAgent:
    """Validates the final structure and produces the persisted payload."""

    name = AgentName.OUTPUT_PARSING

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        assert context.bundle is not None, "copy generation must run before output parsing"
        recorder.start(self.name, input_summary="Validating structured output")

        limit_warnings = check_channel_limits(context.bundle)
        warnings = [*context.warnings, *limit_warnings]
        context.quality.warnings = warnings
        context.quality.status = QualityStatus.WARNING if warnings else QualityStatus.PASSED

        info = self._provider.info()
        try:
            output = GenerationOutput(
                channel=context.channel,
                language=context.language,
                email=context.bundle.email,
                mobile=context.bundle.mobile,
                sms=context.bundle.sms,
                quality=context.quality,
                grounded=bool(context.grounding and context.grounding.grounded),
                provider=info.name,
                models=info.as_dict(),
            )
        except PydanticValidationError as exc:
            logger.error(
                "final output failed validation",
                extra={"generation_id": context.generation_id, "errors": exc.error_count()},
            )
            recorder.fail(self.name, error="Final output failed schema validation.")
            raise AIInvalidOutputError() from exc

        recorder.complete(
            self.name,
            output={
                "quality_status": context.quality.status.value,
                "warnings": warnings,
                "repetition_score": context.quality.repetition_score,
                "grounded": output.grounded,
            },
        )
        context.warnings = warnings
        context.output = output
        logger.info(
            "generation output validated",
            extra={
                "generation_id": context.generation_id,
                "quality_status": context.quality.status.value,
                "warning_count": len(warnings),
            },
        )
