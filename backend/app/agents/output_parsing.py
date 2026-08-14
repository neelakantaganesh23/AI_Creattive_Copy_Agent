"""Agent 7: output parsing, validation and logging."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from app.agents import runtime
from app.agents.base import WorkflowContext, WorkflowRecorder
from app.core.errors import AIInvalidOutputError
from app.core.logging import get_logger
from app.models.enums import AgentName, QualityStatus, Severity
from app.schemas.copy_output import GenerationOutput

logger = get_logger("app.agents.output_parsing")


def _quality_status(context: WorkflowContext) -> QualityStatus:
    """Warnings downgrade; nothing short of a schema failure discards the copy."""
    if not context.warnings and not context.quality.violations:
        return QualityStatus.PASSED
    return QualityStatus.WARNING


class OutputParsingAgent:
    """Validates the final structure and produces the persisted payload."""

    name = AgentName.OUTPUT_PARSING

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        assert context.bundle is not None, "copy generation must run before output parsing"
        recorder.start(self.name, input_summary="Validating structured output")

        # De-duplicate: the same violation can be reported by both the rules
        # engine and the judge.
        context.quality.warnings = list(dict.fromkeys(context.warnings))
        context.quality.status = _quality_status(context)

        info = runtime.model_info()
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

        error_count = sum(
            1 for v in context.quality.violations if v.severity is Severity.ERROR
        )
        recorder.complete(
            self.name,
            output={
                "quality_status": context.quality.status.value,
                "warnings": context.quality.warnings,
                "repetition_score": context.quality.repetition_score,
                "judge_score": context.quality.judge_score,
                "rule_errors": error_count,
                "grounded": output.grounded,
            },
        )
        context.warnings = context.quality.warnings
        context.output = output
        logger.info(
            "generation output validated",
            extra={
                "generation_id": context.generation_id,
                "quality_status": context.quality.status.value,
                "warning_count": len(context.quality.warnings),
            },
        )
