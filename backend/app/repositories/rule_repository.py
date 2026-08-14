"""Repository for admin-managed content rules."""

from __future__ import annotations

from sqlalchemy import select

from app.models.rule import Rule
from app.repositories.base import BaseRepository


class RuleRepository(BaseRepository[Rule]):
    model = Rule

    def list_active(self) -> list[Rule]:
        return list(
            self.session.scalars(
                select(Rule)
                .where(Rule.is_active.is_(True))
                .order_by(Rule.priority.desc(), Rule.id)
            ).all()
        )

    def get_by_name(self, name: str) -> Rule | None:
        return self.session.scalar(select(Rule).where(Rule.name == name))
