"""Admin-managed content rules.

These are the constraints copy must satisfy -- character limits, word counts,
banned terms, and natural-language guidelines such as "make it sound natural".
They are the single source of truth: the ``LIMIT_*`` environment variables only
seed this table on a fresh install.

Scoping mirrors :class:`~app.models.taxonomy.CTARule`: ``channel``, ``field``,
``brand_id`` and ``audience_segment_id`` are each either NULL (wildcard) or must
equal the generation's value for the rule to apply.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import Severity
from app.models.taxonomy import AudienceSegment, Brand


class Rule(Base, TimestampMixin):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # Interpretation depends on ``rule_type``: an integer for the length and word
    # count rules, a comma separated list for term rules, a pattern for regex,
    # and free text for guidelines.
    value: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default=Severity.ERROR)

    # Scope. NULL means "applies to every value of this dimension".
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    field_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), nullable=True, index=True
    )
    audience_segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("audience_segments.id", ondelete="CASCADE"), nullable=True, index=True
    )

    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    brand: Mapped[Brand | None] = relationship()
    audience_segment: Mapped[AudienceSegment | None] = relationship()
