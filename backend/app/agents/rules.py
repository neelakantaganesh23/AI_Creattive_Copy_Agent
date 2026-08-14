"""Deterministic content rule evaluation.

Everything an admin configures that a machine can check -- character limits, word
counts, banned or required terms, regex patterns -- is enforced here rather than by
the model. The functions are pure: they take detached :class:`RuleData` and a
:class:`CopyBundle` and return violations, so they are trivially unit testable and
never touch the ORM.

Two consumers:

* :func:`build_rule_instructions` renders the rules into the copywriter's prompt,
  so the model complies on the first attempt.
* :func:`evaluate_rules` runs as the copy agent's output validator; a violation is
  raised back to the model as a correction request.

Natural-language rules (:attr:`RuleType.GUIDELINE`) are not checkable here and are
passed to the LLM judge instead.
"""

from __future__ import annotations

import re

from app.agents.types import RuleData
from app.core.logging import get_logger
from app.models.enums import CHANNEL_FIELDS, Channel, RuleType, Severity
from app.schemas.copy_output import CopyBundle, RuleViolation
from app.utils.text import truncate

logger = get_logger("app.agents.rules")

_WORD_RE = re.compile(r"\S+")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.strip())


def _terms(value: str) -> list[str]:
    return [term.strip() for term in value.split(",") if term.strip()]


def _as_int(rule: RuleData) -> int | None:
    try:
        return int(str(rule.value).strip())
    except (TypeError, ValueError):
        logger.warning(
            "ignoring rule with a non-numeric value",
            extra={"rule_id": rule.id, "rule_type": rule.rule_type},
        )
        return None


# -- Scoping -----------------------------------------------------------------


def applicable_rules(
    rules: list[RuleData],
    *,
    channel: Channel,
    brand_id: int | None,
    audience_segment_id: int | None,
) -> list[RuleData]:
    """Filter to the rules that apply to this generation.

    A NULL scope column is a wildcard, matching :func:`app.agents.cta.resolve_cta`.
    """
    matched = [
        rule
        for rule in rules
        if (rule.channel is None or rule.channel == channel.value)
        and (rule.brand_id is None or rule.brand_id == brand_id)
        and (
            rule.audience_segment_id is None
            or rule.audience_segment_id == audience_segment_id
        )
    ]
    return sorted(matched, key=lambda rule: (-rule.priority, rule.id))


def _target_fields(rule: RuleData, channel: Channel) -> tuple[str, ...]:
    """Which fields of ``channel`` a rule applies to."""
    available = CHANNEL_FIELDS[channel]
    if rule.field_name is None:
        return available
    return (rule.field_name,) if rule.field_name in available else ()


# -- Evaluation --------------------------------------------------------------


def _check(rule: RuleData, field: str, value: str) -> RuleViolation | None:
    """Evaluate one rule against one field."""
    severity = Severity(rule.severity)
    common = {
        "field": field,
        "severity": severity,
        "rule_id": rule.id,
        "rule_name": rule.name,
    }
    label = field.replace("_", " ")

    match rule.rule_type:
        case RuleType.MAX_CHARS:
            limit = _as_int(rule)
            if limit is not None and len(value) > limit:
                return RuleViolation(
                    **common,
                    explanation=f"is {len(value)} characters, maximum {limit}",
                    suggestion=f"Shorten the {label} to {limit} characters or fewer.",
                )
        case RuleType.MIN_CHARS:
            minimum = _as_int(rule)
            if minimum is not None and len(value) < minimum:
                return RuleViolation(
                    **common,
                    explanation=f"is {len(value)} characters, minimum {minimum}",
                    suggestion=f"Expand the {label} to at least {minimum} characters.",
                )
        case RuleType.MAX_WORDS:
            limit = _as_int(rule)
            count = len(_words(value))
            if limit is not None and count > limit:
                return RuleViolation(
                    **common,
                    explanation=f"is {count} words, maximum {limit}",
                    suggestion=f"Rewrite the {label} in {limit} words or fewer.",
                )
        case RuleType.MIN_WORDS:
            minimum = _as_int(rule)
            count = len(_words(value))
            if minimum is not None and count < minimum:
                return RuleViolation(
                    **common,
                    explanation=f"is {count} words, minimum {minimum}",
                    suggestion=f"Rewrite the {label} using at least {minimum} words.",
                )
        case RuleType.FORBIDDEN_TERMS:
            lowered = value.lower()
            hits = [term for term in _terms(rule.value) if term.lower() in lowered]
            if hits:
                return RuleViolation(
                    **common,
                    explanation=f"uses forbidden wording: {', '.join(hits)}",
                    suggestion=f"Remove {', '.join(hits)} from the {label}.",
                )
        case RuleType.REQUIRED_TERMS:
            lowered = value.lower()
            missing = [term for term in _terms(rule.value) if term.lower() not in lowered]
            if missing:
                return RuleViolation(
                    **common,
                    explanation=f"is missing required wording: {', '.join(missing)}",
                    suggestion=f"Include {', '.join(missing)} in the {label}.",
                )
        case RuleType.REGEX:
            try:
                pattern = re.compile(rule.value)
            except re.error:
                logger.warning("ignoring rule with an invalid regex", extra={"rule_id": rule.id})
                return None
            if not pattern.search(value):
                return RuleViolation(
                    **common,
                    explanation=f"does not match the required pattern {rule.value}",
                    suggestion=rule.description or f"Rewrite the {label} to match the pattern.",
                )
        case RuleType.GUIDELINE:
            # Assessed by the judge, not here.
            return None

    return None


