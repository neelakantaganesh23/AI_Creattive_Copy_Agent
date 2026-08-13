"""Prompt template management (§11). Mutations are admin-only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Pagination, RequireAdmin, paginate_response
from app.core.errors import NotFoundError
from app.models.enums import Channel
from app.repositories.taxonomy_repository import TemplateRepository
from app.schemas.common import MessageResponse, Page
from app.schemas.taxonomy import TemplateCreate, TemplateResponse, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=Page[TemplateResponse], summary="List templates")
def list_templates(
    session: DbSession,
    _user: CurrentUser,
    pagination: Pagination,
    channel: Annotated[Channel | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[TemplateResponse]:
    items, total = TemplateRepository(session).list(
        offset=pagination.offset,
        limit=pagination.page_size,
        is_active=is_active,
        order_by="name",
        filters={"channel": channel.value if channel else None},
    )
    return Page[TemplateResponse].model_validate(
        paginate_response(
            [TemplateResponse.model_validate(item) for item in items], total, pagination
        )
    )


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a template",
)
def create_template(
    payload: TemplateCreate, session: DbSession, _user: RequireAdmin
) -> TemplateResponse:
    values = payload.model_dump()
    values["channel"] = payload.channel.value
    template = TemplateRepository(session).create(**values)
    session.commit()
    return TemplateResponse.model_validate(template)


@router.get("/{template_id}", response_model=TemplateResponse, summary="Template detail")
def get_template(template_id: int, session: DbSession, _user: CurrentUser) -> TemplateResponse:
    template = TemplateRepository(session).get(template_id)
    if template is None:
        raise NotFoundError("Template not found.")
    return TemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=TemplateResponse, summary="Update a template")
def update_template(
    template_id: int, payload: TemplateUpdate, session: DbSession, _user: RequireAdmin
) -> TemplateResponse:
    repo = TemplateRepository(session)
    template = repo.get(template_id)
    if template is None:
        raise NotFoundError("Template not found.")
    values = payload.model_dump(exclude_unset=True)
    if values.get("channel") is not None:
        values["channel"] = values["channel"].value
    repo.update(template, **values)
    session.commit()
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", response_model=MessageResponse, summary="Delete a template")
def delete_template(template_id: int, session: DbSession, _user: RequireAdmin) -> MessageResponse:
    repo = TemplateRepository(session)
    template = repo.get(template_id)
    if template is None:
        raise NotFoundError("Template not found.")
    repo.delete(template)
    session.commit()
    return MessageResponse(message="Template deleted.")
