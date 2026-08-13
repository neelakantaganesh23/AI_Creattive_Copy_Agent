"""Google sign-in.

Uses the Google Identity Services token flow: the browser obtains a signed ID
token, and this service verifies it against Google's public keys before issuing
the application's own session. No client secret and no redirect handling are
involved, so the existing token lifecycle is unchanged.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, AuthenticationError, ErrorCode
from app.core.logging import get_logger
from app.models.enums import AuthProvider, Role
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = get_logger("app.auth.google")

_GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


class GoogleAuthDisabledError(AppError):
    status_code = 503
    code = ErrorCode.AI_NOT_CONFIGURED
    message = "Google sign-in is not configured on this server."


def verify_google_id_token(credential: str) -> dict[str, Any]:
    """Validate the ID token's signature, audience, issuer and expiry."""
    if not settings.google_client_id:
        raise GoogleAuthDisabledError()

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError as exc:  # pragma: no cover - depends on install extras
        raise GoogleAuthDisabledError(
            "The google-auth package is required for Google sign-in."
        ) from exc

    try:
        claims = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        # Covers a bad signature, wrong audience and expiry alike; the message is
        # deliberately generic so it cannot be used to probe the verifier.
        logger.warning("google id token rejected")
        raise AuthenticationError("Google sign-in could not be verified.") from exc

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise AuthenticationError("Google sign-in could not be verified.")
    return claims


class GoogleAuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def authenticate(self, credential: str) -> User:
        """Verify the credential and return the matching (or newly created) user."""
        claims = verify_google_id_token(credential)

        if not claims.get("email_verified", False):
            raise AuthenticationError(
                "This Google account does not have a verified email address."
            )

        subject = str(claims.get("sub") or "")
        email = str(claims.get("email") or "").strip().lower()
        if not subject or not email:
            raise AuthenticationError("Google sign-in could not be verified.")

        user = self.users.get_by_google_sub(subject)
        if user is None:
            user = self.users.get_by_email(email)
            if user is not None:
                # An existing local account keeps its password; Google simply
                # becomes an additional way in.
                user.google_sub = subject
                logger.info(
                    "linked google identity to existing account", extra={"user_id": user.id}
                )
            else:
                user = self.users.create(
                    name=str(claims.get("name") or email.split("@")[0]).strip()[:120],
                    email=email,
                    password_hash=None,
                    role=Role(settings.google_default_role),
                    is_active=True,
                    auth_provider=AuthProvider.GOOGLE,
                    google_sub=subject,
                )
                logger.info(
                    "provisioned account from google sign-in",
                    extra={"user_id": user.id, "role": settings.google_default_role},
                )

        if not user.is_active:
            raise AuthenticationError(
                "This account is inactive. Contact an administrator.",
                code=ErrorCode.ACCOUNT_INACTIVE,
                status_code=403,
            )

        self.session.commit()
        return user
