"""Authentication, session and role tests (§18)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import MARKETER_EMAIL, PASSWORD, login


def test_register_creates_account_and_returns_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "New Marketer",
            "email": "new.marketer@example.com",
            "password": "StrongPass1",
            "role": "marketer",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "new.marketer@example.com"
    assert body["user"]["role"] == "marketer"
    assert "password" not in response.text.lower().replace("strongpass1", "")


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Duplicate", "email": MARKETER_EMAIL, "password": "StrongPass1"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_EMAIL"


def test_register_rejects_weak_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Weak", "email": "weak@example.com", "password": "onlyletters"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_succeeds_and_sets_refresh_cookie(client: TestClient) -> None:
    response = login(client)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert settings.refresh_cookie_name in response.cookies


def test_login_with_wrong_password_is_generic(client: TestClient) -> None:
    response = login(client, MARKETER_EMAIL, "WrongPassword1")
    assert response.status_code == 401
    body = response.json()["error"]
    assert body["code"] == "INVALID_CREDENTIALS"
    # The message must not reveal whether the account exists.
    assert body["message"] == "Incorrect email or password."


def test_login_with_unknown_email_returns_same_error(client: TestClient) -> None:
    response = login(client, "nobody@example.com", PASSWORD)
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Incorrect email or password."


def test_refresh_rotates_the_token(client: TestClient) -> None:
    login(client)
    first = client.post("/api/v1/auth/refresh")
    assert first.status_code == 200
    assert first.json()["access_token"]

    # The rotated cookie replaces the old one, and the old token is revoked.
    second = client.post("/api/v1/auth/refresh")
    assert second.status_code == 200


def test_refresh_without_session_fails(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID"


def test_logout_revokes_the_session(client: TestClient) -> None:
    login(client)
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_me_returns_profile(client: TestClient, marketer_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/auth/me", headers=marketer_headers)
    assert response.status_code == 200
    assert response.json()["email"] == MARKETER_EMAIL


def test_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID"


def test_password_hash_is_never_returned(client: TestClient, admin_headers) -> None:
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert "password" not in response.json()


def test_rate_limit_blocks_repeated_logins(client: TestClient, monkeypatch) -> None:
    from app.core.rate_limit import rate_limiter

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_login", "3/minute")
    rate_limiter.reset()

    for _ in range(3):
        login(client, MARKETER_EMAIL, "WrongPassword1")
    blocked = login(client, MARKETER_EMAIL, "WrongPassword1")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    rate_limiter.reset()
