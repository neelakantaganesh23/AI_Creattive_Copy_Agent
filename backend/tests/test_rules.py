"""Content rule CRUD, validation and role enforcement (§18)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import generation_payload


def create_rule(client, headers, **overrides):
    payload = {
        "name": "Email headline length",
        "rule_type": "max_chars",
        "value": "50",
        "severity": "error",
        "channel": "email",
        "field_name": "headline",
        "priority": 100,
    }
    payload.update(overrides)
    return client.post("/api/v1/rules", headers=headers, json=payload)


# -- Seeded state ------------------------------------------------------------
def test_seeded_rules_cover_every_channel_field(client: TestClient, marketer_headers) -> None:
    items = client.get("/api/v1/rules", headers=marketer_headers).json()["items"]
    limits = {
        (item["channel"], item["field_name"]): item["value"]
        for item in items
        if item["rule_type"] == "max_chars"
    }
    assert limits[("email", "headline")] == "80"
    assert limits[("sms", "description")] == "160"
    # The natural-language rules are seeded for the judge.
    assert any(item["rule_type"] == "guideline" for item in items)


# -- CRUD --------------------------------------------------------------------
def test_admin_can_create_update_and_delete_a_rule(client: TestClient, admin_headers) -> None:
    created = create_rule(client, admin_headers, name="CTA word count",
                          rule_type="max_words", value="3", field_name="cta")
    assert created.status_code == 201, created.text
    rule_id = created.json()["id"]
    assert created.json()["value"] == "3"

    updated = client.put(
        f"/api/v1/rules/{rule_id}", headers=admin_headers, json={"value": "2"}
    )
    assert updated.status_code == 200
    assert updated.json()["value"] == "2"

    assert client.delete(f"/api/v1/rules/{rule_id}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/v1/rules/{rule_id}", headers=admin_headers).status_code == 404


def test_marketers_cannot_manage_rules(client: TestClient, marketer_headers) -> None:
    assert create_rule(client, marketer_headers).status_code == 403


def test_viewers_can_read_rules(client: TestClient, viewer_headers) -> None:
    assert client.get("/api/v1/rules", headers=viewer_headers).status_code == 200


# -- Validation --------------------------------------------------------------
def test_numeric_rules_reject_non_numeric_values(client: TestClient, admin_headers) -> None:
    response = create_rule(client, admin_headers, value="fifty")
    assert response.status_code == 422


def test_regex_rules_reject_invalid_patterns(client: TestClient, admin_headers) -> None:
    response = create_rule(
        client, admin_headers, name="Pattern", rule_type="regex", value="([unclosed"
    )
    assert response.status_code == 422


def test_unknown_field_names_are_rejected(client: TestClient, admin_headers) -> None:
    response = create_rule(client, admin_headers, field_name="not_a_field")
    assert response.status_code == 422


def test_term_lists_are_normalised(client: TestClient, admin_headers) -> None:
    response = create_rule(
        client,
        admin_headers,
        name="Banned words",
        rule_type="forbidden_terms",
        value="  guarantee ,, cheapest  ",
        field_name=None,
    )
    assert response.status_code == 201
    assert response.json()["value"] == "guarantee, cheapest"


def test_changing_the_type_revalidates_the_existing_value(
    client: TestClient, admin_headers
) -> None:
    created = create_rule(
        client, admin_headers, name="Tone", rule_type="guideline", value="Sound natural."
    )
    rule_id = created.json()["id"]

    # "Sound natural." is not a number, so it cannot become a max_chars rule.
    response = client.put(
        f"/api/v1/rules/{rule_id}", headers=admin_headers, json={"rule_type": "max_chars"}
    )
    assert response.status_code == 422


def test_unknown_brand_reference_is_rejected(client: TestClient, admin_headers) -> None:
    assert create_rule(client, admin_headers, brand_id=9999).status_code == 422


# -- Enforcement -------------------------------------------------------------
def test_an_admin_added_rule_is_applied_to_a_generation(
    client: TestClient, admin_headers, taxonomy
) -> None:
    """The acceptance test for the feature: a rule added through the API is enforced."""
    created = create_rule(
        client,
        admin_headers,
        name="Short email headline",
        rule_type="max_chars",
        value="25",
        field_name="headline",
    )
    assert created.status_code == 201

    try:
        generation = client.post(
            "/api/v1/generations", headers=admin_headers, json=generation_payload(taxonomy)
        )
        assert generation.status_code == 202, generation.text

        status = client.get(
            f"/api/v1/generations/{generation.json()['id']}/status", headers=admin_headers
        ).json()
        assert status["status"] == "completed"
        assert len(status["output"]["email"]["headline"]) <= 25
    finally:
        # Rules are global, so leaving this one behind would constrain every
        # later test in the session.
        client.delete(f"/api/v1/rules/{created.json()['id']}", headers=admin_headers)


def test_an_inactive_rule_is_not_applied(client: TestClient, admin_headers, taxonomy) -> None:
    create_rule(
        client,
        admin_headers,
        name="Inactive limit",
        rule_type="max_chars",
        value="5",
        field_name="headline",
        is_active=False,
    )
    generation = client.post(
        "/api/v1/generations", headers=admin_headers, json=generation_payload(taxonomy)
    )
    status = client.get(
        f"/api/v1/generations/{generation.json()['id']}/status", headers=admin_headers
    ).json()
    assert len(status["output"]["email"]["headline"]) > 5


def test_the_validation_stage_reports_a_judge_score(
    client: TestClient, admin_headers, taxonomy
) -> None:
    generation = client.post(
        "/api/v1/generations", headers=admin_headers, json=generation_payload(taxonomy)
    )
    status = client.get(
        f"/api/v1/generations/{generation.json()['id']}/status", headers=admin_headers
    ).json()

    stage = next(
        step for step in status["steps"] if step["agent_name"] == "content_validation"
    )
    assert stage["status"] == "completed"
    assert status["output"]["quality"]["judge_score"] == 1.0
