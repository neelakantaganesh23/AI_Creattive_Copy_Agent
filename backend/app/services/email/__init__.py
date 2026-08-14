"""Email delivery: transactional account email, plus self-test-send of a
generated campaign to the requesting user's own inbox (see §25 in CLAUDE.md).
"""

from functools import lru_cache

from app.services.email.campaign_template import build_campaign_email
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
    "build_campaign_email",
    "build_email_sender",
    "get_email_sender",
    "reset_email_sender_cache",
]
