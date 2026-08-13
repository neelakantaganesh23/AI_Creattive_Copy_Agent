"""Health, readiness and non-secret runtime information (§22)."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.common import SystemInfo
from app.services.ai.factory import get_ai_provider, get_grounding_provider

logger = get_logger("app.api.system")

router = APIRouter(tags=["System"])


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/ready", summary="Readiness probe")
def ready(session: DbSession, response: Response) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("readiness check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "error"}
    return {"status": "ready", "database": "ok"}


@router.get("/system/info", response_model=SystemInfo, summary="Runtime configuration")
def system_info(_user: CurrentUser) -> SystemInfo:
    """Non-secret configuration for the Settings screen. Never exposes API keys."""
    provider = get_ai_provider()
    return SystemInfo(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.app_env,
        ai_provider=provider.name,
        grounding_enabled=settings.grounding_enabled,
        grounding_provider=get_grounding_provider().name,
        models=provider.info().as_dict(),
        channel_limits=settings.channel_limits,
    )