def evaluate_rules(
    bundle: CopyBundle, rules: list[RuleData], channel: Channel
) -> list[RuleViolation]:
    """Return every deterministic rule violation in ``bundle``.

    Only the requested channel is evaluated. The other channels are still produced
    and stored, but the generation is scoped to one channel and rules are written
    against it.
    """
    payload = bundle.channel_payload(channel)
    violations: list[RuleViolation] = []
    for rule in rules:
        if not rule.is_deterministic:
            continue
        for field in _target_fields(rule, channel):
            value = payload.get(field)
            if not isinstance(value, str):
                continue
            violation = _check(rule, field, value)
            if violation is not None:
                violations.append(violation)
    return violations


def guideline_rules(rules: list[RuleData]) -> list[RuleData]:
    return [rule for rule in rules if not rule.is_deterministic]


# -- Prompting ---------------------------------------------------------------


def _describe(rule: RuleData, channel: Channel) -> str | None:
    fields = _target_fields(rule, channel)
    if not fields:
        return None
    scope = "every field" if rule.field_name is None else rule.field_name.replace("_", " ")

    match rule.rule_type:
        case RuleType.MAX_CHARS:
            body = f"at most {rule.value} characters"
        case RuleType.MIN_CHARS:
            body = f"at least {rule.value} characters"
        case RuleType.MAX_WORDS:
            body = f"at most {rule.value} words"
        case RuleType.MIN_WORDS:
            body = f"at least {rule.value} words"
        case RuleType.FORBIDDEN_TERMS:
            body = f"must never contain: {', '.join(_terms(rule.value))}"
        case RuleType.REQUIRED_TERMS:
            body = f"must contain: {', '.join(_terms(rule.value))}"
        case RuleType.REGEX:
            body = f"must match the pattern {rule.value}"
        case RuleType.GUIDELINE:
            body = rule.value
        case _:  # pragma: no cover - RuleType is exhaustive
            return None

    return f"- {scope}: {body}"


def build_rule_instructions(rules: list[RuleData], channel: Channel) -> str:
    """Render the applicable rules as prompt text.

    Rules are given to the model up front so it complies on the first attempt;
    :func:`evaluate_rules` is the backstop, not the primary mechanism.
    """
    lines = [line for rule in rules if (line := _describe(rule, channel))]
    if not lines:
        return ""
    return "Content rules for the " + channel.label + " copy (all are mandatory):\n" + "\n".join(
        lines
    )


def describe_violations(violations: list[RuleViolation]) -> str:
    """Render violations as a correction instruction for the model."""
    lines = []
    for violation in violations:
        label = violation.field.replace("_", " ")
        suffix = f" {violation.suggestion}" if violation.suggestion else ""
        lines.append(f"- {label} {violation.explanation}.{suffix}")
    return "\n".join(lines)


# -- Best-effort repair ------------------------------------------------------


def autofix(bundle: CopyBundle, rules: list[RuleData], channel: Channel) -> CopyBundle:
    """Trim fields that overrun their length or word limits.

    Used only by the mock runtime, which cannot rewrite its way out of a
    violation the way a real model can. Truncation is deliberately not applied on
    the Gemini path: there the model is asked to rewrite instead, which produces
    copy that still reads as a sentence.
    """
    payload = bundle.channel_payload(channel)
    fixed = dict(payload)
    for rule in rules:
        if rule.rule_type not in (RuleType.MAX_CHARS, RuleType.MAX_WORDS):
            continue
        limit = _as_int(rule)
        if limit is None:
            continue
        for field in _target_fields(rule, channel):
            value = fixed.get(field)
            if not isinstance(value, str):
                continue
            if rule.rule_type == RuleType.MAX_CHARS:
                fixed[field] = truncate(value, limit)
            else:
                words = _words(value)
                if len(words) > limit:
                    fixed[field] = " ".join(words[:limit]).rstrip(" ,;:-")

    if fixed == payload:
        return bundle
    return bundle.model_copy(update={channel.value: _rebuild(bundle, channel, fixed)})


def _rebuild(bundle: CopyBundle, channel: Channel, values: dict[str, object]):
    current = getattr(bundle, channel.value)
    return current.model_validate(values)
