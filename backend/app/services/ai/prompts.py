"""Prompt construction for the Gemini provider.

Kept separate from transport so prompts can be reviewed and unit tested without a
network client.
"""

from __future__ import annotations

import json

from app.services.ai.provider import CopyRequest

EXTRACTION_SYSTEM_PROMPT = """\
You are a marketing data extraction agent. Read the raw campaign brief and return
structured facts that are explicitly present in it.

Rules:
- Never invent brands, products, SKUs, features or endorsements.
- Only list a person under "athletes" when the brief explicitly names them as an
  athlete, ambassador or endorser.
- Leave a field empty when the brief does not state it.
- Respond with JSON only, matching the requested schema exactly.
"""

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "brand": {"type": "string", "nullable": True},
        "products": {"type": "array", "items": {"type": "string"}},
        "skus": {"type": "array", "items": {"type": "string"}},
        "athletes": {"type": "array", "items": {"type": "string"}},
        "campaign_goal": {"type": "string", "nullable": True},
        "features": {"type": "array", "items": {"type": "string"}},
        "tone": {"type": "string", "nullable": True},
        "key_message": {"type": "string", "nullable": True},
    },
    "required": ["products", "features"],
}

COPY_SYSTEM_PROMPT = """\
You are a senior marketing copywriter producing channel-ready campaign copy.

Rules:
- Base every claim on the supplied brief, product features and grounding notes.
  Never state a fact that is not supported by them.
- Write for the supplied audience segment and follow its tone guidance.
- Respect the character limits for every field. Shorter is better than truncated.
- Do not reuse sentences or distinctive phrases from the "previously generated
  copy" section.
- Write in the requested language.
- Respond with JSON only, matching the requested schema exactly.
"""

COPY_SCHEMA = {
    "type": "object",
    "properties": {
        "email": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "sub_heading": {"type": "string"},
                "cta": {"type": "string"},
            },
            "required": ["headline", "sub_heading", "cta"],
        },
        "mobile": {
            "type": "object",
            "properties": {
                "superline": {"type": "string"},
                "pre_heading": {"type": "string"},
                "headline": {"type": "string"},
                "sub_heading": {"type": "string"},
                "cta": {"type": "string"},
            },
            "required": ["superline", "pre_heading", "headline", "sub_heading", "cta"],
        },
        "sms": {
            "type": "object",
            "properties": {"description": {"type": "string"}},
            "required": ["description"],
        },
    },
    "required": ["email", "mobile", "sms"],
}

REPAIR_SYSTEM_PROMPT = """\
You repair malformed JSON. Return only the corrected JSON object that satisfies the
supplied schema. Do not add commentary, explanations or code fences.
"""


def build_extraction_prompt(brief: str, language: str) -> str:
    return (
        f"Campaign brief (language: {language}):\n"
        f"---\n{brief}\n---\n\n"
        "Extract the structured campaign data as JSON."
    )


def build_copy_prompt(request: CopyRequest) -> str:
    limits = request.channel_limits
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

    extracted = request.extracted.to_dict()
    sections.append(f"Extracted brief data:\n{json.dumps(extracted, indent=2)}")

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

    if request.previous_copy:
        previous = "\n".join(f"- {item}" for item in request.previous_copy[:12])
        sections.append(f"Previously generated copy to avoid repeating:\n{previous}")

    if request.prompt_template:
        sections.append(f"Additional channel template guidance:\n{request.prompt_template}")

    sections.append(f"Character limits per field:\n{json.dumps(limits, indent=2)}")
    sections.append(
        "Produce copy for all three channels (email, mobile, sms) as a single JSON object. "
        "The 'cta' fields are placeholders and will be replaced by deterministic brand rules; "
        "keep them short and action oriented."
    )
    return "\n\n".join(sections)


def build_rewrite_prompt(
    request: CopyRequest, current: dict, repeated_phrases: list[str]
) -> str:
    phrases = "\n".join(f"- {phrase}" for phrase in repeated_phrases) or "- (general similarity)"
    return (
        "The following campaign copy repeats earlier generations and must be rewritten.\n\n"
        f"Current copy:\n{json.dumps(current, indent=2)}\n\n"
        f"Repeated phrases to eliminate:\n{phrases}\n\n"
        "Rewrite the headline, sub-heading, superline, pre-heading and SMS description so "
        "they express the same campaign meaning with different wording. "
        "Keep every 'cta' value exactly as provided. Respect the same character limits. "
        f"Language: {request.language}. Respond with the same JSON structure."
    )
