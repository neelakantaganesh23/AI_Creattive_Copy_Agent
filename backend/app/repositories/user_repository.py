from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def get_by_google_sub(self, google_sub: str) -> User | None:
        return self.session.scalar(select(User).where(User.google_sub == google_sub))


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_active(self, token_hash: str) -> RefreshToken | None:
        token = self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if token is None or token.revoked_at is not None:
            return None
        expires_at = token.expires_at
        if expires_at.tzinfo is None:  # SQLite returns naive datetimes
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            return None
        return token

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        self.session.flush()

    def revoke_all_for_user(self, user_id: int) -> int:
        tokens = self.session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        ).all()
        now = datetime.now(UTC)
        for token in tokens:
            token.revoked_at = now
        self.session.flush()
        return len(tokens)
