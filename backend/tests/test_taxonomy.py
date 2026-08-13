"""Taxonomy CRUD, role enforcement, dashboard and system routes (§18)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import generation_payload


def test_seeded_audience_segments_are_present(client: TestClient, marketer_headers) -> None:
    items = client.get("/api/v1/audience-segments", headers=marketer_headers).json()["items"]
    assert [item["name"] for item in items] == [
        "Trendsetters",
        "Enthusiasts",
        "Performance Seekers",
        "General / All",
    ]


def test_admin_can_create_and_deactivate_a_segment(client: TestClient, admin_headers) -> None:
    created = client.post(
        "/api/v1/audience-segments",
        headers=admin_headers,
        json={"name": "Gift Buyers", "description": "Shopping for someone else."},
    )
    assert created.status_code == 201
    segment_id = created.json()["id"]

    updated = client.put(
        f"/api/v1/audience-segments/{segment_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    assert (
        client.delete(
            f"/api/v1/audience-segments/{segment_id}", headers=admin_headers
        ).status_code
        == 200
    )


def test_marketer_cannot_manage_taxonomy(client: TestClient, marketer_headers) -> None:
    response = client.post(
        "/api/v1/audience-segments", headers=marketer_headers, json={"name": "Nope"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_duplicate_segment_name_conflicts(client: TestClient, admin_headers) -> None:
    response = client.post(
        "/api/v1/audience-segments", headers=admin_headers, json={"name": "Trendsetters"}
    )
    assert response.status_code == 409


def test_brand_and_product_crud(client: TestClient, admin_headers) -> None:
    brand = client.post(
        "/api/v1/brands", headers=admin_headers, json={"name": "Lumen", "description": "Lighting."}
    )
    assert brand.status_code == 201
    brand_id = brand.json()["id"]

    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"brand_id": brand_id, "name": "Lumen Desk Lamp", "sku": "LM-001"},
    )
    assert product.status_code == 201
    assert product.json()["brand_name"] == "Lumen"

    listing = client.get(
        "/api/v1/products", headers=admin_headers, params={"brand_id": brand_id}
    ).json()
    assert listing["total"] == 1


def test_product_rejects_unknown_brand(client: TestClient, admin_headers) -> None:
    response = client.post(
        "/api/v1/products", headers=admin_headers, json={"brand_id": 9999, "name": "Ghost"}
    )
    assert response.status_code == 422


def test_cta_rule_crud(client: TestClient, admin_headers) -> None:
    created = client.post(
        "/api/v1/cta-rules",
        headers=admin_headers,
        json={"template": "DISCOVER {brand}", "priority": 75, "channel": "mobile"},
    )
    assert created.status_code == 201
    assert created.json()["channel"] == "mobile"

    rules = client.get("/api/v1/cta-rules", headers=admin_headers).json()
    assert rules["total"] >= 4


def test_template_listing_filters_by_channel(client: TestClient, marketer_headers) -> None:
    templates = client.get(
        "/api/v1/templates", headers=marketer_headers, params={"channel": "sms"}
    ).json()
    assert templates["total"] == 1
    assert templates["items"][0]["channel"] == "sms"


def test_dashboard_summary_is_computed_from_data(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    empty = client.get("/api/v1/dashboard/summary", headers=marketer_headers).json()
    assert empty["copies_generated_total"] == 0
    assert empty["audience_segments_configured"] == 4
    assert empty["channels_supported"] == 3
    assert empty["average_generation_time_ms"] is None

    client.post(
        "/api/v1/generations", headers=marketer_headers, json=generation_payload(taxonomy)
    )
    filled = client.get("/api/v1/dashboard/summary", headers=marketer_headers).json()
    assert filled["copies_generated_total"] == 1
    assert filled["copies_generated_this_month"] == 1
    assert filled["generations_by_channel"]["email"] == 1
    assert filled["average_generation_time_ms"] is not None
    assert filled["success_rate"] == 1.0


def test_dashboard_recent_lists_generations(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    client.post(
        "/api/v1/generations", headers=marketer_headers, json=generation_payload(taxonomy)
    )
    recent = client.get("/api/v1/dashboard/recent", headers=marketer_headers).json()
    assert len(recent["items"]) == 1
    assert recent["items"][0]["channel"] == "email"


def test_health_and_ready(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["database"] == "ok"


def test_system_info_never_exposes_secrets(client: TestClient, admin_headers) -> None:
    info = client.get("/system/info", headers=admin_headers).json()
    assert info["ai_provider"] == "mock"
    assert info["grounding_enabled"] is False
    assert "api_key" not in str(info).lower()
    assert info["channel_limits"]["email"]["headline"] == 80


def test_unknown_route_returns_the_standard_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body["error"]) == {"code", "message", "details", "request_id"}
    assert body["error"]["request_id"]


def test_request_id_is_returned_on_every_response(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
