"""Deterministic fixtures for the mock model runtime.

Lets the whole application be exercised without a Gemini key: reproducible output
with the same shape a real model produces. Ported from the previous
``MockAIProvider`` so demo and test output is unchanged apart from rule handling,
which now comes from the ``rules`` table rather than environment variables.

Nothing here is used when ``AI_PROVIDER=gemini``.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents import rules as rules_engine
from app.agents.types import CopyRequest, ExtractedBrief
from app.core.logging import get_logger
from app.schemas.copy_output import CopyBundle, EmailCopy, MobileCopy, SMSCopy
from app.utils.text import similarity, truncate

logger = get_logger("app.agents.mock")

# Feature keyword -> marketing noun phrase, so extracted keywords read naturally.
FEATURE_PHRASES: dict[str, str] = {
    "speed": "responsive speed",
    "comfort": "lasting comfort",
    "cushioning": "responsive cushioning",
    "responsive cushioning": "responsive cushioning",
    "durability": "everyday durability",
    "lightweight": "a lightweight feel",
    "breathable": "breathable support",
    "modern design": "modern design",
    "design": "modern design",
    "performance": "proven performance",
    "quality": "premium quality",
    "style": "standout style",
    "versatility": "everyday versatility",
    "sustainability": "responsible materials",
    "battery life": "all-day battery life",
}

# Ordered by how well each term works as the first benefit in a sub-heading.
FEATURE_PRIORITY = (
    "speed",
    "comfort",
    "responsive cushioning",
    "cushioning",
    "performance",
    "durability",
    "lightweight",
    "breathable",
    "modern design",
    "design",
    "quality",
    "style",
    "versatility",
)

FEATURE_KEYWORDS = (
    "lightweight",
    "breathable",
    "speed",
    "comfort",
    "durability",
    "responsive cushioning",
    "cushioning",
    "modern design",
    "performance",
    "quality",
    "style",
    "versatility",
    "sustainability",
    "battery life",
    "waterproof",
    "adjustable",
)

TONE_KEYWORDS = (
    "exciting",
    "energetic",
    "premium",
    "playful",
    "confident",
    "bold",
    "warm",
    "professional",
    "urgent",
    "inspiring",
)

SEGMENT_OPENERS: dict[str, tuple[str, ...]] = {
    "trendsetters": ("Set The Pace.", "Own The Look.", "Lead The Line."),
    "enthusiasts": ("Built For The Details.", "Made For The Obsessed.", "Crafted To Impress."),
    "performance seekers": ("Run Lighter.", "Push Further.", "Train Harder."),
    "general": ("Made For Every Day.", "Comfort, Everywhere.", "Ready When You Are."),
}

SEGMENT_SUPERLINES: dict[str, str] = {
    "trendsetters": "NEW DROP",
    "enthusiasts": "MEMBER FIRST LOOK",
    "performance seekers": "JUST LAUNCHED",
    "general": "NOW AVAILABLE",
}

SEGMENT_CLOSERS: dict[str, str] = {
    "trendsetters": "styled to stand out",
    "enthusiasts": "engineered down to the last detail",
    "performance seekers": "built to keep up with you",
    "general": "made to fit your everyday",
}

# Sized so the cycles run out of step, giving VARIATION_COUNT distinct results.
VARIATION_INTROS = ("Introducing", "Meet", "Say hello to", "Now available:")
VARIATION_HEADLINE_SUFFIXES = ("", " Feel The Difference.", " Move Your Way.")
# The closer phrases are predicates ("built to keep up with you"), so every
# pattern has to read grammatically with "is {closer}" or a trailing clause.
MOBILE_SUB_PATTERNS = (
    "{product}: {feature_a} and {feature_b}, {closer}.",
    "{feature_a_capitalised} meets {feature_b}. {product} is {closer}.",
    "{product} delivers {feature_a} and {feature_b}, and is {closer}.",
)
SMS_PATTERNS = (
    "{product} has landed. {feature_a_capitalised}, {feature_b}, and {closer}. Shop now.",
    "New in: {product}. {feature_a_capitalised} meets {feature_b}. Shop today.",
    "{product} is here - {feature_a}, {feature_b}, {closer}. Take a look.",
)
VARIATION_COUNT = 12


# -- Fixture builders (called by the FunctionModel) --------------------------


def extraction_fixture(brief_and_language: Any) -> dict[str, Any]:
    """Build the extraction output. ``brief_and_language`` is a ``(brief, language)``."""
    brief, _language = brief_and_language
    logger.info("mock runtime: extracting brief")

    lowered = brief.lower()
    features = [keyword for keyword in FEATURE_KEYWORDS if keyword in lowered]
    # Drop the generic term when the specific phrase already matched.
    if "responsive cushioning" in features and "cushioning" in features:
        features.remove("cushioning")
    if "modern design" in features and "design" in features:
        features.remove("design")

    products = _extract_product_names(brief)
    return {
        "brand": products[0].split()[0] if products else None,
        "products": products,
        "skus": _extract_skus(brief),
        "athletes": _extract_named_people(brief),
        "campaign_goal": _extract_goal(brief),
        "features": features,
        "tone": next((keyword for keyword in TONE_KEYWORDS if keyword in lowered), None),
        "key_message": _extract_key_message(brief),
    }


def copy_fixture(request: Any) -> dict[str, Any]:
    """Build the copy generation output for a :class:`CopyRequest`."""
    logger.info("mock runtime: generating copy")
    bundle = compose(request, variation=len(request.previous_copy))
    return rules_engine.autofix(bundle, request.rules, request.channel).model_dump()


def variety_fixture(payload: Any) -> dict[str, Any]:
    """Build the repetition rewrite. ``payload`` is a ``(request, bundle)``."""
    request, current = payload
    logger.info("mock runtime: rewriting for variety")
    rewritten = _least_repetitive_variant(request, current)
    # The CTA is owned by the deterministic CTA agent and must survive untouched.
    merged = CopyBundle(
        email=EmailCopy(
            headline=rewritten.email.headline,
            sub_heading=rewritten.email.sub_heading,
            cta=current.email.cta,
        ),
        mobile=MobileCopy(
            superline=rewritten.mobile.superline,
            pre_heading=rewritten.mobile.pre_heading,
            headline=rewritten.mobile.headline,
            sub_heading=rewritten.mobile.sub_heading,
            cta=current.mobile.cta,
        ),
        sms=SMSCopy(description=rewritten.sms.description),
    )
    return rules_engine.autofix(merged, request.rules, request.channel).model_dump()


def judge_fixture(payload: Any) -> dict[str, Any]:
    """The mock judge passes everything.

    Deterministic rules are already enforced in code, so a mock verdict that
    invents guideline violations would only add noise to local runs and tests.
    """
    logger.info("mock runtime: judging copy")
    return {
        "passed": True,
        "score": 1.0,
        "naturalness": 1.0,
        "violations": [],
        "reasoning": "Mock runtime: deterministic rules passed; no guideline review performed.",
    }


def revision_fixture(payload: Any) -> dict[str, Any]:
    """Revision under the mock runtime returns the copy unchanged.

    The mock judge never fails, so this only runs if an operator forces a
    revision; returning the input keeps the workflow well defined.
    """
    request, bundle, _violations = payload
    return rules_engine.autofix(bundle, request.rules, request.channel).model_dump()


# -- Composition -------------------------------------------------------------


def compose(request: CopyRequest, *, variation: int) -> CopyBundle:
    segment_key = _segment_key(request.audience_name)
    product = request.product_name or _first(request.extracted.products) or "the collection"
    brand = request.brand_name or request.extracted.brand or "our latest release"
    features = _feature_phrases(request.extracted.features or request.product_features)
    closer = _closing_phrase(product, segment_key)
    provisional_cta = _provisional_cta(request.product_name, request.brand_name)

    headline = _headline(request, segment_key, variation)
    intro = VARIATION_INTROS[variation % len(VARIATION_INTROS)]

    email_sub = (
        f"{intro} {product}, engineered for {features[0]}, "
        f"built for {features[1]}, and designed for {closer}."
    )
    fields = {
        "product": product,
        "feature_a": features[0],
        "feature_a_capitalised": features[0].capitalize(),
        "feature_b": features[1],
        "closer": SEGMENT_CLOSERS[segment_key],
    }
    mobile_sub = MOBILE_SUB_PATTERNS[variation % len(MOBILE_SUB_PATTERNS)].format(**fields)
    sms_text = SMS_PATTERNS[variation % len(SMS_PATTERNS)].format(**fields)

    return CopyBundle(
        email=EmailCopy(headline=headline, sub_heading=email_sub, cta=provisional_cta),
        mobile=MobileCopy(
            superline=SEGMENT_SUPERLINES[segment_key],
            pre_heading=f"{brand} for {request.audience_name or 'everyone'}",
            headline=headline,
            sub_heading=mobile_sub,
            cta=provisional_cta,
        ),
        sms=SMSCopy(description=sms_text),
    )


def _least_repetitive_variant(request: CopyRequest, current: CopyBundle) -> CopyBundle:
    """Score every variant against the history and return the freshest one.

    Only the fields that vary between variants are scored; the fixed ones
    (superline, pre-heading) would otherwise saturate the comparison.
    """
    history = [*request.previous_copy, *current.text_fields()]
    best: tuple[float, CopyBundle] | None = None
    for variation in range(VARIATION_COUNT):
        candidate = compose(request, variation=variation)
        varying = [
            candidate.email.headline,
            candidate.email.sub_heading,
            candidate.mobile.sub_heading,
            candidate.sms.description,
        ]
        scores = [
            max((similarity(field, previous) for previous in history), default=0.0)
            for field in varying
        ]
        score = sum(scores) / len(scores)
        if best is None or score < best[0]:
            best = (score, candidate)
    assert best is not None  # VARIATION_COUNT is always >= 1
    return best[1]


def _headline(request: CopyRequest, segment_key: str, variation: int) -> str:
    key_message = request.extracted.key_message
    if key_message:
        base = _title_case_sentences(key_message)
    else:
        opener = SEGMENT_OPENERS[segment_key][variation % len(SEGMENT_OPENERS[segment_key])]
        product = request.product_name or _first(request.extracted.products) or "The Collection"
        base = f"{opener} {product}."
    suffix = VARIATION_HEADLINE_SUFFIXES[variation % len(VARIATION_HEADLINE_SUFFIXES)]
    return f"{base}{suffix}".strip()


def _title_case_sentences(text: str) -> str:
    """``run lighter. go farther.`` -> ``Run Lighter. Go Farther.``"""
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s*", text) if part.strip()]
    titled = []
    for part in parts:
        words = part.split()
        titled.append(
            " ".join(word if word.isupper() else word[:1].upper() + word[1:] for word in words)
        )
    joined = " ".join(titled)
    return joined if joined.endswith((".", "!", "?")) else f"{joined}."


def _feature_phrases(features: list[str]) -> list[str]:
    def rank(feature: str) -> int:
        return (
            FEATURE_PRIORITY.index(feature)
            if feature in FEATURE_PRIORITY
            else len(FEATURE_PRIORITY)
        )

    ranked = sorted((feature for feature in features if feature), key=rank)
    phrases = [FEATURE_PHRASES.get(feature, feature) for feature in ranked]
    # Always return at least two phrases so composition never index-errors.
    defaults = ["standout quality", "everyday versatility"]
    for default in defaults:
        if len(phrases) >= 2:
            break
        if default not in phrases:
            phrases.append(default)
    return phrases


def _closing_phrase(product: str, segment_key: str) -> str:
    lowered = product.lower()
    if "run" in lowered:
        return "every run"
    if "train" in lowered:
        return "every session"
    if segment_key == "performance seekers":
        return "every workout"
    return "every day"


def _provisional_cta(product_name: str | None, brand_name: str | None) -> str:
    if product_name:
        return f"SHOP {product_name.upper()}"
    if brand_name:
        return f"EXPLORE {brand_name.upper()}"
    return "SHOP THE COLLECTION"


def _segment_key(audience_name: str | None) -> str:
    if not audience_name:
        return "general"
    lowered = audience_name.strip().lower()
    if lowered in SEGMENT_OPENERS:
        return lowered
    for key in SEGMENT_OPENERS:
        if key in lowered or lowered in key:
            return key
    return "general"


def _first(values: list[str]) -> str | None:
    return values[0] if values else None


# -- Brief parsing -----------------------------------------------------------


def _extract_product_names(brief: str) -> list[str]:
    """Find capitalised multi-word product names such as ``AeroFlex Running Shoes``."""
    pattern = re.compile(r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){1,3})\b")
    ignore_prefixes = ("Key ", "The ", "We ", "Promote ", "Highlight ", "Available ")
    found: list[str] = []
    for match in pattern.finditer(brief):
        candidate = match.group(1).strip()
        if candidate.startswith(ignore_prefixes) or len(candidate) < 5:
            continue
        if candidate not in found:
            found.append(candidate)
    return found[:3]


def _extract_skus(brief: str) -> list[str]:
    pattern = re.compile(r"\b(?:SKU[:\s-]*)?([A-Z]{2,}[0-9]{2,}[A-Z0-9-]*)\b")
    return list(dict.fromkeys(match.group(1) for match in pattern.finditer(brief)))[:5]


def _extract_named_people(brief: str) -> list[str]:
    """Only return people the brief explicitly labels; never invent endorsements."""
    pattern = re.compile(
        r"(?:athlete|ambassador|endorsed by|featuring|starring)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        re.IGNORECASE,
    )
    return list(dict.fromkeys(match.group(1) for match in pattern.finditer(brief)))[:5]


def _extract_goal(brief: str) -> str | None:
    for sentence in re.split(r"(?<=[.!?])\s+", brief.strip()):
        lowered = sentence.lower()
        if any(word in lowered for word in ("launch", "promote", "drive", "announce", "grow")):
            return truncate(sentence.strip(), 200)
    return None


def _extract_key_message(brief: str) -> str | None:
    match = re.search(r"key message\s*[:\-]\s*(.+)", brief, re.IGNORECASE)
    if not match:
        return None
    return truncate(match.group(1).split("\n")[0].strip(), 160)


def structured_brief(brief: str, language: str) -> ExtractedBrief:
    """Convenience wrapper used by tests that want the parsed brief directly."""
    payload = extraction_fixture((brief, language))
    return ExtractedBrief(**payload)
