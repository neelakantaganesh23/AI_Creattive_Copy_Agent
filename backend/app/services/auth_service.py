"""Authentication and session management."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import (
    AuthenticationError,
    DuplicateEmailError,
    ErrorCode,
    NotFoundError,
    TokenError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import Role
from app.models.user import User
from app.repositories.user_repository import RefreshTokenRepository, UserRepository

logger = get_logger("app.auth")

# A valid bcrypt hash of a value nobody holds. Verifying against it when the email
# is unknown keeps login timing constant, so the endpoint cannot be used to probe
# for registered addresses.
_DUMMY_PASSWORD_HASH = "$2b$12$.RXC7KqWa2jm0uhP3G07neLZGswx4gE.HX0ggsxH/6r6Hxy5Tabcu"


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    def register(self, *, name: str, email: str, password: str, role: Role) -> User:
        normalised = email.strip().lower()
        if self.users.get_by_email(normalised):
            raise DuplicateEmailError()
        try:
            user = self.users.create(
                name=name.strip(),
                email=normalised,
                password_hash=hash_password(password),
                role=role,
                is_active=True,
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateEmailError() from exc

        logger.info("user registered", extra={"user_id": user.id, "role": str(user.role)})
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.users.get_by_email(email.strip().lower())
        # Always run a hash comparison so timing does not reveal account existence.
        password_ok = verify_password(
            password, user.password_hash if user else _DUMMY_PASSWORD_HASH
        )
        if not user or not password_ok:
            # Includes identity-provider accounts, which hold no password hash.
            logger.warning("failed login attempt")
            raise AuthenticationError()
        if not user.is_active:
            raise AuthenticationError(
                "This account is inactive. Contact an administrator.",
                code=ErrorCode.ACCOUNT_INACTIVE,
                status_code=403,
            )
        logger.info("user authenticated", extra={"user_id": user.id})
        return user

    def issue_tokens(self, user: User) -> tuple[str, datetime, str]:
        """Return ``(access_token, access_expiry, refresh_token)``."""
        access_token, expires_at = create_access_token(str(user.id), role=str(user.role))
        refresh_token, token_hash, refresh_expires = create_refresh_token()
        self.refresh_tokens.create(
            user_id=user.id, token_hash=token_hash, expires_at=refresh_expires
        )
        self.session.commit()
        return access_token, expires_at, refresh_token

    def refresh(self, refresh_token: str) -> tuple[User, str, datetime, str]:
        """Rotate a refresh token. The presented token is revoked immediately."""
        stored = self.refresh_tokens.get_active(hash_token(refresh_token))
        if stored is None:
            raise TokenError("Your session has expired. Please sign in again.")

        user = self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise TokenError("Your session is no longer valid.")

        self.refresh_tokens.revoke(stored)
        access_token, expires_at, new_refresh = self.issue_tokens(user)
        return user, access_token, expires_at, new_refresh

    def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        stored = self.refresh_tokens.get_active(hash_token(refresh_token))
        if stored:
            self.refresh_tokens.revoke(stored)
            self.session.commit()
            logger.info("user logged out", extra={"user_id": stored.user_id})

    def get_user(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    def purge_expired_tokens(self) -> int:
        """Housekeeping helper; safe to call at startup."""
        expired = [
            token
            for token in self.session.query(self.refresh_tokens.model).all()
            if token.revoked_at is not None
            or (token.expires_at.replace(tzinfo=token.expires_at.tzinfo or UTC))
            <= datetime.now(UTC)
        ]
        for token in expired:
            self.session.delete(token)
        self.session.commit()
        return len(expired)
