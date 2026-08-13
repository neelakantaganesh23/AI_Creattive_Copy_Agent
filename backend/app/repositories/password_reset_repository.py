from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.password_reset import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    def get_active(self, token_hash: str) -> PasswordResetToken | None:
        token = self.session.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        if token is None or token.used_at is not None:
            return None
        expires_at = token.expires_at
        if expires_at.tzinfo is None:  # SQLite returns naive datetimes
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            return None
        return token

    def mark_used(self, token: PasswordResetToken) -> None:
        token.used_at = datetime.now(UTC)
        self.session.flush()

    def invalidate_for_user(self, user_id: int) -> int:
        """Burn every outstanding token so only the newest link works."""
        tokens = self.session.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
        ).all()
        now = datetime.now(UTC)
        for token in tokens:
            token.used_at = now
        self.session.flush()
        return len(tokens)
