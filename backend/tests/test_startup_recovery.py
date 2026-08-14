"""Recovery of generations interrupted by a restart, and the taxonomy-only seed."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.seed import seed_taxonomy_only
from app.database.session import SessionLocal
from app.models.enums import AgentStatus, GenerationStatus, Role
from app.models.generation import AgentExecution, Generation
from app.repositories.taxonomy_repository import BrandRepository
from app.repositories.user_repository import UserRepository
from app.services.generation_service import fail_interrupted_generations
from tests.conftest import MARKETER_EMAIL, generation_payload


def _stranded_generation(db: Session, status: GenerationStatus) -> Generation:
    """A generation stuck mid-run, as a killed process would leave it."""
    user = UserRepository(db).get_by_email(MARKETER_EMAIL)
    assert user is not None
    generation = Generation(
        user_id=user.id,
        title="Interrupted run",
        brief="A brief that never finished.",
        channel="email",
        status=status,
    )
    db.add(generation)
    db.flush()
    db.add_all(
        [
            AgentExecution(
                generation_id=generation.id,
                agent_name="data_extraction",
                sequence=1,
                status=AgentStatus.COMPLETED,
            ),
            AgentExecution(
                generation_id=generation.id,
                agent_name="copy_generation",
                sequence=2,
                status=AgentStatus.IN_PROGRESS,
            ),
            AgentExecution(
                generation_id=generation.id,
                agent_name="output_parsing",
                sequence=3,
                status=AgentStatus.PENDING,
            ),
        ]
    )
    db.commit()
    return generation


def test_running_generation_is_failed_on_startup(db: Session) -> None:
    generation = _stranded_generation(db, GenerationStatus.RUNNING)

    assert fail_interrupted_generations(db) == 1

    db.refresh(generation)
    assert generation.status == GenerationStatus.FAILED
    assert generation.error_code == "GENERATION_FAILED"
    assert "interrupted" in (generation.error_message or "").lower()


def test_pending_generation_is_failed_on_startup(db: Session) -> None:
    generation = _stranded_generation(db, GenerationStatus.PENDING)

    assert fail_interrupted_generations(db) == 1

    db.refresh(generation)
    assert generation.status == GenerationStatus.FAILED


def test_sweep_resolves_every_stage(db: Session) -> None:
    generation = _stranded_generation(db, GenerationStatus.RUNNING)

    fail_interrupted_generations(db)

    db.refresh(generation)
    by_name = {row.agent_name: row for row in generation.agent_executions}
    # The stage that was mid-flight failed; the one that never started did not.
    assert by_name["data_extraction"].status == AgentStatus.COMPLETED
    assert by_name["copy_generation"].status == AgentStatus.FAILED
    assert by_name["copy_generation"].completed_at is not None
    assert by_name["output_parsing"].status == AgentStatus.SKIPPED


def test_sweep_leaves_finished_generations_alone(client, marketer_headers, taxonomy) -> None:
    response = client.post(
        "/api/v1/generations", headers=marketer_headers, json=generation_payload(taxonomy)
    )
    assert response.status_code == 202, response.text
    generation_id = response.json()["id"]

    with SessionLocal() as session:
        assert fail_interrupted_generations(session) == 0

    status = client.get(
        f"/api/v1/generations/{generation_id}/status", headers=marketer_headers
    ).json()
    assert status["status"] == "completed"


def test_sweep_is_a_no_op_without_interrupted_runs(db: Session) -> None:
    assert fail_interrupted_generations(db) == 0


def test_taxonomy_only_seed_creates_no_accounts(db: Session) -> None:
    users = UserRepository(db)
    brands = BrandRepository(db)
    for user in users.list(limit=100)[0]:
        db.delete(user)
    for brand in brands.list(limit=100)[0]:
        db.delete(brand)
    db.commit()
    assert users.list(limit=100)[1] == 0

    seed_taxonomy_only(db)

    assert users.list(limit=100)[1] == 0
    assert brands.list(limit=100)[1] > 0


def test_taxonomy_only_seed_is_idempotent(db: Session) -> None:
    brands = BrandRepository(db)
    seed_taxonomy_only(db)
    first = brands.list(limit=100)[1]
    seed_taxonomy_only(db)
    assert brands.list(limit=100)[1] == first


def test_seed_all_still_creates_the_demo_accounts(db: Session) -> None:
    """The development path is unchanged by the taxonomy-only split."""
    users = UserRepository(db)
    admin = users.get_by_email("admin@example.com")
    assert admin is not None
    assert admin.role == Role.ADMIN
