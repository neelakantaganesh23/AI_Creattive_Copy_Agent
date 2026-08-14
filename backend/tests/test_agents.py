"""Unit tests for the individual agents, the rules engine and the judge (§18).

Every test runs on the mock model runtime, so nothing here reaches a network.
"""

from __future__ import annotations

import json

import pytest

from app.agents import mock_content, runtime
from app.agents.base import (
    AudienceData,
    BrandData,
    CTARuleData,
    NullRecorder,
    ProductData,
    WorkflowContext,
)
from app.agents.copy_generation import CopyGenerationAgent
from app.agents.cta import render_template, resolve_cta
from app.agents.extraction import DataExtractionAgent
from app.agents.orchestrator import GenerationWorkflow
from app.agents.repetition import analyse_repetition
from app.agents.rules import (
    applicable_rules,
    autofix,
    build_rule_instructions,
    evaluate_rules,
    guideline_rules,
)
from app.agents.types import ExtractedBrief, RuleData
from app.agents.validation import ContentValidationAgent
from app.core.errors import (
    AIInvalidOutputError,
    AINotConfiguredError,
    AIProviderError,
    GenerationFailedError,
    GroundingError,
)
from app.models.enums import Channel, RuleType, Severity
from app.schemas.copy_output import CopyBundle, EmailCopy, MobileCopy, SMSCopy
from app.services.ai.grounding import MockGroundingProvider, NullGroundingProvider
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


def make_rule(**overrides) -> RuleData:
    defaults = {
        "id": 1,
        "name": "test rule",
        "rule_type": RuleType.MAX_CHARS,
        "value": "80",
        "severity": Severity.ERROR,
    }
    defaults.update(overrides)
    return RuleData(**defaults)


def make_bundle(headline: str, **overrides) -> CopyBundle:
    email = {"headline": headline, "sub_heading": "A sub heading.", "cta": "SHOP NOW"}
    email.update(overrides.get("email", {}))
    return CopyBundle(
        email=EmailCopy(**email),
        mobile=MobileCopy(
            superline="NEW",
            pre_heading="Brand for everyone",
            headline=headline,
            sub_heading="A sub heading.",
            cta="SHOP NOW",
        ),
        sms=SMSCopy(description="A short promotional description."),
    )


# -- Mock runtime -----------------------------------------------------------
async def test_extraction_finds_brief_facts() -> None:
    context = build_context()
    await DataExtractionAgent().run(context, NullRecorder())
    extracted = context.extracted
    assert extracted is not None
    assert "AeroFlex Running Shoes" in extracted.products
    assert extracted.key_message == "Run lighter. Go farther. Feel unstoppable."
    assert "comfort" in extracted.features
    assert extracted.tone == "exciting"
    # No public figure is named in the brief, so none may be invented.
    assert extracted.athletes == []


def test_extraction_only_reports_explicit_people() -> None:
    brief = SAMPLE_BRIEF + " The campaign is endorsed by Jordan Blake."
    assert mock_content.structured_brief(brief, "English").athletes == ["Jordan Blake"]


async def test_generation_is_deterministic() -> None:
    first, second = build_context(), build_context()
    for context in (first, second):
        await DataExtractionAgent().run(context, NullRecorder())
        await CopyGenerationAgent().run(context, NullRecorder())

    assert first.bundle is not None and second.bundle is not None
    assert first.bundle.model_dump() == second.bundle.model_dump()
    assert first.bundle.email.headline == "Run Lighter. Go Farther. Feel Unstoppable."


# -- Rules engine -----------------------------------------------------------
def test_max_chars_rule_reports_the_actual_length() -> None:
    rule = make_rule(rule_type=RuleType.MAX_CHARS, value="10", field_name="headline")
    violations = evaluate_rules(make_bundle("x" * 25), [rule], Channel.EMAIL)
    assert len(violations) == 1
    assert violations[0].field == "headline"
    assert "25 characters" in violations[0].explanation
    assert violations[0].rule_id == 1


