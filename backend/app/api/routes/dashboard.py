"""Dashboard routes (§11)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.dashboard import DashboardRecent, DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary, summary="Headline metrics")
def summary(session: DbSession, user: CurrentUser) -> DashboardSummary:
    return DashboardService(session).summary(user)


@router.get("/recent", response_model=DashboardRecent, summary="Recent generations")
def recent(
    session: DbSession,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=25)] = 5,
) -> DashboardRecent:
    return DashboardRecent(items=DashboardService(session).recent(user, limit=limit))
