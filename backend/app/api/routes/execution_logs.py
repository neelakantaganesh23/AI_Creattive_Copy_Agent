"""Agent execution logs (§11). Admins see everything; other roles see their own runs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, Pagination, paginate_response
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.enums import AgentName, AgentStatus, Role
from app.repositories.generation_repository import (
    AgentExecutionRepository,
    GenerationRepository,
)
from app.schemas.common import Page
from app.schemas.generation import AgentExecutionResponse
from app.services.generation_service import to_agent_response

router = APIRouter(prefix="/execution-logs", tags=["Logs"])


@router.get("", response_model=Page[AgentExecutionResponse], summary="List execution logs")
def list_logs(
    session: DbSession,
    user: CurrentUser,
    pagination: Pagination,
    generation_id: Annotated[int | None, Query()] = None,
    agent_name: Annotated[AgentName | None, Query()] = None,
    log_status: Annotated[AgentStatus | None, Query(alias="status")] = None,
) -> Page[AgentExecutionResponse]:
    if generation_id is not None:
        _assert_can_read(session, generation_id, user)

    items, total = AgentExecutionRepository(session).list_logs(
        offset=pagination.offset,
        limit=pagination.page_size,
        generation_id=generation_id,
        agent_name=agent_name.value if agent_name else None,
        status=log_status.value if log_status else None,
    )
    visible = [row for row in items if _can_read(session, row.generation_id, user)]
    return Page[AgentExecutionResponse].model_validate(
        paginate_response([to_agent_response(row) for row in visible], total, pagination)
    )


@router.get("/{log_id}", response_model=AgentExecutionResponse, summary="Execution log detail")
def get_log(log_id: int, session: DbSession, user: CurrentUser) -> AgentExecutionResponse:
    row = AgentExecutionRepository(session).get(log_id)
    if row is None:
        raise NotFoundError("Execution log not found.")
    _assert_can_read(session, row.generation_id, user)
    return to_agent_response(row)


def _can_read(session, generation_id: int, user) -> bool:
    if Role(user.role) in (Role.ADMIN, Role.VIEWER):
        return True
    generation = GenerationRepository(session).get(generation_id)
    return generation is not None and generation.user_id == user.id


def _assert_can_read(session, generation_id: int, user) -> None:
    if not _can_read(session, generation_id, user):
        raise PermissionDeniedError("You do not have access to these execution logs.")