def test_max_words_rule_counts_words() -> None:
    rule = make_rule(rule_type=RuleType.MAX_WORDS, value="3", field_name="cta")
    bundle = make_bundle("Fine", email={"cta": "SHOP THE ENTIRE COLLECTION NOW"})
    violations = evaluate_rules(bundle, [rule], Channel.EMAIL)
    assert len(violations) == 1
    assert "5 words" in violations[0].explanation


def test_min_chars_rule_flags_short_copy() -> None:
    rule = make_rule(rule_type=RuleType.MIN_CHARS, value="50", field_name="headline")
    violations = evaluate_rules(make_bundle("Too short"), [rule], Channel.EMAIL)
    assert "minimum 50" in violations[0].explanation


def test_forbidden_terms_rule() -> None:
    rule = make_rule(rule_type=RuleType.FORBIDDEN_TERMS, value="guarantee, cheapest")
    violations = evaluate_rules(
        make_bundle("The cheapest shoe you can buy"), [rule], Channel.EMAIL
    )
    assert any("cheapest" in v.explanation for v in violations)


def test_required_terms_rule() -> None:
    rule = make_rule(
        rule_type=RuleType.REQUIRED_TERMS, value="AeroFlex", field_name="headline"
    )
    violations = evaluate_rules(make_bundle("Run lighter today"), [rule], Channel.EMAIL)
    assert "missing required wording" in violations[0].explanation


def test_regex_rule_requires_a_match() -> None:
    rule = make_rule(rule_type=RuleType.REGEX, value=r"^[A-Z]", field_name="headline")
    assert evaluate_rules(make_bundle("Capitalised"), [rule], Channel.EMAIL) == []
    assert evaluate_rules(make_bundle("lowercase"), [rule], Channel.EMAIL)


def test_invalid_rule_values_are_ignored_rather_than_crashing() -> None:
    numeric = make_rule(rule_type=RuleType.MAX_CHARS, value="not a number")
    bad_regex = make_rule(id=2, rule_type=RuleType.REGEX, value="([unclosed")
    assert evaluate_rules(make_bundle("Anything"), [numeric, bad_regex], Channel.EMAIL) == []


def test_guideline_rules_are_left_to_the_judge() -> None:
    rule = make_rule(rule_type=RuleType.GUIDELINE, value="Make it sound natural.")
    assert evaluate_rules(make_bundle("Anything"), [rule], Channel.EMAIL) == []
    assert guideline_rules([rule]) == [rule]


def test_rules_only_evaluate_the_requested_channel() -> None:
    rule = make_rule(
        rule_type=RuleType.MAX_CHARS, value="5", channel=Channel.SMS.value, field_name="description"
    )
    # The rule is scoped to SMS, so an email generation must ignore it entirely.
    assert evaluate_rules(make_bundle("A very long email headline"), [rule], Channel.EMAIL) == []


def test_a_rule_without_a_field_applies_to_every_field_of_the_channel() -> None:
    rule = make_rule(rule_type=RuleType.MAX_CHARS, value="5")
    violations = evaluate_rules(make_bundle("A long headline"), [rule], Channel.EMAIL)
    assert {v.field for v in violations} == {"headline", "sub_heading", "cta"}


def test_applicable_rules_filters_by_scope() -> None:
    everywhere = make_rule(id=1)
    other_brand = make_rule(id=2, brand_id=99)
    this_brand = make_rule(id=3, brand_id=7)
    other_channel = make_rule(id=4, channel=Channel.SMS.value)
    other_segment = make_rule(id=5, audience_segment_id=42)

    matched = applicable_rules(
        [everywhere, other_brand, this_brand, other_channel, other_segment],
        channel=Channel.EMAIL,
        brand_id=7,
        audience_segment_id=3,
    )
    assert {rule.id for rule in matched} == {1, 3}


def test_applicable_rules_orders_by_priority() -> None:
    low = make_rule(id=1, priority=10)
    high = make_rule(id=2, priority=90)
    matched = applicable_rules(
        [low, high], channel=Channel.EMAIL, brand_id=None, audience_segment_id=None
    )
    assert [rule.id for rule in matched] == [2, 1]


