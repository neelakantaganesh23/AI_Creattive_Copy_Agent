"""Image generation providers.

Mirrors ``app.services.ai.grounding``: image generation sits behind its own
interface so the backend can be swapped independently of the text model.
``IMAGE_PROVIDER`` is a separate setting from ``AI_PROVIDER`` -- Gemini can
write the copy while Stability generates the image, e.g. when Gemini's image
quota is unavailable but its text quota is fine.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

import httpx

from app.agents.types import GeneratedImage
from app.core.config import settings
from app.core.errors import (
    AINotConfiguredError,
    AIProviderError,
    AIProviderTimeoutError,
    AIQuotaExceededError,
)
from app.core.logging import get_logger

logger = get_logger("app.ai.image_generation")


class ImageProvider(Protocol):
    name: str

    async def generate(self, prompt: str) -> GeneratedImage: ...


class MockImageProvider:
    """Deterministic placeholder, used for local development and tests."""

    name = "mock"

    async def generate(self, prompt: str) -> GeneratedImage:
        delay = max(settings.mock_stage_delay_ms, 0) / 1000
        if delay:
            await asyncio.sleep(delay)

        from app.agents import mock_content

        return mock_content.generate_placeholder_image(prompt)


class GeminiImageProvider:
    """Delegates to the Pydantic AI Gemini image agent in ``app.agents.runtime``."""

    name = "gemini"

    async def generate(self, prompt: str) -> GeneratedImage:
        from app.agents.runtime import generate_image_via_gemini

        return await generate_image_via_gemini(prompt)


class StabilityImageProvider:
    """Generates via the Stability AI ``stable-image/generate/core`` endpoint."""

    name = "stability"

    def __init__(self) -> None:
        if not settings.stability_api_key:
            raise AINotConfiguredError(
                "STABILITY_API_KEY is required when IMAGE_PROVIDER=stability."
            )
        self._api_key = settings.stability_api_key

    async def generate(self, prompt: str) -> GeneratedImage:
        media_type = f"image/{settings.stability_output_format}"
        try:
            async with httpx.AsyncClient(timeout=settings.stability_timeout_seconds) as client:
                response = await client.post(
                    settings.stability_api_url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        # Stability requires the literal wildcard here; the actual
                        # format returned is controlled by the "output_format"
                        # form field below, not this header.
                        "accept": "image/*",
                    },
                    # Stability requires multipart/form-data even though every
                    # field here is a plain string; an empty files entry is the
                    # standard way to force httpx to encode the request that way.
                    files={"none": ""},
                    data={
                        "prompt": prompt,
                        "output_format": settings.stability_output_format,
                        "aspect_ratio": settings.image_aspect_ratio,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise _map_stability_status(exc.response.status_code) from exc
        except httpx.TimeoutException as exc:
            raise AIProviderTimeoutError() from exc
        except httpx.HTTPError as exc:
            logger.warning("stability image request failed")
            raise AIProviderError() from exc

        logger.info("stability image generated", extra={"bytes": len(response.content)})
        return GeneratedImage(data=response.content, media_type=media_type)


def _map_stability_status(status_code: int) -> AIProviderError:
    if status_code == 429:
        return AIQuotaExceededError()
    if status_code in (401, 403):
        return AINotConfiguredError("The Stability API key was rejected.")
    logger.warning("stability image request failed", extra={"status_code": status_code})
    return AIProviderError()


def build_image_provider() -> ImageProvider:
    if settings.image_provider == "stability":
        return StabilityImageProvider()
    if settings.image_provider == "gemini":
        return GeminiImageProvider()
    return MockImageProvider()
