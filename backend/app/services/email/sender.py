"""Transactional email delivery.

The product does not send marketing email (§25 non-goals); this exists purely for
account operations such as password resets. Delivery sits behind an interface so
the default build stays credential free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.email")


@dataclass(slots=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str | None = None


class EmailSender(Protocol):
    name: str

    async def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailSender:
    """Default sender: writes the message to the log instead of delivering it.

    Keeps the reset flow fully usable in development. The body is logged in full,
    which is acceptable only because no real inbox is involved -- never enable
    this in production.
    """

    name = "console"

    async def send(self, message: EmailMessage) -> None:
        logger.warning(
            "email not delivered - console sender active",
            extra={"to": message.to, "subject": message.subject},
        )
        print(
            "\n"
            "=========================== EMAIL (not sent) ===========================\n"
            f"To      : {message.to}\n"
            f"Subject : {message.subject}\n"
            "------------------------------------------------------------------------\n"
            f"{message.text_body}\n"
            "========================================================================\n",
            flush=True,
        )


class ResendEmailSender:
    """Delivers through the Resend HTTP API."""

    name = "resend"

    def __init__(self) -> None:
        if not settings.resend_api_key:
            raise ValueError("RESEND_API_KEY is required when EMAIL_PROVIDER=resend.")
        self._api_key = settings.resend_api_key

    async def send(self, message: EmailMessage) -> None:
        import httpx

        payload = {
            "from": settings.email_from,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text_body,
        }
        if message.html_body:
            payload["html"] = message.html_body

        async with httpx.AsyncClient(timeout=settings.email_timeout_seconds) as client:
            response = await client.post(
                settings.resend_api_url,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
        logger.info("email sent", extra={"provider": self.name, "to": message.to})


class SmtpEmailSender:
    """Delivers through a standard SMTP server."""

    name = "smtp"

    def __init__(self) -> None:
        if not settings.smtp_host:
            raise ValueError("SMTP_HOST is required when EMAIL_PROVIDER=smtp.")

    async def send(self, message: EmailMessage) -> None:
        import asyncio
        import smtplib
        from email.message import EmailMessage as MimeMessage

        mime = MimeMessage()
        mime["From"] = settings.email_from
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text_body)
        if message.html_body:
            mime.add_alternative(message.html_body, subtype="html")

        def deliver() -> None:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=settings.email_timeout_seconds
            ) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(mime)

        # smtplib is blocking, so keep it off the event loop.
        await asyncio.to_thread(deliver)
        logger.info("email sent", extra={"provider": self.name, "to": message.to})


def build_email_sender() -> EmailSender:
    if settings.email_provider == "resend":
        return ResendEmailSender()
    if settings.email_provider == "smtp":
        return SmtpEmailSender()
    return ConsoleEmailSender()