def test_rule_instructions_are_rendered_for_the_prompt() -> None:
    rules = [
        make_rule(id=1, rule_type=RuleType.MAX_CHARS, value="50", field_name="headline"),
        make_rule(id=2, rule_type=RuleType.MAX_WORDS, value="3", field_name="cta"),
        make_rule(id=3, rule_type=RuleType.GUIDELINE, value="Sound natural."),
    ]
    text = build_rule_instructions(rules, Channel.EMAIL)
    assert "at most 50 characters" in text
    assert "at most 3 words" in text
    assert "Sound natural." in text


def test_rule_instructions_are_empty_without_rules() -> None:
    assert build_rule_instructions([], Channel.EMAIL) == ""


def test_autofix_trims_to_the_limit() -> None:
    rules = [
        make_rule(id=1, rule_type=RuleType.MAX_CHARS, value="12", field_name="headline"),
        make_rule(id=2, rule_type=RuleType.MAX_WORDS, value="2", field_name="cta"),
    ]
    fixed = autofix(make_bundle("An extremely long headline indeed"), rules, Channel.EMAIL)
    assert len(fixed.email.headline) <= 12
    assert len(fixed.email.cta.split()) <= 2
    assert evaluate_rules(fixed, rules, Channel.EMAIL) == []


# -- Rules inside the workflow ----------------------------------------------
async def test_copy_generation_satisfies_an_active_rule() -> None:
    rule = make_rule(rule_type=RuleType.MAX_CHARS, value="30", field_name="headline")
    context = build_context(rules=[rule])
    await DataExtractionAgent().run(context, NullRecorder())
    await CopyGenerationAgent().run(context, NullRecorder())

    assert context.bundle is not None
    assert len(context.bundle.email.headline) <= 30


async def test_cta_rule_is_enforced_after_substitution() -> None:
    """A brand CTA that overruns is trimmed, not left to break the rule."""
    rule = make_rule(rule_type=RuleType.MAX_WORDS, value="2", field_name="cta")
    context = build_context(rules=[rule])
    output, _ = await GenerationWorkflow(NullGroundingProvider()).run(context, NullRecorder())
    assert len(output.email.cta.split()) <= 2


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


# -- Content validation -----------------------------------------------------
async def test_validation_records_a_verdict() -> None:
    context = build_context(rules=[make_rule(rule_type=RuleType.GUIDELINE, value="Be natural.")])
    await DataExtractionAgent().run(context, NullRecorder())
    await CopyGenerationAgent().run(context, NullRecorder())
    await ContentValidationAgent().run(context, NullRecorder())

    assert context.judge is not None
    assert context.quality.judge_score == 1.0
    assert context.quality.revisions == 0


async def test_validation_can_be_disabled(monkeypatch) -> None:
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "judge_enabled", False)
    context = build_context()
    await DataExtractionAgent().run(context, NullRecorder())
    await CopyGenerationAgent().run(context, NullRecorder())
    await ContentValidationAgent().run(context, NullRecorder())

    assert context.judge is None


async def test_a_judge_outage_does_not_lose_the_copy(monkeypatch) -> None:
    async def boom(*_args, **_kwargs):
        raise AIProviderError()

    monkeypatch.setattr("app.agents.validation.judge", boom)
    context = build_context()
    await DataExtractionAgent().run(context, NullRecorder())
    await CopyGenerationAgent().run(context, NullRecorder())
    await ContentValidationAgent().run(context, NullRecorder())

    assert context.bundle is not None
    assert context.judge is None
    assert any("validation was unavailable" in warning for warning in context.warnings)


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


