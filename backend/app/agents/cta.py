"""Agent 5: deterministic CTA optimisation.

No model is involved. CTA rules live in the database; the most specific active rule
whose placeholders can all be resolved wins, with ``priority`` breaking ties.
"""

from __future__ import annotations

import re

from app.agents.base import CTARuleData, WorkflowContext, WorkflowRecorder
from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import AgentName
from app.utils.text import truncate

logger = get_logger("app.agents.cta")

DEFAULT_CTA = "SHOP THE COLLECTION"
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def render_template(template: str, values: dict[str, str | None]) -> str | None:
    """Render ``{placeholder}`` tokens, or return ``None`` if any value is missing."""
    resolved = template
    for match in _PLACEHOLDER_RE.finditer(template):
        key = match.group(1).lower()
        value = values.get(key)
        if not value:
            return None
        resolved = resolved.replace(match.group(0), value)
    return " ".join(resolved.split()).upper()


def _specificity(rule: CTARuleData) -> tuple[int, int, int]:
    """Sort key: priority, then how many dimensions the rule pins down."""
    matched = sum(
        1 for value in (rule.product_id, rule.brand_id, rule.channel) if value is not None
    )
    return (rule.priority, matched, rule.id)


def resolve_cta(context: WorkflowContext) -> tuple[str, int | None]:
    """Return the winning CTA text and the id of the rule that produced it."""
    values = {
        "product": context.product.name if context.product else None,
        "brand": context.brand.name if context.brand else None,
        "channel": context.channel.label,
        "audience": context.audience.name if context.audience else None,
    }

    applicable = [
        rule
        for rule in context.cta_rules
        if (rule.brand_id is None or rule.brand_id == (context.brand.id if context.brand else None))
        and (
            rule.product_id is None
            or rule.product_id == (context.product.id if context.product else None)
        )
        and (rule.channel is None or rule.channel == context.channel.value)
    ]

    for rule in sorted(applicable, key=_specificity, reverse=True):
        rendered = render_template(rule.template, values)
        if rendered:
            return rendered, rule.id

    # Fallbacks mirror the seeded rules so behaviour is identical with an empty table.
    if values["product"]:
        return f"SHOP {values['product'].upper()}", None
    if values["brand"]:
        return f"EXPLORE {values['brand'].upper()}", None
    return DEFAULT_CTA, None


class CTAOptimizationAgent:
    """Overrides the model's provisional CTA with the deterministic brand rule."""

    name = AgentName.CTA_OPTIMIZATION

    async def run(self, context: WorkflowContext, recorder: WorkflowRecorder) -> None:
        assert context.bundle is not None, "copy generation must run before CTA optimisation"
        recorder.start(self.name, input_summary=f"{len(context.cta_rules)} active rules")

        cta, rule_id = resolve_cta(context)
        limits = settings.channel_limits
        context.bundle.email.cta = truncate(cta, limits["email"]["cta"])
        context.bundle.mobile.cta = truncate(cta, limits["mobile"]["cta"])
        context.applied_cta_rule_id = rule_id

        logger.info(
            "cta applied",
            extra={"generation_id": context.generation_id, "cta_rule_id": rule_id},
        )
        recorder.complete(
            self.name,
            output={"cta": context.bundle.email.cta, "rule_id": rule_id, "source": "deterministic"},
        )
