"""Unit tests for the individual agents and the provider abstraction (§18)."""

from __future__ import annotations

import pytest

from app.agents.base import (
    AudienceData,
    BrandData,
    CTARuleData,
    NullRecorder,
    ProductData,
    WorkflowContext,
)
from app.agents.cta import render_template, resolve_cta
from app.agents.orchestrator import GenerationWorkflow
from app.agents.repetition import analyse_repetition
from app.core.errors import AIInvalidOutputError, AIProviderError, GenerationFailedError
from app.models.enums import Channel
from app.schemas.copy_output import CopyBundle, EmailCopy, MobileCopy, SMSCopy
from app.services.ai.grounding import MockGroundingProvider, NullGroundingProvider
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.provider import CopyRequest, ExtractedBrief, GroundingResult, ProviderInfo
from app.utils.json_parsing import JSONRepairFailed, parse_json_object
from tests.conftest import SAMPLE_BRIEF


def build_context(**overrides) -> WorkflowContext:
    defaults = {
        "generation_id": 1,
        "brief": SAMPLE_BRIEF,
        "channel": Channel.EMAIL,
        "language": "English",
        "brand": BrandData(id=1, name="AeroFlex"),
        "product": ProductData(
            id=1, name="AeroFlex Running Shoes", features=["speed", "comfort"]
        ),
        "audience": AudienceData(id=3, name="Performance Seekers"),
        "cta_rules": [
            CTARuleData(id=1, template="SHOP {product}", priority=100),
            CTARuleData(id=2, template="EXPLORE {brand}", priority=50),
            CTARuleData(id=3, template="SHOP THE COLLECTION", priority=10),
        ],
    }
    defaults.update(overrides)
    return WorkflowContext(**defaults)


# -- Mock provider ----------------------------------------------------------
async def test_mock_extraction_finds_brief_facts() -> None:
    extracted = await MockAIProvider().extract_brief(SAMPLE_BRIEF, language="English")
    assert "AeroFlex Running Shoes" in extracted.products
    assert extracted.key_message == "Run lighter. Go farther. Feel unstoppable."
    assert "comfort" in extracted.features
    assert extracted.tone == "exciting"
    # No public figure is named in the brief, so none may be invented.
    assert extracted.athletes == []


async def test_mock_extraction_only_reports_explicit_people() -> None:
    brief = SAMPLE_BRIEF + " The campaign is endorsed by Jordan Blake."
    extracted = await MockAIProvider().extract_brief(brief, language="English")
    assert extracted.athletes == ["Jordan Blake"]


async def test_mock_generation_is_deterministic() -> None:
    provider = MockAIProvider()
    extracted = await provider.extract_brief(SAMPLE_BRIEF, language="English")
    request = CopyRequest(
        brief=SAMPLE_BRIEF,
        channel=Channel.EMAIL,
        language="English",
        extracted=extracted,
        grounding=GroundingResult(),
        audience_name="Performance Seekers",
        product_name="AeroFlex Running Shoes",
        brand_name="AeroFlex",
    )
    first = await provider.generate_copy(request)
    second = await provider.generate_copy(request)
    assert first.model_dump() == second.model_dump()
    assert first.email.headline == "Run Lighter. Go Farther. Feel Unstoppable."


# -- CTA rules --------------------------------------------------------------
def test_cta_prefers_the_product_rule() -> None:
    cta, rule_id = resolve_cta(build_context())
    assert cta == "SHOP AEROFLEX RUNNING SHOES"
    assert rule_id == 1


def test_cta_falls_back_to_the_brand_rule() -> None:
    cta, rule_id = resolve_cta(build_context(product=None))
    assert cta == "EXPLORE AEROFLEX"
    assert rule_id == 2


def test_cta_falls_back_to_the_collection() -> None:
    cta, rule_id = resolve_cta(build_context(brand=None, product=None))
    assert cta == "SHOP THE COLLECTION"
    assert rule_id == 3


def test_cta_respects_a_channel_specific_rule() -> None:
    context = build_context(
        cta_rules=[
            CTARuleData(id=1, template="SHOP {product}", priority=100),
            CTARuleData(id=9, template="TAP TO SHOP {product}", priority=200, channel="email"),
        ]
    )
    cta, rule_id = resolve_cta(context)
    assert cta == "TAP TO SHOP AEROFLEX RUNNING SHOES"
    assert rule_id == 9


