"""Agent 3: copy generation.

Content rules are enforced *during* the run rather than checked afterwards. The
output validator evaluates every candidate the model produces and raises
``ModelRetry`` with the specific failures, so the model rewrites until it complies
or runs out of attempts. If it runs out, the closest attempt is kept -- copy is
never discarded over a rule violation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent, ModelRetry, RunContext

from app.agents import mock_content, prompts, runtime
from app.agents.base import WorkflowContext, WorkflowRecorder
from app.agents.rules import describe_violations, evaluate_rules
from app.agents.types import CopyRequest, GroundingResult
from app.core.errors import AIInvalidOutputError
from app.core.logging import get_logger
from app.models.enums import AgentName, Channel, Severity
from app.schemas.copy_output import CopyBundle, RuleViolation

logger = get_logger("app.agents.copy_generation")


@dataclass
class RuleGate:
    """Per-run rule state, injected as the agent's dependency.

    Also remembers every candidate it rejects so the workflow has something to
    fall back on when the model exhausts its attempts.
    """

    request: CopyRequest
    attempts: list[tuple[CopyBundle, list[RuleViolation]]] = field(default_factory=list)
    # Violations on the attempt that was ultimately accepted. Only warnings can
    # appear here -- an error would have triggered another attempt.
    accepted: list[RuleViolation] = field(default_factory=list)

    @property
    def channel(self) -> Channel:
        return self.request.channel

    def record(self, bundle: CopyBundle, violations: list[RuleViolation]) -> None:
        self.attempts.append((bundle, violations))

    def best_effort(self) -> tuple[CopyBundle, list[RuleViolation]] | None:
        """The attempt with the fewest errors, then the fewest violations overall."""
        if not self.attempts:
            return None

        def rank(item: tuple[CopyBundle, list[RuleViolation]]) -> tuple[int, int]:
            _, violations = item
            errors = sum(1 for v in violations if v.severity is Severity.ERROR)
            return (errors, len(violations))

        return min(self.attempts, key=rank)


def build_copy_request(context: WorkflowContext) -> CopyRequest:
    """Assemble the model request from the workflow context."""
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
        prompt_template=context.prompt_template,
        rules=context.rules,
        previous_copy=context.previous_copy,
    )


def _enforce_rules(ctx: RunContext[RuleGate], bundle: CopyBundle) -> CopyBundle:
    """Reject copy that breaks a deterministic rule, telling the model why.

    Severity decides the response: an ``error`` sends the copy back for a rewrite,
    a ``warning`` is recorded and surfaced but accepted as-is.
    """
    gate = ctx.deps
    violations = evaluate_rules(bundle, gate.request.rules, gate.channel)
    gate.record(bundle, violations)

    errors = [v for v in violations if v.severity is Severity.ERROR]
    if errors:
        logger.info(
            "copy rejected by the rules engine; asking the model to correct it",
            extra={"errors": len(errors), "attempt": len(gate.attempts)},
        )
        raise ModelRetry(
            "The copy breaks these content rules and must be rewritten:\n"
            + describe_violations(errors)
            + "\nKeep everything else as it is."
        )

    gate.accepted = violations
    return bundle


@lru_cache
def _agent() -> Agent[RuleGate, CopyBundle]:
    agent = runtime.build_agent(
        output_type=CopyBundle,
        instructions=prompts.COPY_INSTRUCTIONS,
        name="copy_generation",
        deps_type=RuleGate,
    )
    agent.output_validator(_enforce_rules)
    return agent


@lru_cache
def _variety_agent() -> Agent[RuleGate, CopyBundle]:
    agent = runtime.build_agent(
        output_type=CopyBundle,
        instructions=prompts.VARIETY_INSTRUCTIONS,
        name="repetition_fix",
        deps_type=RuleGate,
    )
    agent.output_validator(_enforce_rules)
    return agent


async def generate(request: CopyRequest) -> tuple[CopyBundle, list[RuleViolation]]:
    """Produce copy that satisfies the rules, or the closest attempt plus its violations."""
    gate = RuleGate(request=request)
    try:
        bundle = await runtime.run_agent(
            _agent(),
            prompts.build_copy_prompt(request),
            tier="quality",
            deps=gate,
            request=request,
            mock_builder=mock_content.copy_fixture,
        )
    except AIInvalidOutputError:
        return _fall_back(gate)
    return bundle, gate.accepted


async def rewrite_for_variety(
    request: CopyRequest, bundle: CopyBundle, repeated_phrases: list[str]
) -> tuple[CopyBundle, list[RuleViolation]]:
    """Rewrite copy that overlaps earlier campaigns, keeping the CTA intact."""
    gate = RuleGate(request=request)
    try:
        rewritten = await runtime.run_agent(
            _variety_agent(),
            prompts.build_rewrite_prompt(request, bundle, repeated_phrases),
            tier="quality",
            deps=gate,
            request=(request, bundle),
            mock_builder=mock_content.variety_fixture,
        )
    except AIInvalidOutputError:
        rewritten, violations = _fall_back(gate)
    else:
        violations = gate.accepted

    # The CTA is deterministic and must survive the rewrite untouched.
    rewritten.email.cta = bundle.email.cta
    rewritten.mobile.cta = bundle.mobile.cta
    return rewritten, violations


def _fall_back(gate: RuleGate) -> tuple[CopyBundle, list[RuleViolation]]:
    """Keep the best rejected attempt rather than failing the whole generation."""
    best = gate.best_effort()
    if best is None:
        raise AIInvalidOutputError()
    bundle, violations = best
    logger.warning(
        "model could not satisfy every content rule; keeping the closest attempt",
        extra={"attempts": len(gate.attempts), "violations": len(violations)},
    )
    return bundle, violations


class CopyGenerationAgent:
    """Produces Email, Mobile and SMS copy in one structured call."""

    name = AgentName.COPY_GENERATION

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        request = build_copy_request(context)
        # The full prompt sent to the model, so an admin can see exactly what
        # was asked -- including every content rule that was in effect.
        recorder.start(
            self.name,
            input_summary=prompts.full_prompt_for_display(
                prompts.COPY_INSTRUCTIONS, prompts.build_copy_prompt(request)
            ),
        )
        bundle, violations = await generate(request)

        context.bundle = bundle
        carry_violations(context, violations)

        logger.info(
            "copy generated",
            extra={
                "generation_id": context.generation_id,
                "channel": context.channel.value,
                "unresolved_violations": len(violations),
            },
        )
        recorder.complete(
            self.name,
            output={
                **bundle.model_dump(),
                "unresolved_violations": [v.model_dump(mode="json") for v in violations],
            },
            model_name=runtime.model_name("quality"),
        )


def carry_violations(context: WorkflowContext, violations: list[RuleViolation]) -> None:
    """Record violations the model could not fix so the UI can show them."""
    for violation in violations:
        context.quality.violations.append(violation)
        context.warnings.append(violation.as_warning())
