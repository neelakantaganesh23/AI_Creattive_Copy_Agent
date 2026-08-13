"""Authentication routes (§11).

The refresh token is delivered as an HttpOnly cookie so it is never reachable from
JavaScript. The short-lived access token is returned in the response body and kept
in memory by the frontend's API client.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import CurrentUser, DbSession, login_rate_limit
from app.core.config import settings
from app.core.errors import AppError, ErrorCode, TokenError
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _token_response(service: AuthService, user, response: Response) -> TokenResponse:
    access_token, _expires_at, refresh_token = service.issue_tokens(user)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
def register(
    payload: RegisterRequest,
    response: Response,
    session: DbSession,
    _: Annotated[None, Depends(login_rate_limit)],
) -> TokenResponse:
    if not settings.allow_registration:
        raise AppError(
            "Self-registration is disabled. Contact an administrator.",
            code=ErrorCode.REGISTRATION_DISABLED,
            status_code=status.HTTP_403_FORBIDDEN,
        )
    service = AuthService(session)
    user = service.register(
        name=payload.name, email=payload.email, password=payload.password, role=payload.role
    )
    return _token_response(service, user, response)


@router.post("/login", response_model=TokenResponse, summary="Sign in")
def login(
    payload: LoginRequest,
    response: Response,
    session: DbSession,
    _: Annotated[None, Depends(login_rate_limit)],
) -> TokenResponse:
    service = AuthService(session)
    user = service.authenticate(email=payload.email, password=payload.password)
    return _token_response(service, user, response)


@router.post("/refresh", response_model=TokenResponse, summary="Rotate the access token")
def refresh(request: Request, response: Response, session: DbSession) -> TokenResponse:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise TokenError("No active session was found. Please sign in.")

    service = AuthService(session)
    user, access_token, _expires_at, new_refresh = service.refresh(token)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse, summary="Sign out")
def logout(request: Request, response: Response, session: DbSession) -> MessageResponse:
    AuthService(session).logout(request.cookies.get(settings.refresh_cookie_name))
    _clear_refresh_cookie(response)
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=UserResponse, summary="Current user profile")
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
