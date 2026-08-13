"""Shared FastAPI dependencies: database sessions, authentication, authorisation."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import NotAuthenticatedError, PermissionDeniedError, RateLimitError
from app.core.rate_limit import RateLimitPolicy, rate_limiter
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import PaginationParams

# ``auto_error=False`` so a missing header produces our standard error envelope.
bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: DbSession,
) -> User:
    if credentials is None or not credentials.credentials:
        raise NotAuthenticatedError()

    payload = decode_access_token(credentials.credentials)
    user = UserRepository(session).get(int(payload["sub"]))
    if user is None or not user.is_active:
        raise NotAuthenticatedError("Your account is no longer active.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    """Dependency factory enforcing role-based access (§15)."""

    allowed = set(roles)

    def _guard(user: CurrentUser) -> User:
        if Role(user.role) not in allowed:
            raise PermissionDeniedError(
                "This action requires one of the following roles: "
                + ", ".join(sorted(role.value for role in allowed))
                + "."
            )
        return user

    return _guard


RequireAdmin = Annotated[User, Depends(require_roles(Role.ADMIN))]
RequireEditor = Annotated[User, Depends(require_roles(Role.ADMIN, Role.MARKETER))]


def get_pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


Pagination = Annotated[PaginationParams, Depends(get_pagination)]


def client_identity(request: Request) -> str:
    """Best-effort client key for rate limiting."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(bucket: str, expression: str, identity: str) -> None:
    if not settings.rate_limit_enabled:
        return
    result = rate_limiter.check(bucket, identity, RateLimitPolicy.parse(expression))
    if not result.allowed:
        raise RateLimitError(retry_after=result.retry_after_seconds)


def login_rate_limit(request: Request) -> None:
    enforce_rate_limit("login", settings.rate_limit_login, client_identity(request))


def generation_rate_limit(request: Request) -> None:
    enforce_rate_limit("generation", settings.rate_limit_generation, client_identity(request))


def paginate_response(items: list, total: int, pagination: PaginationParams) -> dict:
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": pages,
    }
