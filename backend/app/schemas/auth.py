"""Authentication request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MAX_PASSWORD_BYTES
from app.models.enums import Role

PASSWORD_FIELD = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = PASSWORD_FIELD
    role: Role = Role.MARKETER

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(
            char.isdigit() for char in value
        ):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)
    remember_me: bool = False


class GoogleLoginRequest(BaseModel):
    """The ID token issued by Google Identity Services in the browser."""

    credential: str = Field(min_length=20, max_length=8192)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    password: str = PASSWORD_FIELD

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(
            char.isdigit() for char in value
        ):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class AuthOptionsResponse(BaseModel):
    """Non-secret capability flags the login screen reads before rendering."""

    google_login_enabled: bool
    google_client_id: str | None
    registration_enabled: bool
    password_reset_enabled: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime
    auth_provider: str = "local"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    # Returned only when cookies are unavailable to the client (see README).
    refresh_token: str | None = None
