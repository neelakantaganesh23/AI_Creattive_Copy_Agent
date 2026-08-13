"""Transactional email for account operations only."""

from functools import lru_cache

from app.services.email.sender import (
    ConsoleEmailSender,
    EmailMessage,
    EmailSender,
    ResendEmailSender,
    SmtpEmailSender,
    build_email_sender,
)


@lru_cache
def get_email_sender() -> EmailSender:
    return build_email_sender()


def reset_email_sender_cache() -> None:
    """Clear the cached sender. Used by tests that swap configuration."""
    get_email_sender.cache_clear()


__all__ = [
    "ConsoleEmailSender",
    "EmailMessage",
    "EmailSender",
    "ResendEmailSender",
    "SmtpEmailSender",
    "build_email_sender",
    "get_email_sender",
    "reset_email_sender_cache",
]
