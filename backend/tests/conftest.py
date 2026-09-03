"""Pytest fixtures.

Every test runs against a throwaway SQLite file with the mock AI provider and no
simulated latency, so the suite never touches an external service.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

# Configure the environment before any application module is imported.
_TEST_DB = Path(tempfile.gettempdir()) / "creative_copy_test.db"
_TEST_DB.unlink(missing_ok=True)
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite:///{_TEST_DB.as_posix()}",
        "JWT_SECRET_KEY": "test-secret-key-not-used-outside-tests",
        "AI_PROVIDER": "mock",
        "MOCK_STAGE_DELAY_MS": "0",
        "GROUNDING_ENABLED": "false",
        "GROUNDING_PROVIDER": "none",
        "SEED_ON_STARTUP": "false",
        "AUTO_CREATE_TABLES": "false",
        "RATE_LIMIT_ENABLED": "false",
        "LOG_LEVEL": "WARNING",
        "LOG_JSON": "false",
        "BCRYPT_ROUNDS": "4",
        # Pinned so the suite never inherits a developer's real .env. Tests that
        # need these enable them explicitly via monkeypatch.
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_DEFAULT_ROLE": "marketer",
        "EMAIL_PROVIDER": "console",
        "TAVILY_API_KEY": "",
        "GEMINI_API_KEY": "",
        "GEMINI_FLASH_MODEL": "",
        "GEMINI_PRO_MODEL": "",
        "GEMINI_IMAGE_MODEL": "",
        "IMAGE_PROVIDER": "mock",
        # Tracing is never touched by the suite; explicitly off so no test can
        # inherit a real Opik key from the environment.
        "OPIK_ENABLED": "false",
        "OPIK_API_KEY": "",
        "OPIK_URL_OVERRIDE": "",
        "STABILITY_API_KEY": "",
        "MEDIA_DIR": str(Path(tempfile.gettempdir()) / "creative_copy_test_media"),
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.rate_limit import rate_limiter  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.seed import seed_all  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import Role  # noqa: E402
from app.services.ai.factory import reset_provider_cache  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402

ADMIN_EMAIL = "admin@example.com"
MARKETER_EMAIL = "marketer@example.com"
VIEWER_EMAIL = "viewer@example.com"
PASSWORD = "ChangeMe123!"

SAMPLE_BRIEF = (
    "We are launching the new AeroFlex Running Shoes. The shoes are lightweight, "
    "breathable, and built for speed and comfort. The product is designed for everyday "
    "runners and athletes who want performance with modern style. AeroFlex Running Shoes "
    "are available in four colorways.\n\n"
    "Key message: Run lighter. Go farther. Feel unstoppable.\n\n"
    "Promote the launch with an exciting and energetic tone. Highlight comfort, "
    "durability, responsive cushioning, and modern design."
)


@pytest.fixture(autouse=True)
def _reset_database() -> Iterator[None]:
    """Rebuild the schema and reseed reference data before every test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_provider_cache()
    rate_limiter.reset()
    with SessionLocal() as session:
        seed_all(session)
        AuthService(session).register(
            name="Viewer User", email=VIEWER_EMAIL, password=PASSWORD, role=Role.VIEWER
        )
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str = MARKETER_EMAIL, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth_headers(client: TestClient, email: str = MARKETER_EMAIL) -> dict[str, str]:
    response = login(client, email)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def marketer_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, MARKETER_EMAIL)


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, ADMIN_EMAIL)


@pytest.fixture
def viewer_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, VIEWER_EMAIL)


@pytest.fixture
def taxonomy(client: TestClient, marketer_headers: dict[str, str]) -> dict[str, int]:
    """Ids for the seeded AeroFlex product and the Performance Seekers segment."""
    products = client.get("/api/v1/products", headers=marketer_headers).json()["items"]
    segments = client.get("/api/v1/audience-segments", headers=marketer_headers).json()["items"]
    product = next(item for item in products if item["name"] == "AeroFlex Running Shoes")
    segment = next(item for item in segments if item["name"] == "Performance Seekers")
    return {
        "brand_id": product["brand_id"],
        "product_id": product["id"],
        "audience_segment_id": segment["id"],
    }


def generation_payload(taxonomy: dict[str, int], **overrides) -> dict:
    payload = {
        "brief": SAMPLE_BRIEF,
        "channel": "email",
        "language": "English",
        **taxonomy,
    }
    payload.update(overrides)
    return payload
