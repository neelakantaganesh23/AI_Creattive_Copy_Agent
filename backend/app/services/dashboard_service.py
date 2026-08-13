"""Dashboard aggregates, computed from the database (§7)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import Channel, GenerationStatus, Role
from app.models.user import User
from app.repositories.generation_repository import GenerationRepository
from app.repositories.taxonomy_repository import AudienceSegmentRepository
from app.schemas.dashboard import ChannelInfo, DashboardSummary
from app.schemas.generation import GenerationSummary
from app.services.generation_service import to_summary

CHANNEL_CATALOGUE: list[ChannelInfo] = [
    ChannelInfo(
        value=Channel.EMAIL.value,
        label="Email",
        description="Headline, Sub-heading, CTA",
        fields=["headline", "sub_heading", "cta"],
    ),
    ChannelInfo(
        value=Channel.MOBILE.value,
        label="Mobile",
        description="Superline, Pre-heading, Headline, Sub-heading, CTA",
        fields=["superline", "pre_heading", "headline", "sub_heading", "cta"],
    ),
    ChannelInfo(
        value=Channel.SMS.value,
        label="SMS",
        description="Concise promotional description",
        fields=["description"],
    ),
]


class DashboardService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.generations = GenerationRepository(session)
        self.segments = AudienceSegmentRepository(session)

    def _scope(self, user: User) -> int | None:
        return None if Role(user.role) in (Role.ADMIN, Role.VIEWER) else user.id

    def summary(self, user: User) -> DashboardSummary:
        scope = self._scope(user)
        by_status = self.generations.count_by("status", user_id=scope)
        total = sum(by_status.values())
        completed = by_status.get(GenerationStatus.COMPLETED.value, 0) + by_status.get(
            GenerationStatus.PARTIAL.value, 0
        )
        return DashboardSummary(
            copies_generated_this_month=self.generations.count_since(
                GenerationRepository.month_start(), user_id=scope
            ),
            copies_generated_total=total,
            audience_segments_configured=self.segments.count_active(),
            channels_supported=len(CHANNEL_CATALOGUE),
            average_generation_time_ms=self.generations.average_execution_time_ms(
                user_id=scope
            ),
            success_rate=round(completed / total, 4) if total else 0.0,
            channels=CHANNEL_CATALOGUE,
            generations_by_channel=self.generations.count_by("channel", user_id=scope),
            generations_by_status=by_status,
        )

    def recent(self, user: User, *, limit: int = 5) -> list[GenerationSummary]:
        rows = self.generations.recent_completed(limit=limit, user_id=self._scope(user))
        return [to_summary(row) for row in rows]
