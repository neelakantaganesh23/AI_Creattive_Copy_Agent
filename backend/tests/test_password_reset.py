"""Password reset tests (§18). No email ever leaves the process."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_token
from app.repositories.password_reset_repository import PasswordResetTokenRepository
from app.repositories.user_repository import UserRepository
from app.services import password_reset_service
from app.services.email import EmailMessage
from tests.conftest import MARKETER_EMAIL, PASSWORD, login

NEW_PASSWORD = "BrandNewPass1"


class CapturingSender:
    """Stands in for the email transport and records what would be delivered."""

    name = "capture"

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


@pytest.fixture
def sender(monkeypatch) -> CapturingSender:
    captured = CapturingSender()
    monkeypatch.setattr(password_reset_service, "get_email_sender", lambda: captured)
    return captured


def request_reset(client: TestClient, email: str = MARKETER_EMAIL):
    return client.post("/api/v1/auth/password-reset/request", json={"email": email})


def token_from(message: EmailMessage) -> str:
    marker = "reset-password?token="
    start = message.text_body.index(marker) + len(marker)
    return message.text_body[start:].split()[0]


def test_request_sends_a_reset_link(client: TestClient, sender) -> None:
    response = request_reset(client)
    assert response.status_code == 200
    assert len(sender.messages) == 1

    message = sender.messages[0]
    assert message.to == MARKETER_EMAIL
    assert settings.frontend_base_url in message.text_body
    assert "reset-password?token=" in message.text_body


def test_request_for_an_unknown_address_looks_identical(client: TestClient, sender) -> None:
    known = request_reset(client)
    unknown = request_reset(client, "nobody@example.com")

    # Same status and same body: the endpoint cannot be used to enumerate users.
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(sender.messages) == 1


def test_delivery_failure_stays_indistinguishable(client: TestClient, monkeypatch) -> None:
    """A broken transport must not make a registered address answer differently.

    Misconfigured delivery is the normal state on a fresh deployment -- an unverified
    sender domain, a missing key -- so this is the case where the enumeration guard
    is most likely to be tested in the wild.
    """

    class FailingSender:
        name = "failing"

        async def send(self, _message: EmailMessage) -> None:
            raise ValueError("RESEND_API_KEY is required when EMAIL_PROVIDER=resend.")

    monkeypatch.setattr(password_reset_service, "get_email_sender", lambda: FailingSender())

    known = request_reset(client)
    unknown = request_reset(client, "nobody@example.com")

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_reset_token_is_stored_only_as_a_hash(client: TestClient, db, sender) -> None:
    request_reset(client)
    token = token_from(sender.messages[0])

    stored = PasswordResetTokenRepository(db).get_active(hash_token(token))
    assert stored is not None
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


def test_confirm_changes_the_password(client: TestClient, sender) -> None:
    request_reset(client)
    token = token_from(sender.messages[0])

    response = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "password": NEW_PASSWORD}
    )
    assert response.status_code == 200

    assert login(client, MARKETER_EMAIL, NEW_PASSWORD).status_code == 200
    assert login(client, MARKETER_EMAIL, PASSWORD).status_code == 401


def test_token_is_single_use(client: TestClient, sender) -> None:
    request_reset(client)
    token = token_from(sender.messages[0])
    payload = {"token": token, "password": NEW_PASSWORD}

    assert client.post("/api/v1/auth/password-reset/confirm", json=payload).status_code == 200
    second = client.post("/api/v1/auth/password-reset/confirm", json=payload)
    assert second.status_code == 401
    assert second.json()["error"]["code"] == "TOKEN_INVALID"


def test_requesting_again_invalidates_the_previous_link(client: TestClient, sender) -> None:
    request_reset(client)
    first_token = token_from(sender.messages[0])
    request_reset(client)
    second_token = token_from(sender.messages[1])

    stale = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": first_token, "password": NEW_PASSWORD},
    )
    assert stale.status_code == 401
    assert (
        client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": second_token, "password": NEW_PASSWORD},
        ).status_code
        == 200
    )


def test_expired_token_is_rejected(client: TestClient, db, sender) -> None:
    request_reset(client)
    token = token_from(sender.messages[0])

    repo = PasswordResetTokenRepository(db)
    stored = repo.get_active(hash_token(token))
    stored.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    response = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "password": NEW_PASSWORD}
    )
    assert response.status_code == 401
    assert "expired" in response.json()["error"]["message"]


def test_unknown_token_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "x" * 40, "password": NEW_PASSWORD},
    )
    assert response.status_code == 401


def test_weak_new_password_is_rejected(client: TestClient, sender) -> None:
    request_reset(client)
    token = token_from(sender.messages[0])

    response = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "password": "onlyletters"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reset_revokes_every_existing_session(client: TestClient, sender) -> None:
    # An active session exists before the reset.
    assert login(client).status_code == 200
    assert client.post("/api/v1/auth/refresh").status_code == 200

    request_reset(client)
    token = token_from(sender.messages[0])
    assert (
        client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "password": NEW_PASSWORD},
        ).status_code
        == 200
    )

    # The old refresh cookie no longer buys a new access token.
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_no_email_for_a_google_only_account(client: TestClient, db, sender) -> None:
    from app.models.enums import AuthProvider, Role

    UserRepository(db).create(
        name="Google Person",
        email="google.person@example.com",
        password_hash=None,
        role=Role.MARKETER,
        is_active=True,
        auth_provider=AuthProvider.GOOGLE,
        google_sub="sub-1",
    )
    db.commit()

    response = request_reset(client, "google.person@example.com")
    assert response.status_code == 200
    # Nothing to reset, and the response is indistinguishable from the happy path.
    assert sender.messages == []


def test_rate_limit_applies_to_reset_requests(client: TestClient, sender, monkeypatch) -> None:
    from app.core.rate_limit import rate_limiter

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_password_reset", "2/hour")
    rate_limiter.reset()

    assert request_reset(client).status_code == 200
    assert request_reset(client).status_code == 200
    blocked = request_reset(client)
    assert blocked.status_code == 429
    rate_limiter.reset()


async def test_console_sender_does_not_raise() -> None:
    from app.services.email import ConsoleEmailSender

    await ConsoleEmailSender().send(
        EmailMessage(to="x@example.com", subject="s", text_body="body")
    )


async def test_resend_logs_why_the_provider_refused(monkeypatch, caplog) -> None:
    """The provider's explanation is the only thing that identifies the misconfiguration."""
    import httpx

    from app.services.email import sender as sender_module

    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    refusal = {"message": "The example.com domain is not verified.", "name": "validation_error"}

    real_client = httpx.AsyncClient

    def fake_client(*_args, **kwargs):
        return real_client(
            transport=httpx.MockTransport(lambda _r: httpx.Response(403, json=refusal)), **kwargs
        )

    # The sender imports httpx inside the method, so patch the module itself.
    monkeypatch.setattr(httpx, "AsyncClient", fake_client)

    with caplog.at_level("ERROR"), pytest.raises(httpx.HTTPStatusError):
        await sender_module.ResendEmailSender().send(
            EmailMessage(to="x@example.com", subject="s", text_body="body")
        )

    logged = "".join(record.getMessage() + str(record.__dict__) for record in caplog.records)
    assert "domain is not verified" in logged
    assert "403" in logged
    # The credential must never reach the log.
    assert "re_test_key" not in logged
