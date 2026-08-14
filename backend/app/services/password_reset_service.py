"""Password reset request and confirmation.

The request endpoint always reports success, whether or not the address exists,
so it cannot be used to discover registered accounts. Tokens are single use,
short lived, and stored only as hashes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import TokenError
from app.core.logging import get_logger
from app.core.security import create_url_safe_token, hash_password, hash_token
from app.models.enums import AuthProvider
from app.models.user import User
from app.repositories.password_reset_repository import PasswordResetTokenRepository
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.services.email import EmailMessage, get_email_sender

logger = get_logger("app.auth.password_reset")


def build_reset_email(user: User, token: str) -> EmailMessage:
    link = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={token}"
    minutes = settings.password_reset_expire_minutes
    text = (
        f"Hello {user.name},\n\n"
        "We received a request to reset your AI Creative Copy Agent password.\n\n"
        f"Reset your password: {link}\n\n"
        f"This link expires in {minutes} minutes and can be used once.\n"
        "If you did not request a reset, you can ignore this email -- your password "
        "has not changed.\n"
    )
    html = (
        f"<p>Hello {user.name},</p>"
        "<p>We received a request to reset your AI Creative Copy Agent password.</p>"
        f'<p><a href="{link}">Reset your password</a></p>'
        f"<p>This link expires in {minutes} minutes and can be used once.</p>"
        "<p>If you did not request a reset, you can ignore this email &mdash; your "
        "password has not changed.</p>"
    )
    return EmailMessage(
        to=user.email,
        subject="Reset your AI Creative Copy Agent password",
        text_body=text,
        html_body=html,
    )


class PasswordResetService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = PasswordResetTokenRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def request_reset(self, email: str) -> None:
        """Issue a reset token and email it. Silent when the address is unknown."""
        user = self.users.get_by_email(email.strip().lower())

        if user is None or not user.is_active:
            logger.info("password reset requested for an unknown or inactive address")
            return
        if not user.has_password and user.auth_provider == AuthProvider.GOOGLE:
            # Nothing to reset: this account signs in through Google.
            logger.info(
                "password reset requested for a google-only account",
                extra={"user_id": user.id},
            )
            return

        # Invalidate any outstanding tokens so only the newest link works.
        self.tokens.invalidate_for_user(user.id)

        token = create_url_safe_token()
        self.tokens.create(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.password_reset_expire_minutes),
        )
        self.session.commit()

        try:
            await get_email_sender().send(build_reset_email(user, token))
        except Exception:
            # This endpoint answers identically whether or not the address is
            # registered. Letting a transport failure become a 500 would undo that:
            # an unknown address would still get 200 while a real one errored,
            # which is exactly the disclosure the early returns above prevent.
            logger.exception(
                "password reset email delivery failed", extra={"user_id": user.id}
            )
            return

        logger.info("password reset email dispatched", extra={"user_id": user.id})

    def confirm_reset(self, token: str, new_password: str) -> User:
        """Consume a reset token and set the new password."""
        stored = self.tokens.get_active(hash_token(token))
        if stored is None:
            raise TokenError("This reset link is invalid or has expired. Request a new one.")

        user = self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise TokenError("This reset link is no longer valid.")

        user.password_hash = hash_password(new_password)
        if user.auth_provider == AuthProvider.GOOGLE:
            # The account now has both sign-in methods.
            user.auth_provider = AuthProvider.LOCAL
        self.tokens.mark_used(stored)

        # A password change ends every existing session.
        revoked = self.refresh_tokens.revoke_all_for_user(user.id)
        self.session.commit()

        logger.info(
            "password reset completed",
            extra={"user_id": user.id, "sessions_revoked": revoked},
        )
        return user
