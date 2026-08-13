"""Password hashing and JWT handling.

Password hashing uses the ``bcrypt`` library directly rather than Passlib. Passlib
1.7.4 (its last release, from 2020) crashes during backend detection against
bcrypt >= 4.1 -- ``module 'bcrypt' has no attribute '__about__'`` -- so it is not
usable on a current interpreter. The algorithm and cost factor are unchanged; only
the wrapper differs, and it is isolated in this module.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import TokenError

# bcrypt truncates (and, since 4.1, refuses) secrets longer than 72 bytes.
MAX_PASSWORD_BYTES = 72

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """Constant-time password check. Never raises on malformed input.

    A ``None`` hash means the account has no password (identity-provider only),
    which can never be satisfied by a password login.
    """
    if not password_hash:
        return False
    try:
        encoded = password.encode("utf-8")
        if len(encoded) > MAX_PASSWORD_BYTES:
            return False
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    *,
    role: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """Create a signed JWT access token. Returns the token and its expiry."""
    now = datetime.now(UTC)
    expires_at = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_hex(8),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token, or raise :class:`TokenError`."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Your session has expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError() from exc

    if payload.get("type") != "access":
        raise TokenError()
    if not payload.get("sub"):
        raise TokenError()
    return payload


def create_refresh_token() -> tuple[str, str, datetime]:
    """Create an opaque refresh token.

    Returns ``(token, token_hash, expires_at)``. Only the hash is persisted, so a
    database leak cannot be replayed against the API.
    """
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return token, hash_token(token), expires_at


def create_url_safe_token(length: int = 48) -> str:
    """Opaque token for links delivered by email."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