def test_cta_works_with_an_empty_rule_table() -> None:
    cta, rule_id = resolve_cta(build_context(cta_rules=[]))
    assert cta == "SHOP AEROFLEX RUNNING SHOES"
    assert rule_id is None


def test_render_template_skips_unresolvable_placeholders() -> None:
    assert render_template("SHOP {product}", {"product": None}) is None
    assert render_template("SHOP {product}", {"product": "Trail Pro"}) == "SHOP TRAIL PRO"


# -- Repetition -------------------------------------------------------------
def make_bundle(headline: str) -> CopyBundle:
    return CopyBundle(
        email=EmailCopy(headline=headline, sub_heading="A sub heading.", cta="SHOP NOW"),
        mobile=MobileCopy(
            superline="NEW",
            pre_heading="Brand for everyone",
            headline=headline,
            sub_heading="A sub heading.",
            cta="SHOP NOW",
        ),
        sms=SMSCopy(description="A short promotional description."),
    )


def test_repetition_scores_zero_without_history() -> None:
    score, phrases = analyse_repetition(make_bundle("Run lighter today"), [])
    assert score == 0.0
    assert phrases == []


def test_repetition_detects_reused_phrases() -> None:
    previous = ["Run lighter and go farther with every stride"]
    score, phrases = analyse_repetition(
        make_bundle("Run lighter and go farther with every stride"), previous
    )
    assert score > 0.9
    assert any("run lighter and go farther" in phrase for phrase in phrases)


# -- Grounding --------------------------------------------------------------
async def test_null_grounding_reports_not_grounded() -> None:
    result = await NullGroundingProvider().search(ExtractedBrief(), brief=SAMPLE_BRIEF)
    assert result.grounded is False
    assert result.sources == []


async def test_mock_grounding_returns_sources_for_known_entities() -> None:
    extracted = ExtractedBrief(brand="AeroFlex", products=["AeroFlex Running Shoes"])
    result = await MockGroundingProvider().search(extracted, brief=SAMPLE_BRIEF)
    assert result.grounded is True
    assert result.sources


# -- JSON repair ------------------------------------------------------------
def test_parse_json_object_handles_code_fences() -> None:
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_object_handles_surrounding_prose() -> None:
    assert parse_json_object('Here you go: {"a": 1} Hope that helps!') == {"a": 1}


def test_parse_json_object_repairs_trailing_commas() -> None:
    assert parse_json_object('{"a": 1,}') == {"a": 1}


def test_parse_json_object_raises_when_unrecoverable() -> None:
    with pytest.raises(JSONRepairFailed):
        parse_json_object("not json at all")


# -- Provider failures ------------------------------------------------------
class FailingProvider:
    """Stands in for a provider outage."""

    name = "failing"

    def __init__(self, error: Exception) -> None:
        self._error = error

    def info(self) -> ProviderInfo:
        return ProviderInfo(name=self.name)

    async def extract_brief(self, brief: str, *, language: str):
        raise self._error

    async def generate_copy(self, request):  # pragma: no cover - never reached
        raise self._error

    async def rewrite_for_variety(self, request, bundle, repeated_phrases):
        raise self._error  # pragma: no cover - never reached


async def test_workflow_surfaces_provider_errors() -> None:
    workflow = GenerationWorkflow(FailingProvider(AIProviderError()), NullGroundingProvider())
    with pytest.raises(AIProviderError):
        await workflow.run(build_context(), NullRecorder())


async def test_workflow_wraps_unexpected_errors() -> None:
    workflow = GenerationWorkflow(
        FailingProvider(RuntimeError("boom")), NullGroundingProvider()
    )
    with pytest.raises(GenerationFailedError):
        await workflow.run(build_context(), NullRecorder())


async def test_workflow_reports_invalid_ai_output() -> None:
    workflow = GenerationWorkflow(
        FailingProvider(AIInvalidOutputError()), NullGroundingProvider()
    )
    with pytest.raises(AIInvalidOutputError):
        await workflow.run(build_context(), NullRecorder())


async def test_workflow_completes_with_the_mock_provider() -> None:
    workflow = GenerationWorkflow(MockAIProvider(), NullGroundingProvider())
    output, duration_ms = await workflow.run(build_context(), NullRecorder())
    assert output.email.cta == "SHOP AEROFLEX RUNNING SHOES"
    assert output.grounded is False
    assert duration_ms >= 0
