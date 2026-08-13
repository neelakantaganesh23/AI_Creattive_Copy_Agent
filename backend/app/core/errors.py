"""Standardised application errors and their JSON representation (§16).

Every error the API returns is shaped as::

    {"error": {"code": "...", "message": "...", "details": null, "request_id": "..."}}
"""

from __future__ import annotations

from typing import Any


class ErrorCode:
    """Stable machine-readable error codes shared with the frontend."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    DUPLICATE_EMAIL = "DUPLICATE_EMAIL"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    REGISTRATION_DISABLED = "REGISTRATION_DISABLED"

    INVALID_CHANNEL = "INVALID_CHANNEL"
    INVALID_AUDIENCE_SEGMENT = "INVALID_AUDIENCE_SEGMENT"
    GENERATION_FAILED = "GENERATION_FAILED"
    GENERATION_IN_PROGRESS = "GENERATION_IN_PROGRESS"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    AI_PROVIDER_TIMEOUT = "AI_PROVIDER_TIMEOUT"
    AI_QUOTA_EXCEEDED = "AI_QUOTA_EXCEEDED"
    AI_INVALID_OUTPUT = "AI_INVALID_OUTPUT"
    AI_NOT_CONFIGURED = "AI_NOT_CONFIGURED"
    GROUNDING_FAILED = "GROUNDING_FAILED"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Base class for every error that maps to a controlled API response."""

    status_code: int = 500
    code: str = ErrorCode.INTERNAL_ERROR
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)

    def to_payload(self, request_id: str | None = None) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "request_id": request_id,
            }
        }


class ValidationError(AppError):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR
    message = "The submitted data is invalid."


class AuthenticationError(AppError):
    status_code = 401
    code = ErrorCode.INVALID_CREDENTIALS
    # Deliberately generic: never reveal whether the account exists (§15).
    message = "Incorrect email or password."


class NotAuthenticatedError(AppError):
    status_code = 401
    code = ErrorCode.NOT_AUTHENTICATED
    message = "Authentication is required to access this resource."


class TokenError(AppError):
    status_code = 401
    code = ErrorCode.TOKEN_INVALID
    message = "The provided token is invalid or has expired."


class PermissionDeniedError(AppError):
    status_code = 403
    code = ErrorCode.PERMISSION_DENIED
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.CONFLICT
    message = "The request conflicts with the current state of the resource."


class DuplicateEmailError(ConflictError):
    code = ErrorCode.DUPLICATE_EMAIL
    message = "An account with this email address already exists."


class RateLimitError(AppError):
    status_code = 429
    code = ErrorCode.RATE_LIMITED
    message = "Too many requests. Please try again later."

    def __init__(self, message: str | None = None, *, retry_after: int | None = None) -> None:
        super().__init__(message, details={"retry_after_seconds": retry_after})
        self.retry_after = retry_after


class PayloadTooLargeError(AppError):
    status_code = 413
    code = ErrorCode.PAYLOAD_TOO_LARGE
    message = "The request payload is too large."


class AIProviderError(AppError):
    status_code = 502
    code = ErrorCode.AI_PROVIDER_ERROR
    message = "The AI provider could not complete the request."


class AIProviderTimeoutError(AIProviderError):
    status_code = 504
    code = ErrorCode.AI_PROVIDER_TIMEOUT
    message = "The AI provider timed out."


class AIQuotaExceededError(AIProviderError):
    status_code = 429
    code = ErrorCode.AI_QUOTA_EXCEEDED
    message = "The AI provider quota has been exceeded."


class AIInvalidOutputError(AIProviderError):
    status_code = 502
    code = ErrorCode.AI_INVALID_OUTPUT
    message = "The AI provider returned output that could not be validated."


class AINotConfiguredError(AppError):
    status_code = 503
    code = ErrorCode.AI_NOT_CONFIGURED
    message = "The configured AI provider is missing required settings."


class GroundingError(AppError):
    status_code = 502
    code = ErrorCode.GROUNDING_FAILED
    message = "Web search grounding failed."


class GenerationFailedError(AppError):
    status_code = 500
    code = ErrorCode.GENERATION_FAILED
    message = "Unable to generate campaign copy."


class DatabaseError(AppError):
    status_code = 500
    code = ErrorCode.DATABASE_ERROR
    message = "A database error occurred."
