"""Web search grounding providers (§12, Agent 2).

Grounding sits behind its own interface so the search backend can be swapped. When
grounding is disabled or fails, the workflow continues from the brief alone and the
generation is explicitly labelled as not externally grounded.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Protocol

import httpx

from app.agents.types import ExtractedBrief, GroundingResult, GroundingSourceData
from app.core.config import settings
from app.core.errors import AINotConfiguredError, GroundingError
from app.core.logging import get_logger

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


class TavilyGroundingProvider:
    """Grounds via the Tavily search API.

    One HTTP request per generation: the extracted entities are combined into a
    single query, because Tavily bills per search.
    """

    name = "tavily"

    def __init__(self) -> None:
        if not settings.tavily_api_key:
            raise AINotConfiguredError(
                "TAVILY_API_KEY is required when GROUNDING_PROVIDER=tavily."
            )
        self._api_key = settings.tavily_api_key

    async def search(self, extracted: ExtractedBrief, *, brief: str) -> GroundingResult:
        queries = _build_queries(extracted)
        if not queries:
            return GroundingResult(
                grounded=False, notes=["No groundable entities were found in the brief."]
            )

        query = " ".join(queries[:3])
        payload = {
            "query": query,
            "max_results": settings.tavily_max_results,
            "search_depth": settings.tavily_search_depth,
            "include_answer": False,
            "include_raw_content": False,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.tavily_timeout_seconds) as client:
                response = await client.post(
                    settings.tavily_api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            reason = _classify_tavily_status(exc.response.status_code)
            logger.warning(
                "tavily grounding failed",
                extra={"status_code": exc.response.status_code, "reason": reason},
            )
            raise GroundingError(reason) from exc
        except httpx.TimeoutException as exc:
            raise GroundingError("The grounded search request timed out.") from exc
        except httpx.HTTPError as exc:
            logger.warning("tavily grounding request failed")
            raise GroundingError(
                "Grounded search could not be reached; the copy is based on the brief only."
            ) from exc

        sources = [
            GroundingSourceData(
                title=str(item.get("title") or item.get("url") or "Untitled source")[:300],
                url=str(item["url"])[:1000],
                source_type="tavily",
                # Tavily returns an extracted snippet per result in "content".
                snippet=(str(item["content"])[:800] if item.get("content") else None),
            )
            for item in (data.get("results") or [])
            if item.get("url")
        ]

        logger.info(
            "tavily grounding completed",
            extra={"query_terms": len(queries[:3]), "source_count": len(sources)},
        )
        return GroundingResult(
            grounded=bool(sources),
            sources=sources[:8],
            notes=[] if sources else ["The search returned no citable sources."],
        )


def _classify_tavily_status(status_code: int) -> str:
    if status_code in (401, 403):
        return "The Tavily API key was rejected."
    if status_code == 429:
        return (
            "The Tavily search quota has been exhausted. Copy was generated from the brief "
            "alone. Try again later or set GROUNDING_ENABLED=false."
        )
    if status_code >= 500:
        return "The Tavily search service is unavailable; the copy is based on the brief only."
    return "Grounded search failed; the copy is based on the brief only."


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
            reason = _classify(exc)
            # The reason reaches the workflow stepper, so it has to be actionable.
            logger.warning(
                "gemini grounding failed",
                extra={"model": self._model, "reason": reason},
            )
            raise GroundingError(reason) from exc

        sources = _extract_sources(response)
        return GroundingResult(
            grounded=bool(sources),
            sources=sources,
            notes=[] if sources else ["The search returned no citable sources."],
        )


def _classify(exc: Exception) -> str:
    """Turn a provider exception into a message the user can act on.

    Grounded search is metered separately from plain generation, so quota
    exhaustion here is common and needs to be distinguishable from a real fault.
    """
    message = str(exc).lower()
    if "quota" in message or "resource_exhausted" in message or "429" in message:
        return (
            "The search grounding quota has been exhausted. Copy was generated from the "
            "brief alone. Try again later or set GROUNDING_ENABLED=false."
        )
    if "api key" in message or "unauthenticated" in message or "permission" in message:
        return "The Gemini API key was rejected for grounded search."
    if "not found" in message or "404" in message:
        return f"The model {settings.gemini_flash_model!r} does not support grounded search."
    if "timeout" in message or isinstance(exc, TimeoutError):
        return "The grounded search request timed out."
    return "Grounded search failed; the copy is based on the brief only."


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
    if settings.grounding_provider == "tavily":
        return TavilyGroundingProvider()
    return GeminiGroundingProvider()


def now_utc() -> datetime:
    return datetime.now(UTC)
