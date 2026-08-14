"""Agent 6: LLM-as-Judge content validation.

Deterministic rules were already enforced by the rules engine during copy
generation. This stage covers what code cannot check -- naturalness, brand voice,
and the natural-language guidelines an admin has configured.

A failed verdict triggers a bounded revision: the copy is rewritten from the
judge's findings and re-judged, up to ``JUDGE_MAX_REVISIONS`` times. If it still
fails, the generation completes with a ``warning`` quality status and the
surviving violations attached. Copy is never discarded.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_ai import Agent

from app.agents import mock_content, prompts, runtime
from app.agents.base import WorkflowContext, WorkflowRecorder
from app.agents.copy_generation import build_copy_request
from app.agents.rules import evaluate_rules
from app.agents.types import CopyRequest
from app.core.config import settings
from app.core.errors import AIProviderError
from app.core.logging import get_logger
from app.models.enums import AgentName, Severity
from app.schemas.copy_output import CopyBundle, JudgeVerdict, RuleViolation

logger = get_logger("app.agents.validation")


@lru_cache
def _judge_agent() -> Agent[None, JudgeVerdict]:
    return runtime.build_agent(
        output_type=JudgeVerdict,
        instructions=prompts.JUDGE_INSTRUCTIONS,
        name="content_validation",
        temperature=settings.judge_temperature,
    )


@lru_cache
def _revision_agent() -> Agent[None, CopyBundle]:
    return runtime.build_agent(
        output_type=CopyBundle,
        instructions=prompts.REVISION_INSTRUCTIONS,
        name="content_revision",
    )


async def judge(request: CopyRequest, bundle: CopyBundle) -> JudgeVerdict:
    return await runtime.run_agent(
        _judge_agent(),
        prompts.build_judge_prompt(request, bundle),
        tier="quality",
        request=(request, bundle),
        mock_builder=mock_content.judge_fixture,
    )


async def revise(
    request: CopyRequest, bundle: CopyBundle, violations: list[RuleViolation]
) -> CopyBundle:
    revised = await runtime.run_agent(
        _revision_agent(),
        prompts.build_revision_prompt(request, bundle, violations),
        tier="quality",
        request=(request, bundle, violations),
        mock_builder=mock_content.revision_fixture,
    )
    # The CTA belongs to the deterministic CTA agent, not the editor.
    revised.email.cta = bundle.email.cta
    revised.mobile.cta = bundle.mobile.cta
    return revised


def _has_errors(verdict: JudgeVerdict) -> bool:
    return any(v.severity is Severity.ERROR for v in verdict.violations)


def _rejected(verdict: JudgeVerdict) -> bool:
    """Whether the verdict warrants a rewrite."""
    return not verdict.passed or _has_errors(verdict) or verdict.score < settings.judge_min_score


class ContentValidationAgent:
    """Judges the finished copy against the configured guidelines."""

    name = AgentName.CONTENT_VALIDATION

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        assert context.bundle is not None, "copy generation must run before validation"

        if not settings.judge_enabled:
            recorder.skip(self.name, reason="Content validation is disabled by configuration.")
            return

        request = build_copy_request(context)
        # The full prompt sent to the judge for the first pass. If the copy is
        # revised, later passes judge different copy against the same
        # instructions and guidelines, so this remains representative.
        recorder.start(
            self.name,
            input_summary=prompts.full_prompt_for_display(
                prompts.JUDGE_INSTRUCTIONS, prompts.build_judge_prompt(request, context.bundle)
            ),
        )

        try:
            verdict = await self._judge_with_revisions(context, request)
        except AIProviderError as exc:
            # A judge failure must not cost the user their copy.
            logger.warning(
                "content validation unavailable; keeping the copy unjudged",
                extra={"generation_id": context.generation_id},
            )
            context.warnings.append("Content validation was unavailable for this generation.")
            recorder.fail(self.name, error=exc.message)
            return

        context.judge = verdict
        context.quality.judge_score = round(verdict.score, 4)
        context.quality.naturalness = round(verdict.naturalness, 4)
        for violation in verdict.violations:
            context.quality.violations.append(violation)
            context.warnings.append(violation.as_warning())

        logger.info(
            "content validated",
            extra={
                "generation_id": context.generation_id,
                "judge_score": context.quality.judge_score,
                "revisions": context.quality.revisions,
                "violations": len(verdict.violations),
            },
        )
        recorder.complete(
            self.name,
            output={
                "passed": verdict.passed and not verdict.violations,
                "score": context.quality.judge_score,
                "naturalness": context.quality.naturalness,
                "revisions": context.quality.revisions,
                "violations": [v.model_dump(mode="json") for v in verdict.violations],
                "reasoning": verdict.reasoning,
            },
            model_name=runtime.model_name("quality"),
        )

    async def _judge_with_revisions(
        self, context: WorkflowContext, request: CopyRequest
    ) -> JudgeVerdict:
        """Judge, revise, re-judge -- up to the configured cap."""
        assert context.bundle is not None
        verdict = await judge(request, context.bundle)

        for attempt in range(settings.judge_max_revisions):
            if not _rejected(verdict):
                break
            logger.info(
                "judge rejected the copy; revising",
                extra={
                    "generation_id": context.generation_id,
                    "attempt": attempt + 1,
                    "score": round(verdict.score, 4),
                },
            )
            revised = await revise(request, context.bundle, verdict.violations)

            # A revision must not reintroduce a deterministic rule breach.
            breaches = evaluate_rules(revised, request.rules, request.channel)
            if breaches:
                logger.warning(
                    "discarding a revision that broke the content rules",
                    extra={"generation_id": context.generation_id, "breaches": len(breaches)},
                )
                break

            context.bundle = revised
            context.quality.revisions = attempt + 1
            verdict = await judge(request, revised)

        return verdict
