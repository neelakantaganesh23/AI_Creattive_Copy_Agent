"""Prompt construction for the workflow agents.

Kept separate from the agents themselves so prompts can be reviewed and unit
tested without a model. Pydantic AI owns the output schemas, so nothing here
describes JSON shapes any more -- these are instructions and context only.
"""

from __future__ import annotations

import json

from app.agents.rules import build_rule_instructions
from app.agents.types import CopyRequest
from app.schemas.copy_output import CopyBundle, RuleViolation

EXTRACTION_INSTRUCTIONS = """\
You are a marketing data extraction agent. Read the raw campaign brief and return
structured facts that are explicitly present in it.

Rules:
- Never invent brands, products, SKUs, features or endorsements.
- Only list a person under "athletes" when the brief explicitly names them as an
  athlete, ambassador or endorser.
- Leave a field empty when the brief does not state it.
"""

COPY_INSTRUCTIONS = """\
You are a senior marketing copywriter producing channel-ready campaign copy.

Rules:
- Base every claim on the supplied brief, product features and grounding notes.
  Never state a fact that is not supported by them.
- Write for the supplied audience segment and follow its tone guidance.
- Obey every content rule exactly. They are hard requirements, not suggestions.
- Prefer copy that is naturally short over copy that is cut short.
- Do not reuse sentences or distinctive phrases from the "previously generated
  copy" section.
- Write in the requested language.
"""

JUDGE_INSTRUCTIONS = """\
You are a meticulous marketing copy reviewer. Assess the supplied copy against the
brand's content guidelines and report what fails.

How to judge:
- Only report a violation you can point to in the copy. Do not speculate.
- Character counts and word counts have already been verified in code. Do not
  comment on them; focus on meaning, tone and phrasing.
- "Natural" means a person would say it out loud: no keyword stuffing, no
  robotic constructions, no repeated sentence shapes across fields.
- Judge the copy against the brief and the audience it is written for, not
  against your own taste.
- Score 1.0 when the copy is publishable as-is; below 0.5 only when a guideline
  is clearly broken.
- Set passed to false only when at least one violation has error severity.
"""

REVISION_INSTRUCTIONS = """\
You are a marketing copy editor. Rewrite only what the reviewer flagged.

Rules:
- Fix every reported violation.
- Leave everything the reviewer did not mention exactly as it is.
- Never introduce a claim that was not already in the copy.
- Keep the call to action text character for character: it is set by a
  deterministic brand rule, not by you.
"""

VARIETY_INSTRUCTIONS = """\
You are a senior marketing copywriter rewriting copy that came out too similar to
earlier campaigns.

Rules:
- Replace every repeated phrase with a fresh formulation.
- Keep the same product facts, audience and tone.
- Keep the call to action text character for character.
- Obey every content rule exactly.
"""


def build_extraction_prompt(brief: str, language: str) -> str:
    return (
        f"Campaign brief (language: {language}):\n"
        f"---\n{brief}\n---\n\n"
        "Extract the structured campaign data."
    )


def _context_sections(request: CopyRequest) -> list[str]:
    """The shared brief/brand/audience context every copy prompt needs."""
    sections: list[str] = [
        f"Primary channel: {request.channel.value}",
        f"Language: {request.language}",
        f"Campaign brief:\n{request.brief}",
    ]

    if request.brand_name:
        sections.append(f"Brand: {request.brand_name}")
    if request.brand_guidelines:
        sections.append(f"Brand guidelines: {request.brand_guidelines}")
    if request.product_name:
        sections.append(f"Product: {request.product_name}")
    if request.product_features:
        sections.append(f"Product features: {', '.join(request.product_features)}")
    if request.audience_name:
        sections.append(f"Audience segment: {request.audience_name}")
    if request.audience_description:
        sections.append(f"Audience description: {request.audience_description}")
    if request.audience_tone:
        sections.append(f"Audience tone guidance: {request.audience_tone}")

    sections.append(
        f"Extracted brief data:\n{json.dumps(request.extracted.to_dict(), indent=2)}"
    )

    if request.grounding.grounded and request.grounding.sources:
        grounding_lines = "\n".join(
            f"- {source.title}: {source.snippet or source.url}"
            for source in request.grounding.sources
        )
        sections.append(f"Verified grounding notes (safe to reference):\n{grounding_lines}")
    else:
        sections.append(
            "No external grounding is available. Use only the brief and product data."
        )

    rule_text = build_rule_instructions(request.rules, request.channel)
    if rule_text:
        sections.append(rule_text)

    return sections


def build_copy_prompt(request: CopyRequest) -> str:
    sections = _context_sections(request)

    if request.previous_copy:
        previous = "\n".join(f"- {item}" for item in request.previous_copy[:12])
        sections.append(f"Previously generated copy to avoid repeating:\n{previous}")
    if request.prompt_template:
        sections.append(f"Additional campaign template guidance:\n{request.prompt_template}")

    sections.append(
        "Write the Email, Mobile and SMS copy. The call to action is provisional; "
        "a brand rule may replace it afterwards."
    )
    return "\n\n".join(sections)


def build_rewrite_prompt(
    request: CopyRequest, bundle: CopyBundle, repeated_phrases: list[str]
) -> str:
    sections = _context_sections(request)
    sections.append(f"Current copy:\n{json.dumps(bundle.model_dump(), indent=2)}")
    if repeated_phrases:
        phrases = "\n".join(f"- {phrase}" for phrase in repeated_phrases[:10])
        sections.append(f"Phrases that repeat earlier campaigns and must change:\n{phrases}")
    sections.append("Rewrite the copy so none of those phrases survive.")
    return "\n\n".join(sections)


def build_judge_prompt(request: CopyRequest, bundle: CopyBundle) -> str:
    from app.agents.rules import guideline_rules

    sections: list[str] = [
        f"Channel under review: {request.channel.label}",
        f"Language: {request.language}",
        f"Campaign brief:\n{request.brief}",
    ]
    if request.brand_guidelines:
        sections.append(f"Brand guidelines: {request.brand_guidelines}")
    if request.audience_name:
        sections.append(
            f"Audience: {request.audience_name}"
            + (f" -- {request.audience_tone}" if request.audience_tone else "")
        )

    guidelines = guideline_rules(request.rules)
    if guidelines:
        rendered = "\n".join(
            f"- [{rule.severity}] {rule.name}: {rule.value}" for rule in guidelines
        )
        sections.append(f"Guidelines to enforce:\n{rendered}")
    else:
        sections.append(
            "No explicit guidelines are configured. Judge naturalness and internal "
            "repetition only."
        )

    payload = bundle.channel_payload(request.channel)
    sections.append(f"Copy under review:\n{json.dumps(payload, indent=2)}")
    sections.append(
        "Report violations against the field names shown above. Use those exact names."
    )
    return "\n\n".join(sections)


def build_revision_prompt(
    request: CopyRequest, bundle: CopyBundle, violations: list[RuleViolation]
) -> str:
    from app.agents.rules import describe_violations

    sections = _context_sections(request)
    sections.append(f"Current copy:\n{json.dumps(bundle.model_dump(), indent=2)}")
    sections.append(f"Reviewer findings to fix:\n{describe_violations(violations)}")
    sections.append("Return the full copy with those findings resolved.")
    return "\n\n".join(sections)
