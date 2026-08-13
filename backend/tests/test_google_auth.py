"""Google sign-in tests (§18).

The Google verifier is patched throughout: no test ever contacts Google.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.enums import AuthProvider, Role
from app.repositories.user_repository import UserRepository
from app.services import google_auth_service
from tests.conftest import MARKETER_EMAIL, PASSWORD, login

# The endpoint enforces a 20-character minimum on the credential.
VALID_CREDENTIAL = "valid-google-id-token-payload"
INVALID_CREDENTIAL = "invalid-google-id-token-payload"
UNVERIFIED_CREDENTIAL = "unverified-google-id-token-payload"

GOOGLE_CLAIMS = {
    "iss": "https://accounts.google.com",
    "sub": "google-subject-1234",
    "email": "new.person@example.com",
    "email_verified": True,
    "name": "New Person",
}


@pytest.fixture
def google_enabled(monkeypatch):
    """Enable Google sign-in with the Google SDK call stubbed out.

    Only ``verify_oauth2_token`` is replaced, so the service's own issuer,
    email-verification and error-mapping logic still runs for real.
    """
    import google.oauth2.id_token as google_id_token

    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_default_role", "marketer")

    def _verify(credential: str, request, audience):
        if credential == INVALID_CREDENTIAL:
            # Exactly what the real SDK raises for a bad signature or audience.
            raise ValueError("Token has wrong audience")
        if credential == UNVERIFIED_CREDENTIAL:
            return {**GOOGLE_CLAIMS, "email_verified": False}
        return dict(GOOGLE_CLAIMS)

    monkeypatch.setattr(google_id_token, "verify_oauth2_token", _verify)
    return _verify


def google_login(client: TestClient, credential: str = VALID_CREDENTIAL):
    return client.post("/api/v1/auth/google", json={"credential": credential})


def test_options_report_google_disabled_by_default(client: TestClient) -> None:
    body = client.get("/api/v1/auth/options").json()
    assert body["google_login_enabled"] is False
    assert body["google_client_id"] is None
    assert body["password_reset_enabled"] is True


def test_options_expose_the_client_id_when_configured(client: TestClient, google_enabled) -> None:
    body = client.get("/api/v1/auth/options").json()
    assert body["google_login_enabled"] is True
    assert body["google_client_id"] == "test-client-id.apps.googleusercontent.com"


def test_google_login_is_unavailable_when_not_configured(client: TestClient) -> None:
    response = google_login(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_google_login_provisions_a_new_marketer(
    client: TestClient, db, google_enabled
) -> None:
    response = google_login(client)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["user"]["email"] == "new.person@example.com"
    assert body["user"]["role"] == "marketer"
    assert body["user"]["auth_provider"] == "google"
    assert body["access_token"]
    assert settings.refresh_cookie_name in response.cookies

    created = UserRepository(db).get_by_email("new.person@example.com")
    assert created is not None
    # Provisioned accounts hold no password at all.
    assert created.password_hash is None
    assert created.google_sub == "google-subject-1234"


def test_second_google_login_reuses_the_same_account(
    client: TestClient, db, google_enabled
) -> None:
    assert google_login(client).status_code == 200
    assert google_login(client).status_code == 200

    users, total = UserRepository(db).list(limit=50, filters={"email": "new.person@example.com"})
    assert total == 1
    assert users[0].id


def test_google_login_links_to_an_existing_local_account(
    client: TestClient, db, google_enabled, monkeypatch
) -> None:
    import google.oauth2.id_token as google_id_token

    monkeypatch.setattr(
        google_id_token,
        "verify_oauth2_token",
        lambda credential, request, audience: {**GOOGLE_CLAIMS, "email": MARKETER_EMAIL},
    )
    response = google_login(client)
    assert response.status_code == 200
    assert response.json()["user"]["email"] == MARKETER_EMAIL

    user = UserRepository(db).get_by_email(MARKETER_EMAIL)
    assert user.google_sub == "google-subject-1234"
    # The existing password still works; Google is an additional route in.
    assert user.password_hash is not None
    assert login(client, MARKETER_EMAIL, PASSWORD).status_code == 200


def test_google_login_rejects_an_invalid_token(client: TestClient, google_enabled) -> None:
    response = google_login(client, INVALID_CREDENTIAL)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_google_login_requires_a_verified_email(client: TestClient, google_enabled) -> None:
    response = google_login(client, UNVERIFIED_CREDENTIAL)
    assert response.status_code == 401
    assert "verified email" in response.json()["error"]["message"]


def test_google_login_rejects_an_inactive_account(
    client: TestClient, db, google_enabled
) -> None:
    assert google_login(client).status_code == 200
    repo = UserRepository(db)
    user = repo.get_by_email("new.person@example.com")
    user.is_active = False
    db.commit()

    response = google_login(client)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_google_only_account_cannot_sign_in_with_a_password(
    client: TestClient, google_enabled
) -> None:
    assert google_login(client).status_code == 200
    response = login(client, "new.person@example.com", "AnyPassword1")
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Incorrect email or password."


def test_google_session_behaves_like_a_normal_session(
    client: TestClient, google_enabled
) -> None:
    token = google_login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    # Provisioned marketers can generate, but not manage taxonomy.
    assert (
        client.post("/api/v1/audience-segments", headers=headers, json={"name": "X"}).status_code
        == 403
    )
    assert client.post("/api/v1/auth/refresh").status_code == 200


def test_verifier_rejects_a_forged_issuer(monkeypatch) -> None:
    """A token that verifies but claims a foreign issuer must still be refused."""
    import google.oauth2.id_token as google_id_token

    from app.core.errors import AuthenticationError

    monkeypatch.setattr(settings, "google_client_id", "client-id")
    monkeypatch.setattr(
        google_id_token,
        "verify_oauth2_token",
        lambda credential, request, audience: {"iss": "evil.example.com", "sub": "1"},
    )
    with pytest.raises(AuthenticationError):
        google_auth_service.verify_google_id_token("token")


def test_verifier_requires_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", None)
    with pytest.raises(google_auth_service.GoogleAuthDisabledError):
        google_auth_service.verify_google_id_token("token")


def test_seeded_users_remain_local(client: TestClient) -> None:
    body = login(client).json()
    assert body["user"]["auth_provider"] == AuthProvider.LOCAL
    assert body["user"]["role"] == Role.MARKETER
