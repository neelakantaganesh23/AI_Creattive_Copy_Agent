"""Repositories for the taxonomy tables."""

from __future__ import annotations

from sqlalchemy import select

from app.models.taxonomy import AudienceSegment, Brand, CTARule, Product, Template
from app.repositories.base import BaseRepository


class BrandRepository(BaseRepository[Brand]):
    model = Brand

    def get_by_name(self, name: str) -> Brand | None:
        return self.session.scalar(select(Brand).where(Brand.name == name))


class ProductRepository(BaseRepository[Product]):
    model = Product

    def get_by_name(self, name: str) -> Product | None:
        return self.session.scalar(select(Product).where(Product.name == name))

    def list_for_brand(self, brand_id: int) -> list[Product]:
        return list(
            self.session.scalars(
                select(Product).where(Product.brand_id == brand_id).order_by(Product.name)
            ).all()
        )


class AudienceSegmentRepository(BaseRepository[AudienceSegment]):
    model = AudienceSegment

    def get_by_name(self, name: str) -> AudienceSegment | None:
        return self.session.scalar(select(AudienceSegment).where(AudienceSegment.name == name))

    def count_active(self) -> int:
        return len(
            list(
                self.session.scalars(
                    select(AudienceSegment.id).where(AudienceSegment.is_active.is_(True))
                ).all()
            )
        )


class CTARuleRepository(BaseRepository[CTARule]):
    model = CTARule

    def list_active(self) -> list[CTARule]:
        return list(
            self.session.scalars(
                select(CTARule).where(CTARule.is_active.is_(True)).order_by(CTARule.priority.desc())
            ).all()
        )


class TemplateRepository(BaseRepository[Template]):
    model = Template

    def get_active_for_channel(self, channel: str) -> Template | None:
        return self.session.scalar(
            select(Template)
            .where(Template.channel == channel, Template.is_active.is_(True))
            .order_by(Template.id)
        )
