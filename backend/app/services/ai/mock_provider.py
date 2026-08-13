"""Deterministic mock AI provider (§21).

Lets the whole application be exercised without a Gemini key: same interface, same
timing shape, reproducible output. It is never imported by the Gemini provider and
announces itself in the logs on every call.
"""

from __future__ import annotations

import asyncio
import re

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.copy_output import CopyBundle, EmailCopy, MobileCopy, SMSCopy
from app.services.ai.provider import (
    AIProvider,
    CopyRequest,
    ExtractedBrief,
    ProviderInfo,
)
from app.utils.text import similarity, truncate

logger = get_logger("app.ai.mock")

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


class MockAIProvider:
    """A rules-based stand-in that mirrors :class:`AIProvider`."""

    name = "mock"

    def info(self) -> ProviderInfo:
        return ProviderInfo(name=self.name, fast_model="mock-fast", quality_model="mock-quality")

    async def _simulate_latency(self) -> None:
        delay = max(settings.mock_stage_delay_ms, 0) / 1000
        if delay:
            await asyncio.sleep(delay)

    # -- Agent 1 -------------------------------------------------------------
    async def extract_brief(self, brief: str, *, language: str) -> ExtractedBrief:
        logger.info("mock provider: extracting brief", extra={"provider": self.name})
        await self._simulate_latency()

        lowered = brief.lower()
        features = [keyword for keyword in FEATURE_KEYWORDS if keyword in lowered]
        # Drop the generic term when the specific phrase already matched.
        if "responsive cushioning" in features and "cushioning" in features:
            features.remove("cushioning")
        if "modern design" in features and "design" in features:
            features.remove("design")

        tone = next((keyword for keyword in TONE_KEYWORDS if keyword in lowered), None)
        products = _extract_product_names(brief)
        brand = products[0].split()[0] if products else None

        return ExtractedBrief(
            brand=brand,
            products=products,
            skus=_extract_skus(brief),
            athletes=_extract_named_people(brief),
            campaign_goal=_extract_goal(brief),
            features=features,
            tone=tone,
            key_message=_extract_key_message(brief),
        )

    # -- Agent 3 -------------------------------------------------------------
    async def generate_copy(self, request: CopyRequest) -> CopyBundle:
        logger.info(
            "mock provider: generating copy",
            extra={
                "provider": self.name,
                "channel": str(request.channel),
                "language": request.language,
            },
        )
        await self._simulate_latency()
        return self._compose(request, variation=len(request.previous_copy))

    # -- Agent 4 -------------------------------------------------------------
    async def rewrite_for_variety(
        self, request: CopyRequest, bundle: CopyBundle, repeated_phrases: list[str]
    ) -> CopyBundle:
        logger.info(
            "mock provider: rewriting for variety",
            extra={"provider": self.name, "repeated_phrases": len(repeated_phrases)},
        )
        await self._simulate_latency()
        # Pick the variant least similar to everything generated before, ignoring
        # any that reproduces the copy being rewritten. The CTA is left untouched
        # because it is owned by the deterministic CTA agent.
        rewritten = self._least_repetitive_variant(request, bundle)
        return CopyBundle(
            email=EmailCopy(
                headline=rewritten.email.headline,
                sub_heading=rewritten.email.sub_heading,
                cta=bundle.email.cta,
            ),
            mobile=MobileCopy(
                superline=rewritten.mobile.superline,
                pre_heading=rewritten.mobile.pre_heading,
                headline=rewritten.mobile.headline,
                sub_heading=rewritten.mobile.sub_heading,
                cta=bundle.mobile.cta,
            ),
            sms=SMSCopy(description=rewritten.sms.description),
        )

    def _least_repetitive_variant(self, request: CopyRequest, current: CopyBundle) -> CopyBundle:
        """Score every variant against the history and return the freshest one.

        Only the fields that vary between variants are scored; the fixed ones
        (superline, pre-heading) would otherwise saturate the comparison.
        """
        history = [*request.previous_copy, *current.text_fields()]
        best: tuple[float, CopyBundle] | None = None
        for variation in range(VARIATION_COUNT):
            candidate = self._compose(request, variation=variation)
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

    # -- Composition ---------------------------------------------------------
    def _compose(self, request: CopyRequest, *, variation: int) -> CopyBundle:
        limits = request.channel_limits or settings.channel_limits
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
            email=EmailCopy(
                headline=truncate(headline, limits["email"]["headline"]),
                sub_heading=truncate(email_sub, limits["email"]["sub_heading"]),
                cta=truncate(provisional_cta, limits["email"]["cta"]),
            ),
            mobile=MobileCopy(
                superline=truncate(
                    SEGMENT_SUPERLINES[segment_key], limits["mobile"]["superline"]
                ),
                pre_heading=truncate(
                    f"{brand} for {request.audience_name or 'everyone'}",
                    limits["mobile"]["pre_heading"],
                ),
                headline=truncate(headline, limits["mobile"]["headline"]),
                sub_heading=truncate(mobile_sub, limits["mobile"]["sub_heading"]),
                cta=truncate(provisional_cta, limits["mobile"]["cta"]),
            ),
            sms=SMSCopy(description=truncate(sms_text, limits["sms"]["description"])),
        )


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


# Structural check: the mock must satisfy the provider contract.
_: AIProvider = MockAIProvider()
