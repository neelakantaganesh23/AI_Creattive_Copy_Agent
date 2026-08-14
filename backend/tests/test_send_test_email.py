"""Self-test-send of a generated campaign email (§18, §25).

Mirrors the CapturingSender pattern in test_password_reset.py: no email ever
leaves the process. The recipient is always the requesting user's own address
-- there is no request field that could target anyone else.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services import generation_service
from app.services.email import EmailMessage
from tests.conftest import MARKETER_EMAIL, generation_payload


class CapturingSender:
    """Stands in for the email transport and records what would be delivered."""

    name = "capture"

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def sender(monkeypatch) -> CapturingSender:
    captured = CapturingSender()
    monkeypatch.setattr(generation_service, "get_email_sender", lambda: captured)
    return captured


class FailingSender:
    """Stands in for a transport that rejects the send, e.g. Resend returning 422."""

    name = "failing"

    async def send(self, message: EmailMessage) -> None:
        raise RuntimeError("simulated transport failure")


def create_generation(client, headers, taxonomy, **overrides):
    response = client.post(
        "/api/v1/generations", headers=headers, json=generation_payload(taxonomy, **overrides)
    )
    assert response.status_code == 202, response.text
    return response.json()


def send_test_email(client, headers, generation_id):
    return client.post(f"/api/v1/generations/{generation_id}/send-test-email", headers=headers)


def test_send_test_email_delivers_to_the_requesting_users_own_address(
    client: TestClient, marketer_headers, taxonomy, monkeypatch
) -> None:
    captured = sender(monkeypatch)

    created = create_generation(client, marketer_headers, taxonomy)
    response = send_test_email(client, marketer_headers, created["id"])
    # The response to POST /generations is captured before the background
    # workflow finishes, so re-fetch it to see the completed output.
    generation = client.get(
        f"/api/v1/generations/{created['id']}", headers=marketer_headers
    ).json()

    assert response.status_code == 200, response.text
    assert response.json()["message"] == f"Test email sent to {MARKETER_EMAIL}."
    assert len(captured.messages) == 1
    message = captured.messages[0]
    assert message.to == MARKETER_EMAIL
    assert generation["output"]["email"]["headline"] in message.subject
    assert message.html_body is not None
    assert generation["output"]["email"]["cta"] in message.html_body


def test_send_test_email_omits_the_image_block_when_there_is_no_image(
    client: TestClient, marketer_headers, taxonomy, monkeypatch
) -> None:
    captured = sender(monkeypatch)
    monkeypatch.setattr("app.core.config.settings.image_generation_enabled", False)

    generation = create_generation(client, marketer_headers, taxonomy)
    response = send_test_email(client, marketer_headers, generation["id"])

    assert response.status_code == 200, response.text
    assert "<img" not in captured.messages[0].html_body


def test_send_test_email_requires_a_completed_generation(
    client: TestClient, marketer_headers, taxonomy, monkeypatch
) -> None:
    captured = sender(monkeypatch)

    # A generation row exists but the background task has not populated
    # output_json -- simulates "still running" without waiting on a real run.
    generation = create_generation(client, marketer_headers, taxonomy)
    from app.database.session import SessionLocal
    from app.repositories.generation_repository import GenerationRepository

    session = SessionLocal()
    try:
        row = GenerationRepository(session).get(generation["id"])
        row.output_json = None
        session.commit()
    finally:
        session.close()

    response = send_test_email(client, marketer_headers, generation["id"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GENERATION_NOT_READY"
    assert captured.messages == []


def test_send_test_email_rejects_a_non_email_channel(
    client: TestClient, marketer_headers, taxonomy, monkeypatch
) -> None:
    captured = sender(monkeypatch)

    generation = create_generation(client, marketer_headers, taxonomy, channel="sms")
    response = send_test_email(client, marketer_headers, generation["id"])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GENERATION_NOT_READY"
    assert captured.messages == []


def test_a_marketer_cannot_send_another_users_generation(
    client: TestClient, marketer_headers, admin_headers, taxonomy, monkeypatch
) -> None:
    captured = sender(monkeypatch)

    generation = create_generation(client, admin_headers, taxonomy)
    response = send_test_email(client, marketer_headers, generation["id"])

    assert response.status_code == 403
    assert captured.messages == []


def test_viewers_cannot_send_test_email(
    client: TestClient, viewer_headers, marketer_headers, taxonomy, monkeypatch
) -> None:
    captured = sender(monkeypatch)

    generation = create_generation(client, marketer_headers, taxonomy)
    response = send_test_email(client, viewer_headers, generation["id"])

    assert response.status_code == 403
    assert captured.messages == []


def test_send_test_email_is_rate_limited(
    client: TestClient, marketer_headers, taxonomy, monkeypatch
) -> None:
    from app.core.config import settings as app_settings

    captured = sender(monkeypatch)
    monkeypatch.setattr(app_settings, "rate_limit_enabled", True)
    monkeypatch.setattr(app_settings, "rate_limit_test_email", "2/hour")

    generation = create_generation(client, marketer_headers, taxonomy)

    for _ in range(2):
        assert send_test_email(client, marketer_headers, generation["id"]).status_code == 200

    limited = send_test_email(client, marketer_headers, generation["id"])
    assert limited.status_code == 429
    assert len(captured.messages) == 2


def test_a_transport_failure_returns_a_clean_error_not_a_500(
    client: TestClient, marketer_headers, taxonomy, monkeypatch
) -> None:
    monkeypatch.setattr(generation_service, "get_email_sender", lambda: FailingSender())

    generation = create_generation(client, marketer_headers, taxonomy)
    response = send_test_email(client, marketer_headers, generation["id"])

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "EMAIL_DELIVERY_FAILED"
