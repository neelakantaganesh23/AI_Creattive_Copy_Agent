"""Pydantic AI runtime: model construction, execution and error mapping.

The only module that knows which model backs the agents. ``AI_PROVIDER=gemini``
wires the configured Gemini models; ``AI_PROVIDER=mock`` wires a
:class:`~pydantic_ai.models.function.FunctionModel` that replays deterministic
fixtures, so the whole application -- and the entire test suite -- runs with no
credentials and no network.

Model identifiers are never hard-coded: they come from ``settings`` and the
runtime refuses to start without them.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from typing import Any, Literal, TypeVar

from pydantic_ai import Agent
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits

from app.agents.types import ModelInfo
from app.core.config import settings
from app.core.errors import (
    AIInvalidOutputError,
    AINotConfiguredError,
    AIProviderError,
    AIProviderTimeoutError,
    AIQuotaExceededError,
)
from app.core.logging import get_logger

logger = get_logger("app.agents.runtime")

ModelTier = Literal["fast", "quality"]
OutputT = TypeVar("OutputT")
DepsT = TypeVar("DepsT")

MOCK_FAST_MODEL = "mock-fast"
MOCK_QUALITY_MODEL = "mock-quality"

# The mock model cannot see the typed request the agent was built from -- it only
# receives rendered prompt text. Rather than parse prompts back apart, the caller
# stashes the request here and the fixture builder reads it. Only ever consumed by
# the FunctionModel path.
_mock_request: ContextVar[Any | None] = ContextVar("mock_request", default=None)
_mock_builder: ContextVar[MockBuilder | None] = ContextVar("mock_builder", default=None)

# Builds the output payload for one mock agent call, given whatever the caller
# stashed. Returns a dict matching the agent's output schema.
MockBuilder = Callable[[Any], dict[str, Any]]


def is_mock() -> bool:
    return settings.ai_provider != "gemini"


def model_info() -> ModelInfo:
    """Which models the workflow is currently wired to."""
    if is_mock():
        return ModelInfo(name="mock", fast_model=MOCK_FAST_MODEL, quality_model=MOCK_QUALITY_MODEL)
    return ModelInfo(
        name="gemini",
        fast_model=settings.gemini_flash_model,
        quality_model=settings.gemini_pro_model,
    )


def model_name(tier: ModelTier) -> str | None:
    info = model_info()
    return info.fast_model if tier == "fast" else info.quality_model


# -- Model construction ------------------------------------------------------


def _mock_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Produce a deterministic response matching the agent's output schema."""
    builder = _mock_builder.get()
    if builder is None:  # pragma: no cover - guarded by run_agent
        raise AIProviderError("The mock runtime was invoked without a fixture builder.")
    if not info.output_tools:  # pragma: no cover - every agent uses structured output
        raise AIProviderError("The mock runtime requires an agent with structured output.")

    payload = builder(_mock_request.get())
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload)])


@lru_cache
def _build_model(tier: ModelTier) -> Model:
    if is_mock():
        logger.warning(
            "using the MOCK model runtime - generated copy is simulated, not model output",
            extra={"ai_provider": "mock", "tier": tier},
        )
        return FunctionModel(
            _mock_function, model_name=MOCK_FAST_MODEL if tier == "fast" else MOCK_QUALITY_MODEL
        )

    if not settings.gemini_api_key:
        raise AINotConfiguredError("GEMINI_API_KEY is not configured.")
    if not settings.gemini_flash_model or not settings.gemini_pro_model:
        raise AINotConfiguredError(
            "GEMINI_FLASH_MODEL and GEMINI_PRO_MODEL must both be configured."
        )

    try:
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider
    except ImportError as exc:  # pragma: no cover - depends on install extras
        raise AINotConfiguredError(
            "pydantic-ai-slim[google] is required when AI_PROVIDER=gemini."
        ) from exc

    name = settings.gemini_flash_model if tier == "fast" else settings.gemini_pro_model
    logger.info("using the Gemini model runtime", extra={"tier": tier, "model": name})
    return GoogleModel(name, provider=GoogleProvider(api_key=settings.gemini_api_key))


def reset_model_cache() -> None:
    """Clear cached models. Used by tests that swap configuration."""
    _build_model.cache_clear()


def build_agent(
    *,
    output_type: type[OutputT],
    instructions: str,
    name: str,
    deps_type: type[DepsT] = type(None),
    temperature: float | None = None,
    retries: int | None = None,
) -> Agent[DepsT, OutputT]:
    """Create an agent. The model is bound per-run so tiers stay swappable."""
    return Agent(
        output_type=output_type,
        instructions=instructions,
        name=name,
        deps_type=deps_type,
        retries=settings.agent_retries if retries is None else retries,
        model_settings=ModelSettings(
            temperature=settings.agent_temperature if temperature is None else temperature
        ),
    )


# -- Execution ---------------------------------------------------------------


@contextmanager
def _mock_scope(request: Any, builder: MockBuilder | None) -> Iterator[None]:
    request_token = _mock_request.set(request)
    builder_token = _mock_builder.set(builder)
    try:
        yield
    finally:
        _mock_request.reset(request_token)
        _mock_builder.reset(builder_token)


async def run_agent(
    agent: Agent[DepsT, OutputT],
    prompt: str,
    *,
    tier: ModelTier,
    deps: DepsT = None,
    request: Any = None,
    mock_builder: MockBuilder | None = None,
) -> OutputT:
    """Run an agent, mapping every failure onto the application's error types.

    ``request`` and ``mock_builder`` are only read by the mock runtime; on the
    Gemini path they are ignored.
    """
    model = _build_model(tier)
    limits = UsageLimits(request_limit=settings.agent_request_limit)

    if is_mock():
        await _simulate_latency()

    try:
        with _mock_scope(request, mock_builder):
            result = await asyncio.wait_for(
                agent.run(prompt, model=model, deps=deps, usage_limits=limits),
                timeout=settings.gemini_timeout_seconds,
            )
    except TimeoutError as exc:
        raise AIProviderTimeoutError() from exc
    except ModelHTTPError as exc:
        raise _map_http_error(exc) from exc
    except UsageLimitExceeded as exc:
        logger.error("agent exceeded its usage limit", extra={"agent": agent.name})
        raise AIProviderError() from exc
    except UnexpectedModelBehavior as exc:
        # Includes "exceeded max retries" when output validation keeps failing.
        logger.error(
            "agent produced unusable output",
            extra={"agent": agent.name, "reason": str(exc)[:200]},
        )
        raise AIInvalidOutputError() from exc
    except ModelAPIError as exc:
        logger.error("model call failed", extra={"agent": agent.name})
        raise AIProviderError() from exc

    return result.output


def _map_http_error(exc: ModelHTTPError) -> AIProviderError:
    status = exc.status_code
    if status == 429:
        return AIQuotaExceededError()
    if status in (401, 403):
        return AINotConfiguredError("The Gemini API key was rejected.")
    logger.error("model returned an HTTP error", extra={"status_code": status})
    return AIProviderError()


async def _simulate_latency() -> None:
    """Give the mock runtime the timing shape of a real call, for the workflow UI."""
    delay = max(settings.mock_stage_delay_ms, 0) / 1000
    if delay:
        await asyncio.sleep(delay)
