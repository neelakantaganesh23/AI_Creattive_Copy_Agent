"""Audience segment management (§11). Mutations are admin-only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Pagination, RequireAdmin, paginate_response
from app.core.errors import ConflictError, NotFoundError
from app.repositories.taxonomy_repository import AudienceSegmentRepository
from app.schemas.common import MessageResponse, Page
from app.schemas.taxonomy import (
    AudienceSegmentCreate,
    AudienceSegmentResponse,
    AudienceSegmentUpdate,
)

router = APIRouter(prefix="/audience-segments", tags=["Audience segments"])


@router.get("", response_model=Page[AudienceSegmentResponse], summary="List audience segments")
def list_segments(
    session: DbSession,
    _user: CurrentUser,
    pagination: Pagination,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[AudienceSegmentResponse]:
    items, total = AudienceSegmentRepository(session).list(
        offset=pagination.offset,
        limit=pagination.page_size,
        is_active=is_active,
        order_by="id",
    )
    return Page[AudienceSegmentResponse].model_validate(
        paginate_response(
            [AudienceSegmentResponse.model_validate(item) for item in items], total, pagination
        )
    )


@router.post(
    "",
    response_model=AudienceSegmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an audience segment",
)
def create_segment(
    payload: AudienceSegmentCreate, session: DbSession, _user: RequireAdmin
) -> AudienceSegmentResponse:
    repo = AudienceSegmentRepository(session)
    if repo.get_by_name(payload.name):
        raise ConflictError("An audience segment with this name already exists.")
    segment = repo.create(**payload.model_dump())
    session.commit()
    return AudienceSegmentResponse.model_validate(segment)


@router.get(
    "/{segment_id}", response_model=AudienceSegmentResponse, summary="Audience segment detail"
)
def get_segment(
    segment_id: int, session: DbSession, _user: CurrentUser
) -> AudienceSegmentResponse:
    segment = AudienceSegmentRepository(session).get(segment_id)
    if segment is None:
        raise NotFoundError("Audience segment not found.")
    return AudienceSegmentResponse.model_validate(segment)


@router.put(
    "/{segment_id}", response_model=AudienceSegmentResponse, summary="Update an audience segment"
)
def update_segment(
    segment_id: int,
    payload: AudienceSegmentUpdate,
    session: DbSession,
    _user: RequireAdmin,
) -> AudienceSegmentResponse:
    repo = AudienceSegmentRepository(session)
    segment = repo.get(segment_id)
    if segment is None:
        raise NotFoundError("Audience segment not found.")
    values = payload.model_dump(exclude_unset=True)
    if "name" in values:
        existing = repo.get_by_name(values["name"])
        if existing and existing.id != segment_id:
            raise ConflictError("An audience segment with this name already exists.")
    repo.update(segment, **values)
    session.commit()
    return AudienceSegmentResponse.model_validate(segment)


@router.delete(
    "/{segment_id}", response_model=MessageResponse, summary="Delete an audience segment"
)
def delete_segment(segment_id: int, session: DbSession, _user: RequireAdmin) -> MessageResponse:
    repo = AudienceSegmentRepository(session)
    segment = repo.get(segment_id)
    if segment is None:
        raise NotFoundError("Audience segment not found.")
    repo.delete(segment)
    session.commit()
    return MessageResponse(message="Audience segment deleted.")