# -- Runtime failures -------------------------------------------------------
def _failing_runtime(monkeypatch, error: Exception) -> None:
    """Make every model call fail, standing in for a provider outage."""

    async def boom(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(runtime, "run_agent", boom)


async def test_workflow_surfaces_provider_errors(monkeypatch) -> None:
    _failing_runtime(monkeypatch, AIProviderError())
    with pytest.raises(AIProviderError):
        await GenerationWorkflow(NullGroundingProvider()).run(build_context(), NullRecorder())


async def test_workflow_wraps_unexpected_errors(monkeypatch) -> None:
    _failing_runtime(monkeypatch, RuntimeError("boom"))
    with pytest.raises(GenerationFailedError):
        await GenerationWorkflow(NullGroundingProvider()).run(build_context(), NullRecorder())


async def test_workflow_reports_invalid_ai_output(monkeypatch) -> None:
    _failing_runtime(monkeypatch, AIInvalidOutputError())
    with pytest.raises(AIInvalidOutputError):
        await GenerationWorkflow(NullGroundingProvider()).run(build_context(), NullRecorder())


async def test_workflow_completes_with_the_mock_runtime() -> None:
    workflow = GenerationWorkflow(NullGroundingProvider())
    output, duration_ms = await workflow.run(build_context(), NullRecorder())
    assert output.email.cta == "SHOP AEROFLEX RUNNING SHOES"
    assert output.grounded is False
    assert output.provider == "mock"
    assert duration_ms >= 0


# -- Tavily grounding -------------------------------------------------------
def _tavily_provider(monkeypatch, handler):
    """Build a Tavily provider whose HTTP calls hit a mock transport."""
    import httpx

    from app.core.config import settings as app_settings
    from app.services.ai import grounding as grounding_module

    monkeypatch.setattr(app_settings, "tavily_api_key", "tvly-test-key")

    real_client = httpx.AsyncClient

    def fake_client(*_args, **kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(grounding_module.httpx, "AsyncClient", fake_client)
    return grounding_module.TavilyGroundingProvider()


async def test_tavily_grounding_returns_sources(monkeypatch) -> None:
    import httpx

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "AeroFlex review",
                        "url": "https://example.com/aeroflex",
                        "content": "A running shoe overview.",
                    },
                    {"title": "No url entry"},
                ]
            },
        )

    provider = _tavily_provider(monkeypatch, handler)
    result = await provider.search(
        ExtractedBrief(brand="AeroFlex", products=["AeroFlex Running Shoes"]), brief=SAMPLE_BRIEF
    )

    assert result.grounded is True
    assert len(result.sources) == 1
    assert result.sources[0].url == "https://example.com/aeroflex"
    assert result.sources[0].source_type == "tavily"
    assert captured["auth"] == "Bearer tvly-test-key"
    # Entities are combined into a single billed search.
    assert "AeroFlex Running Shoes" in captured["body"]["query"]


async def test_tavily_grounding_reports_quota_exhaustion(monkeypatch) -> None:
    import httpx

    provider = _tavily_provider(
        monkeypatch, lambda _request: httpx.Response(429, json={"detail": "quota"})
    )
    with pytest.raises(GroundingError, match="quota has been exhausted"):
        await provider.search(ExtractedBrief(products=["AeroFlex"]), brief=SAMPLE_BRIEF)


async def test_tavily_grounding_reports_bad_key(monkeypatch) -> None:
    import httpx

    provider = _tavily_provider(monkeypatch, lambda _request: httpx.Response(401, json={}))
    with pytest.raises(GroundingError, match="key was rejected"):
        await provider.search(ExtractedBrief(products=["AeroFlex"]), brief=SAMPLE_BRIEF)


async def test_tavily_grounding_skips_when_nothing_to_search(monkeypatch) -> None:
    import httpx

    def handler(_request: httpx.Request) -> httpx.Response:  # pragma: no cover - not called
        raise AssertionError("no request should be made without entities")

    provider = _tavily_provider(monkeypatch, handler)
    result = await provider.search(ExtractedBrief(), brief=SAMPLE_BRIEF)
    assert result.grounded is False
    assert result.sources == []


def test_tavily_requires_an_api_key(monkeypatch) -> None:
    from app.core.config import settings as app_settings
    from app.services.ai.grounding import TavilyGroundingProvider

    monkeypatch.setattr(app_settings, "tavily_api_key", None)
    with pytest.raises(AINotConfiguredError, match="TAVILY_API_KEY"):
        TavilyGroundingProvider()
