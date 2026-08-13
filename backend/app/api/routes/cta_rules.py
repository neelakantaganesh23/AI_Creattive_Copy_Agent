"""CTA rule management (§11). Mutations are admin-only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Pagination, RequireAdmin, paginate_response
from app.core.errors import NotFoundError, ValidationError
from app.repositories.taxonomy_repository import (
    BrandRepository,
    CTARuleRepository,
    ProductRepository,
)
from app.schemas.common import MessageResponse, Page
from app.schemas.taxonomy import CTARuleCreate, CTARuleResponse, CTARuleUpdate

router = APIRouter(prefix="/cta-rules", tags=["CTA rules"])


def _validate_references(session, brand_id: int | None, product_id: int | None) -> None:
    if brand_id is not None and BrandRepository(session).get(brand_id) is None:
        raise ValidationError("The referenced brand does not exist.")
    if product_id is not None and ProductRepository(session).get(product_id) is None:
        raise ValidationError("The referenced product does not exist.")


@router.get("", response_model=Page[CTARuleResponse], summary="List CTA rules")
def list_rules(
    session: DbSession,
    _user: CurrentUser,
    pagination: Pagination,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[CTARuleResponse]:
    items, total = CTARuleRepository(session).list(
        offset=pagination.offset,
        limit=pagination.page_size,
        is_active=is_active,
        order_by="priority",
        descending=True,
    )
    return Page[CTARuleResponse].model_validate(
        paginate_response(
            [CTARuleResponse.model_validate(item) for item in items], total, pagination
        )
    )


@router.post(
    "",
    response_model=CTARuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a CTA rule",
)
def create_rule(
    payload: CTARuleCreate, session: DbSession, _user: RequireAdmin
) -> CTARuleResponse:
    _validate_references(session, payload.brand_id, payload.product_id)
    values = payload.model_dump()
    values["channel"] = payload.channel.value if payload.channel else None
    rule = CTARuleRepository(session).create(**values)
    session.commit()
    return CTARuleResponse.model_validate(rule)


@router.get("/{rule_id}", response_model=CTARuleResponse, summary="CTA rule detail")
def get_rule(rule_id: int, session: DbSession, _user: CurrentUser) -> CTARuleResponse:
    rule = CTARuleRepository(session).get(rule_id)
    if rule is None:
        raise NotFoundError("CTA rule not found.")
    return CTARuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=CTARuleResponse, summary="Update a CTA rule")
def update_rule(
    rule_id: int, payload: CTARuleUpdate, session: DbSession, _user: RequireAdmin
) -> CTARuleResponse:
    repo = CTARuleRepository(session)
    rule = repo.get(rule_id)
    if rule is None:
        raise NotFoundError("CTA rule not found.")
    values = payload.model_dump(exclude_unset=True)
    _validate_references(session, values.get("brand_id"), values.get("product_id"))
    if "channel" in values and values["channel"] is not None:
        values["channel"] = values["channel"].value
    repo.update(rule, **values)
    session.commit()
    return CTARuleResponse.model_validate(rule)


@router.delete("/{rule_id}", response_model=MessageResponse, summary="Delete a CTA rule")
def delete_rule(rule_id: int, session: DbSession, _user: RequireAdmin) -> MessageResponse:
    repo = CTARuleRepository(session)
    rule = repo.get(rule_id)
    if rule is None:
        raise NotFoundError("CTA rule not found.")
    repo.delete(rule)
    session.commit()
    return MessageResponse(message="CTA rule deleted.")
