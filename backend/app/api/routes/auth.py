"""Authentication routes (§11).

The refresh token is delivered as an HttpOnly cookie so it is never reachable from
JavaScript. The short-lived access token is returned in the response body and kept
in memory by the frontend's API client.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import (
    CurrentUser,
    DbSession,
    client_identity,
    enforce_rate_limit,
    login_rate_limit,
)
from app.core.config import settings
from app.core.errors import AppError, ErrorCode, TokenError
from app.schemas.auth import (
    AuthOptionsResponse,
    GoogleLoginRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService
from app.services.google_auth_service import GoogleAuthService
from app.services.password_reset_service import PasswordResetService

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


@router.post("/google", response_model=TokenResponse, summary="Sign in with Google")
def google_login(
    payload: GoogleLoginRequest,
    response: Response,
    session: DbSession,
    _: Annotated[None, Depends(login_rate_limit)],
) -> TokenResponse:
    """Exchange a Google ID token for an application session.

    First-time sign-ins are provisioned automatically with the role configured in
    ``GOOGLE_DEFAULT_ROLE``.
    """
    user = GoogleAuthService(session).authenticate(payload.credential)
    return _token_response(AuthService(session), user, response)


@router.get(
    "/options",
    response_model=AuthOptionsResponse,
    summary="Which sign-in methods this server offers",
)
def auth_options() -> AuthOptionsResponse:
    """Public, non-secret. The client id is safe to expose -- it identifies the
    application to Google and is embedded in every browser request anyway."""
    return AuthOptionsResponse(
        google_login_enabled=settings.google_login_enabled,
        google_client_id=settings.google_client_id,
        registration_enabled=settings.allow_registration,
        password_reset_enabled=True,
    )


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    summary="Request a password reset link",
)
async def request_password_reset(
    payload: PasswordResetRequest, request: Request, session: DbSession
) -> MessageResponse:
    """Always reports success so the endpoint cannot reveal registered addresses."""
    enforce_rate_limit(
        "password_reset", settings.rate_limit_password_reset, client_identity(request)
    )
    await PasswordResetService(session).request_reset(payload.email)
    return MessageResponse(
        message="If that email address has an account, a reset link is on its way."
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Set a new password using a reset token",
)
def confirm_password_reset(
    payload: PasswordResetConfirm, session: DbSession, response: Response
) -> MessageResponse:
    PasswordResetService(session).confirm_reset(payload.token, payload.password)
    # Every session was revoked, so drop the cookie this browser is holding too.
    _clear_refresh_cookie(response)
    return MessageResponse(message="Your password has been updated. Please sign in.")


@router.get("/me", response_model=UserResponse, summary="Current user profile")
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
