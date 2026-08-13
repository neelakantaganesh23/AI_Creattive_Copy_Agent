"""Web search grounding providers (§12, Agent 2).

Grounding sits behind its own interface so the search backend can be swapped. When
grounding is disabled or fails, the workflow continues from the brief alone and the
generation is explicitly labelled as not externally grounded.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Protocol

from app.core.config import settings
from app.core.errors import AINotConfiguredError, GroundingError
from app.core.logging import get_logger
from app.services.ai.provider import ExtractedBrief, GroundingResult, GroundingSourceData

logger = get_logger("app.ai.grounding")


class GroundingProvider(Protocol):
    name: str

    async def search(self, extracted: ExtractedBrief, *, brief: str) -> GroundingResult: ...


class NullGroundingProvider:
    """Used when grounding is disabled. Returns no sources and never fails."""

    name = "none"

    async def search(self, extracted: ExtractedBrief, *, brief: str) -> GroundingResult:
        return GroundingResult(
            grounded=False,
            sources=[],
            notes=["Grounding is disabled; copy is based on the supplied brief only."],
        )


class MockGroundingProvider:
    """Deterministic stand-in for local development and tests."""

    name = "mock"

    async def search(self, extracted: ExtractedBrief, *, brief: str) -> GroundingResult:
        await asyncio.sleep(max(settings.mock_stage_delay_ms, 0) / 1000)
        queries = _build_queries(extracted)
        if not queries:
            return GroundingResult(
                grounded=False,
                notes=["No groundable entities were found in the brief."],
            )
        sources = [
            GroundingSourceData(
                title=f"{query} - category overview",
                url=f"https://example.com/research/{_slug(query)}",
                source_type="mock",
                snippet=(
                    f"Simulated research context for '{query}'. Mock grounding never "
                    "introduces factual claims into the generated copy."
                ),
            )
            for query in queries[:3]
        ]
        logger.info("mock grounding completed", extra={"queries": len(queries)})
        return GroundingResult(grounded=True, sources=sources, notes=[])


class GeminiGroundingProvider:
    """Grounds via Gemini's Google Search tool."""

    name = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key or not settings.gemini_flash_model:
            raise AINotConfiguredError(
                "GEMINI_API_KEY and GEMINI_FLASH_MODEL are required for Gemini grounding."
            )
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise AINotConfiguredError(
                "The google-genai package is required for Gemini grounding."
            ) from exc
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_flash_model

    async def search(self, extracted: ExtractedBrief, *, brief: str) -> GroundingResult:
        from google.genai import types

        queries = _build_queries(extracted)
        if not queries:
            return GroundingResult(
                grounded=False, notes=["No groundable entities were found in the brief."]
            )

        prompt = (
            "Summarise verifiable public context for the following marketing entities. "
            "State only facts you can source. Entities: " + "; ".join(queries)
        )
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                ),
                timeout=settings.gemini_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("gemini grounding failed", extra={"model": self._model})
            raise GroundingError() from exc

        sources = _extract_sources(response)
        return GroundingResult(
            grounded=bool(sources),
            sources=sources,
            notes=[] if sources else ["The search returned no citable sources."],
        )


def _extract_sources(response: object) -> list[GroundingSourceData]:
    """Pull citation metadata out of a Gemini grounded response, defensively."""
    sources: list[GroundingSourceData] = []
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        metadata = getattr(candidate, "grounding_metadata", None)
        for chunk in getattr(metadata, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            uri = getattr(web, "uri", None)
            if not uri:
                continue
            sources.append(
                GroundingSourceData(
                    title=getattr(web, "title", None) or uri,
                    url=uri,
                    source_type="web",
                )
            )
    # De-duplicate by URL while preserving order.
    seen: set[str] = set()
    unique: list[GroundingSourceData] = []
    for source in sources:
        if source.url not in seen:
            seen.add(source.url)
            unique.append(source)
    return unique[:8]


def _build_queries(extracted: ExtractedBrief) -> list[str]:
    """Only search for entities the extraction step actually identified."""
    queries: list[str] = []
    queries.extend(extracted.products)
    if extracted.brand and extracted.brand not in queries:
        queries.append(extracted.brand)
    queries.extend(extracted.athletes)
    return [query for query in dict.fromkeys(queries) if len(query) > 2]


def _slug(value: str) -> str:
    return "-".join(part.lower() for part in value.split() if part.isalnum() or part.isalpha())


def build_grounding_provider() -> GroundingProvider:
    """Select the grounding provider from configuration."""
    if not settings.grounding_enabled or settings.grounding_provider == "none":
        return NullGroundingProvider()
    if settings.grounding_provider == "mock":
        return MockGroundingProvider()
    return GeminiGroundingProvider()


def now_utc() -> datetime:
    return datetime.now(UTC)
