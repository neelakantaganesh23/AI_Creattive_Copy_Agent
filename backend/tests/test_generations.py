"""Generation lifecycle, persistence and role tests (§18)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.enums import AGENT_SEQUENCE
from tests.conftest import SAMPLE_BRIEF, generation_payload


def create_generation(client, headers, taxonomy, **overrides):
    response = client.post(
        "/api/v1/generations", headers=headers, json=generation_payload(taxonomy, **overrides)
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_generation_runs_every_stage(client: TestClient, marketer_headers, taxonomy) -> None:
    generation = create_generation(client, marketer_headers, taxonomy)
    status = client.get(
        f"/api/v1/generations/{generation['id']}/status", headers=marketer_headers
    ).json()

    assert status["status"] == "completed"
    assert status["progress"] == 1.0
    assert [step["sequence"] for step in status["steps"]] == [1, 2, 3, 4, 5, 6, 7]
    assert [step["agent_name"] for step in status["steps"]] == [
        "data_extraction",
        "web_search_grounding",
        "copy_generation",
        "repetition_fix",
        "cta_optimization",
        "content_validation",
        "output_parsing",
    ]
    # Grounding is disabled in tests, so that stage is skipped rather than failed.
    assert {step["status"] for step in status["steps"]} <= {"completed", "skipped"}


def test_generation_produces_all_three_channels(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    generation = create_generation(client, marketer_headers, taxonomy)
    output = client.get(
        f"/api/v1/generations/{generation['id']}", headers=marketer_headers
    ).json()["output"]

    assert set(output["email"]) == {"headline", "sub_heading", "cta"}
    assert set(output["mobile"]) == {
        "superline",
        "pre_heading",
        "headline",
        "sub_heading",
        "cta",
    }
    assert set(output["sms"]) == {"description"}
    assert output["channel"] == "email"
    assert output["provider"] == "mock"
    assert output["grounded"] is False


def test_generated_copy_respects_channel_limits(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    generation = create_generation(client, marketer_headers, taxonomy)
    output = client.get(
        f"/api/v1/generations/{generation['id']}", headers=marketer_headers
    ).json()["output"]

    limits = settings.channel_limits
    for channel, payload in (
        ("email", output["email"]),
        ("mobile", output["mobile"]),
        ("sms", output["sms"]),
    ):
        for field, value in payload.items():
            assert len(value) <= limits[channel][field], f"{channel}.{field} exceeds its limit"
    assert output["quality"]["status"] == "passed"


def test_cta_rule_overrides_the_model_output(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    generation = create_generation(client, marketer_headers, taxonomy)
    detail = client.get(
        f"/api/v1/generations/{generation['id']}", headers=marketer_headers
    ).json()

    assert detail["output"]["email"]["cta"] == "SHOP AEROFLEX RUNNING SHOES"
    cta_step = next(
        step for step in detail["agent_executions"] if step["agent_name"] == "cta_optimization"
    )
    assert cta_step["output_json"]["source"] == "deterministic"
    assert cta_step["output_json"]["rule_id"] is not None


def test_cta_falls_back_when_no_product_selected(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    generation = create_generation(
        client, marketer_headers, {}, brand_id=None, product_id=None
    )
    detail = client.get(
        f"/api/v1/generations/{generation['id']}", headers=marketer_headers
    ).json()
    assert detail["output"]["email"]["cta"] == "SHOP THE COLLECTION"


def test_regenerate_creates_a_new_generation(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    first = create_generation(client, marketer_headers, taxonomy)
    response = client.post(
        f"/api/v1/generations/{first['id']}/regenerate", headers=marketer_headers
    )
    assert response.status_code == 202
    second = response.json()
    assert second["id"] != first["id"]
    assert second["brief"] == first["brief"]


def test_repetition_fix_varies_repeated_generations(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    first = create_generation(client, marketer_headers, taxonomy)
    second = client.post(
        f"/api/v1/generations/{first['id']}/regenerate", headers=marketer_headers
    ).json()

    first_output = client.get(
        f"/api/v1/generations/{first['id']}", headers=marketer_headers
    ).json()["output"]
    second_detail = client.get(
        f"/api/v1/generations/{second['id']}", headers=marketer_headers
    ).json()

    repetition_step = next(
        step
        for step in second_detail["agent_executions"]
        if step["agent_name"] == "repetition_fix"
    )
    assert repetition_step["output_json"]["rewritten"] is True
    assert second_detail["output"]["email"]["sub_heading"] != first_output["email"]["sub_heading"]
    # The deterministic CTA survives the rewrite untouched.
    assert second_detail["output"]["email"]["cta"] == first_output["email"]["cta"]


def test_brief_below_minimum_length_is_rejected(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    response = client.post(
        "/api/v1/generations",
        headers=marketer_headers,
        json=generation_payload(taxonomy, brief="Too short"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_channel_is_rejected(client: TestClient, marketer_headers, taxonomy) -> None:
    response = client.post(
        "/api/v1/generations",
        headers=marketer_headers,
        json=generation_payload(taxonomy, channel="fax"),
    )
    assert response.status_code == 422


def test_unknown_audience_segment_is_rejected(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    response = client.post(
        "/api/v1/generations",
        headers=marketer_headers,
        json=generation_payload(taxonomy, audience_segment_id=99999),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AUDIENCE_SEGMENT"


def test_generation_is_persisted_and_listed(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    create_generation(client, marketer_headers, taxonomy)
    listing = client.get("/api/v1/generations", headers=marketer_headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["title"].startswith("We are launching")
    assert listing["items"][0]["audience_segment_name"] == "Performance Seekers"


def test_history_filters_by_channel(client: TestClient, marketer_headers, taxonomy) -> None:
    create_generation(client, marketer_headers, taxonomy, channel="email")
    create_generation(client, marketer_headers, taxonomy, channel="sms")

    email_only = client.get(
        "/api/v1/generations", headers=marketer_headers, params={"channel": "email"}
    ).json()
    assert email_only["total"] == 1
    assert email_only["items"][0]["channel"] == "email"


def test_history_search_matches_the_brief(client: TestClient, marketer_headers, taxonomy) -> None:
    create_generation(client, marketer_headers, taxonomy)
    found = client.get(
        "/api/v1/generations", headers=marketer_headers, params={"search": "aeroflex"}
    ).json()
    assert found["total"] == 1
    assert SAMPLE_BRIEF.startswith(found["items"][0]["brief"][:20])


def test_generation_requires_authentication(client: TestClient, taxonomy) -> None:
    response = client.post("/api/v1/generations", json=generation_payload(taxonomy))
    assert response.status_code == 401


def test_viewer_cannot_create_generations(client: TestClient, viewer_headers, taxonomy) -> None:
    response = client.post(
        "/api/v1/generations", headers=viewer_headers, json=generation_payload(taxonomy)
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_delete_removes_the_generation(client: TestClient, marketer_headers, taxonomy) -> None:
    generation = create_generation(client, marketer_headers, taxonomy)
    assert (
        client.delete(
            f"/api/v1/generations/{generation['id']}", headers=marketer_headers
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/generations/{generation['id']}", headers=marketer_headers
        ).status_code
        == 404
    )


def test_missing_generation_returns_not_found(client: TestClient, marketer_headers) -> None:
    response = client.get("/api/v1/generations/424242", headers=marketer_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_execution_logs_record_agent_details(
    client: TestClient, marketer_headers, taxonomy
) -> None:
    generation = create_generation(client, marketer_headers, taxonomy)
    logs = client.get(
        "/api/v1/execution-logs",
        headers=marketer_headers,
        params={"generation_id": generation["id"]},
    ).json()

    assert logs["total"] == len(AGENT_SEQUENCE)
    extraction = next(
        item for item in logs["items"] if item["agent_name"] == "data_extraction"
    )
    assert extraction["status"] == "completed"
    assert extraction["duration_ms"] is not None
    assert extraction["output_json"]["products"]
