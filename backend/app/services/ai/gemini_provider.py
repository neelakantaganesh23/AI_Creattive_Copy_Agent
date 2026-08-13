"""Google Gemini AI provider.

Model identifiers are never hard-coded: ``GEMINI_FLASH_MODEL`` (low latency, used
for extraction) and ``GEMINI_PRO_MODEL`` (higher quality, used for copy) must be
supplied through the environment, and the provider refuses to start without them.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.errors import (
    AIInvalidOutputError,
    AINotConfiguredError,
    AIProviderError,
    AIProviderTimeoutError,
    AIQuotaExceededError,
)
from app.core.logging import get_logger
from app.schemas.copy_output import CopyBundle
from app.services.ai import prompts
from app.services.ai.provider import AIProvider, CopyRequest, ExtractedBrief, ProviderInfo
from app.utils.json_parsing import JSONRepairFailed, parse_json_object

logger = get_logger("app.ai.gemini")


class GeminiAIProvider:
    """Calls Gemini through the ``google-genai`` SDK."""

    name = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise AINotConfiguredError("GEMINI_API_KEY is not configured.")
        if not settings.gemini_flash_model or not settings.gemini_pro_model:
            raise AINotConfiguredError(
                "GEMINI_FLASH_MODEL and GEMINI_PRO_MODEL must both be configured."
            )
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise AINotConfiguredError(
                "The google-genai package is required when AI_PROVIDER=gemini."
            ) from exc

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._fast_model = settings.gemini_flash_model
        self._quality_model = settings.gemini_pro_model

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name, fast_model=self._fast_model, quality_model=self._quality_model
        )

    # -- Transport -----------------------------------------------------------
    async def _generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """One structured call plus, if needed, one controlled repair attempt."""
        raw = await self._call_model(model, system_prompt, user_prompt, schema)
        try:
            return parse_json_object(raw)
        except JSONRepairFailed:
            logger.warning(
                "gemini returned unparsable JSON; attempting one repair",
                extra={"model": model},
            )

        repaired = await self._call_model(
            model,
            prompts.REPAIR_SYSTEM_PROMPT,
            f"Schema:\n{schema}\n\nMalformed response:\n{raw}",
            schema,
        )
        try:
            return parse_json_object(repaired)
        except JSONRepairFailed as exc:
            # The raw payload stays in the internal log only; the API surfaces a
            # generic message (§13).
            logger.error(
                "gemini repair attempt failed",
                extra={"model": model, "raw_length": len(raw)},
            )
            raise AIInvalidOutputError() from exc

    async def _call_model(
        self, model: str, system_prompt: str, user_prompt: str, schema: dict[str, Any]
    ) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.8,
        )
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=model, contents=user_prompt, config=config
                ),
                timeout=settings.gemini_timeout_seconds,
            )
        except TimeoutError as exc:
            raise AIProviderTimeoutError() from exc
        except Exception as exc:  # SDK raises provider-specific error types
            message = str(exc).lower()
            if "quota" in message or "resource_exhausted" in message or "429" in message:
                raise AIQuotaExceededError() from exc
            if "api key" in message or "unauthenticated" in message or "permission" in message:
                raise AINotConfiguredError("The Gemini API key was rejected.") from exc
            logger.error("gemini call failed", extra={"model": model})
            raise AIProviderError() from exc

        text = getattr(response, "text", None)
        if not text:
            raise AIInvalidOutputError("The Gemini response contained no text.")
        return text

    # -- Agent 1 -------------------------------------------------------------
    async def extract_brief(self, brief: str, *, language: str) -> ExtractedBrief:
        payload = await self._generate_json(
            model=self._fast_model,
            system_prompt=prompts.EXTRACTION_SYSTEM_PROMPT,
            user_prompt=prompts.build_extraction_prompt(brief, language),
            schema=prompts.EXTRACTION_SCHEMA,
        )
        return ExtractedBrief(
            brand=_as_optional_str(payload.get("brand")),
            products=_as_str_list(payload.get("products")),
            skus=_as_str_list(payload.get("skus")),
            athletes=_as_str_list(payload.get("athletes")),
            campaign_goal=_as_optional_str(payload.get("campaign_goal")),
            features=_as_str_list(payload.get("features")),
            tone=_as_optional_str(payload.get("tone")),
            key_message=_as_optional_str(payload.get("key_message")),
        )

    # -- Agent 3 -------------------------------------------------------------
    async def generate_copy(self, request: CopyRequest) -> CopyBundle:
        payload = await self._generate_json(
            model=self._quality_model,
            system_prompt=prompts.COPY_SYSTEM_PROMPT,
            user_prompt=prompts.build_copy_prompt(request),
            schema=prompts.COPY_SCHEMA,
        )
        return _validate_bundle(payload)

    # -- Agent 4 -------------------------------------------------------------
    async def rewrite_for_variety(
        self, request: CopyRequest, bundle: CopyBundle, repeated_phrases: list[str]
    ) -> CopyBundle:
        payload = await self._generate_json(
            model=self._quality_model,
            system_prompt=prompts.COPY_SYSTEM_PROMPT,
            user_prompt=prompts.build_rewrite_prompt(
                request, bundle.model_dump(), repeated_phrases
            ),
            schema=prompts.COPY_SCHEMA,
        )
        rewritten = _validate_bundle(payload)
        # The CTA is deterministic and must survive the rewrite untouched.
        rewritten.email.cta = bundle.email.cta
        rewritten.mobile.cta = bundle.mobile.cta
        return rewritten


def _validate_bundle(payload: dict[str, Any]) -> CopyBundle:
    try:
        return CopyBundle.model_validate(payload)
    except PydanticValidationError as exc:
        logger.error("gemini output failed schema validation", extra={"errors": exc.error_count()})
        raise AIInvalidOutputError() from exc


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_: type[AIProvider] = GeminiAIProvider  # structural conformance check
