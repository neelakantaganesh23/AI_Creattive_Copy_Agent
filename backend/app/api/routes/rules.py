"""Content rule management. Mutations are admin-only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Pagination, RequireAdmin, paginate_response
from app.core.errors import NotFoundError, ValidationError
from app.repositories.rule_repository import RuleRepository
from app.repositories.taxonomy_repository import AudienceSegmentRepository, BrandRepository
from app.schemas.common import MessageResponse, Page
from app.schemas.rule import RuleCreate, RuleResponse, RuleUpdate, validate_rule_value

router = APIRouter(prefix="/rules", tags=["Content rules"])


def _validate_references(session, brand_id: int | None, segment_id: int | None) -> None:
    if brand_id is not None and BrandRepository(session).get(brand_id) is None:
        raise ValidationError("The referenced brand does not exist.")
    if segment_id is not None and AudienceSegmentRepository(session).get(segment_id) is None:
        raise ValidationError("The referenced audience segment does not exist.")


@router.get("", response_model=Page[RuleResponse], summary="List content rules")
def list_rules(
    session: DbSession,
    _user: CurrentUser,
    pagination: Pagination,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[RuleResponse]:
    items, total = RuleRepository(session).list(
        offset=pagination.offset,
        limit=pagination.page_size,
        is_active=is_active,
        order_by="priority",
        descending=True,
    )
    return Page[RuleResponse].model_validate(
        paginate_response(
            [RuleResponse.model_validate(item) for item in items], total, pagination
        )
    )


@router.post(
    "",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a content rule",
)
def create_rule(payload: RuleCreate, session: DbSession, _user: RequireAdmin) -> RuleResponse:
    _validate_references(session, payload.brand_id, payload.audience_segment_id)
    values = payload.model_dump()
    values["rule_type"] = payload.rule_type.value
    values["severity"] = payload.severity.value
    values["channel"] = payload.channel.value if payload.channel else None
    rule = RuleRepository(session).create(**values)
    session.commit()
    return RuleResponse.model_validate(rule)


@router.get("/{rule_id}", response_model=RuleResponse, summary="Content rule detail")
def get_rule(rule_id: int, session: DbSession, _user: CurrentUser) -> RuleResponse:
    rule = RuleRepository(session).get(rule_id)
    if rule is None:
        raise NotFoundError("Content rule not found.")
    return RuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleResponse, summary="Update a content rule")
def update_rule(
    rule_id: int, payload: RuleUpdate, session: DbSession, _user: RequireAdmin
) -> RuleResponse:
    repo = RuleRepository(session)
    rule = repo.get(rule_id)
    if rule is None:
        raise NotFoundError("Content rule not found.")

    values = payload.model_dump(exclude_unset=True)
    _validate_references(session, values.get("brand_id"), values.get("audience_segment_id"))

    for key in ("rule_type", "severity", "channel"):
        if values.get(key) is not None:
            values[key] = values[key].value

    # The value's meaning depends on the type, which may be changing in the same
    # request, so re-validate the pair rather than each field alone.
    effective_type = values.get("rule_type", rule.rule_type)
    if "value" in values:
        try:
            values["value"] = validate_rule_value(effective_type, values["value"])
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
    elif "rule_type" in values:
        try:
            values["value"] = validate_rule_value(effective_type, rule.value)
        except ValueError as exc:
            raise ValidationError(
                f"The existing value {rule.value!r} is not valid for {effective_type}: {exc}"
            ) from exc

    repo.update(rule, **values)
    session.commit()
    return RuleResponse.model_validate(rule)


@router.delete("/{rule_id}", response_model=MessageResponse, summary="Delete a content rule")
def delete_rule(rule_id: int, session: DbSession, _user: RequireAdmin) -> MessageResponse:
    repo = RuleRepository(session)
    rule = repo.get(rule_id)
    if rule is None:
        raise NotFoundError("Content rule not found.")
    repo.delete(rule)
    session.commit()
    return MessageResponse(message="Content rule deleted.")
