"""Agent 4: repetition detection and repair."""

from __future__ import annotations

from app.agents import runtime
from app.agents.base import WorkflowContext, WorkflowRecorder
from app.agents.copy_generation import build_copy_request, carry_violations, rewrite_for_variety
from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import AgentName
from app.schemas.copy_output import CopyBundle
from app.utils.text import shared_phrases, similarity

logger = get_logger("app.agents.repetition")


def analyse_repetition(bundle: CopyBundle, previous_copy: list[str]) -> tuple[float, list[str]]:
    """Return the highest similarity against recent copy and the repeated phrases."""
    if not previous_copy:
        return 0.0, []

    highest = 0.0
    phrases: list[str] = []
    for field in bundle.text_fields():
        for previous in previous_copy:
            score = similarity(field, previous)
            highest = max(highest, score)
            for phrase in shared_phrases(field, previous):
                if phrase not in phrases:
                    phrases.append(phrase)
    return highest, phrases


class RepetitionFixAgent:
    """Rewrites copy only when similarity exceeds the configured threshold.

    The CTA is never rewritten here: it is owned by the deterministic CTA agent.
    """

    name = AgentName.REPETITION_FIX

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        assert context.bundle is not None, "copy generation must run before repetition fix"
        recorder.start(
            self.name,
            input_summary=f"comparing against {len(context.previous_copy)} recent fields",
        )

        score, phrases = analyse_repetition(context.bundle, context.previous_copy)
        threshold = settings.repetition_similarity_threshold
        context.quality.repetition_score = round(score, 4)

        if score < threshold:
            recorder.complete(
                self.name,
                output={
                    "repetition_score": round(score, 4),
                    "threshold": threshold,
                    "rewritten": False,
                    "repeated_phrases": phrases[:5],
                },
            )
            return

        logger.info(
            "repetition threshold exceeded; rewriting copy",
            extra={
                "generation_id": context.generation_id,
                "repetition_score": round(score, 4),
                "threshold": threshold,
            },
        )
        request = build_copy_request(context)
        rewritten, violations = await rewrite_for_variety(request, context.bundle, phrases)
        new_score, _ = analyse_repetition(rewritten, context.previous_copy)

        context.bundle = rewritten
        context.quality.repetition_fixed = True
        context.quality.repetition_score = round(new_score, 4)
        carry_violations(context, violations)
        if new_score >= threshold:
            context.warnings.append(
                "Generated copy still resembles a recent generation after one rewrite."
            )

        recorder.complete(
            self.name,
            output={
                "repetition_score": round(new_score, 4),
                "previous_score": round(score, 4),
                "threshold": threshold,
                "rewritten": True,
                "repeated_phrases": phrases[:5],
            },
            model_name=runtime.model_name("quality"),
        )
