"""Generic CRUD repository used by the taxonomy resources."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        order_by: str = "id",
        descending: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ModelT], int]:
        statement = select(self.model)
        count_statement = select(func.count()).select_from(self.model)

        conditions = []
        if is_active is not None and hasattr(self.model, "is_active"):
            conditions.append(self.model.is_active.is_(is_active))
        for key, value in (filters or {}).items():
            if value is not None and hasattr(self.model, key):
                conditions.append(getattr(self.model, key) == value)
        for condition in conditions:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        column = getattr(self.model, order_by, None) or self.model.id
        statement = statement.order_by(column.desc() if descending else column.asc())
        statement = statement.offset(offset).limit(limit)

        items = list(self.session.scalars(statement).all())
        total = self.session.scalar(count_statement) or 0
        return items, total

    def create(self, **values: Any) -> ModelT:
        entity = self.model(**values)
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: ModelT, **values: Any) -> ModelT:
        for key, value in values.items():
            setattr(entity, key, value)
        self.session.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        self.session.delete(entity)
        self.session.flush()
