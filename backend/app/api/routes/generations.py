"""Generation routes (§11)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.deps import (
    CurrentUser,
    DbSession,
    Pagination,
    RequireEditor,
    generation_rate_limit,
    paginate_response,
    test_email_rate_limit,
)
from app.core.logging import get_logger
from app.models.enums import Channel, GenerationStatus
from app.schemas.common import MessageResponse, Page
from app.schemas.generation import (
    GenerationCreate,
    GenerationDetail,
    GenerationStatusResponse,
    GenerationSummary,
)
from app.services.generation_service import GenerationService, to_detail, to_summary

logger = get_logger("app.api.generations")

router = APIRouter(prefix="/generations", tags=["Generations"])


async def _run_generation(generation_id: int) -> None:
    """Background entry point; owns its own session."""
    from app.database.session import SessionLocal

    session = SessionLocal()
    try:
        await GenerationService(session).run_workflow(generation_id)
    finally:
        session.close()


@router.post(
    "",
    response_model=GenerationDetail,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a copy generation",
)
def create_generation(
    payload: GenerationCreate,
    background_tasks: BackgroundTasks,
    session: DbSession,
    user: RequireEditor,
    _: Annotated[None, Depends(generation_rate_limit)],
) -> GenerationDetail:
    """Queue a generation and return it immediately.

    The workflow runs in the background; the client polls
    ``GET /generations/{id}/status`` for stage-by-stage progress.
    """
    service = GenerationService(session)
    generation = service.create(payload, user)
    background_tasks.add_task(_run_generation, generation.id)
    return to_detail(service.get_for_user(generation.id, user))


@router.get("", response_model=Page[GenerationSummary], summary="List generations")
def list_generations(
    session: DbSession,
    user: CurrentUser,
    pagination: Pagination,
    channel: Annotated[Channel | None, Query()] = None,
    generation_status: Annotated[GenerationStatus | None, Query(alias="status")] = None,
    audience_segment_id: Annotated[int | None, Query()] = None,
    brand_id: Annotated[int | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> Page[GenerationSummary]:
    items, total = GenerationService(session).list_for_user(
        user,
        offset=pagination.offset,
        limit=pagination.page_size,
        channel=channel.value if channel else None,
        status=generation_status.value if generation_status else None,
        audience_segment_id=audience_segment_id,
        brand_id=brand_id,
        search=search,
    )
    return Page[GenerationSummary].model_validate(
        paginate_response([to_summary(item) for item in items], total, pagination)
    )


@router.get("/{generation_id}", response_model=GenerationDetail, summary="Generation detail")
def get_generation(generation_id: int, session: DbSession, user: CurrentUser) -> GenerationDetail:
    return to_detail(GenerationService(session).get_for_user(generation_id, user))


@router.get(
    "/{generation_id}/status",
    response_model=GenerationStatusResponse,
    summary="Workflow progress",
)
def get_generation_status(
    generation_id: int, session: DbSession, user: CurrentUser
) -> GenerationStatusResponse:
    return GenerationService(session).status(generation_id, user)


@router.post(
    "/{generation_id}/regenerate",
    response_model=GenerationDetail,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerate from an existing brief",
)
def regenerate(
    generation_id: int,
    background_tasks: BackgroundTasks,
    session: DbSession,
    user: RequireEditor,
    _: Annotated[None, Depends(generation_rate_limit)],
) -> GenerationDetail:
    service = GenerationService(session)
    generation = service.regenerate(generation_id, user)
    background_tasks.add_task(_run_generation, generation.id)
    return to_detail(service.get_for_user(generation.id, user))


@router.delete(
    "/{generation_id}", response_model=MessageResponse, summary="Delete a generation"
)
def delete_generation(
    generation_id: int, session: DbSession, user: RequireEditor
) -> MessageResponse:
    GenerationService(session).delete(generation_id, user)
    return MessageResponse(message="Generation deleted.")


@router.post(
    "/{generation_id}/send-test-email",
    response_model=MessageResponse,
    summary="Send the Email-channel copy to your own inbox",
)
async def send_test_email(
    generation_id: int,
    session: DbSession,
    user: RequireEditor,
    _: Annotated[None, Depends(test_email_rate_limit)],
) -> MessageResponse:
    """Self-test-send only: always mails the requesting user's own address.

    There is no recipient field on this request -- the product does not send
    marketing email to third parties (§25).
    """
    await GenerationService(session).send_test_email(generation_id, user)
    return MessageResponse(message=f"Test email sent to {user.email}.")
