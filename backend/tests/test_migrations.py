"""Constraints on the migration chain that only a real database would enforce."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

# Alembic's ``alembic_version.version_num`` column is VARCHAR(32). SQLite ignores
# declared string lengths, so an over-long id passes locally and fails on the first
# PostgreSQL deployment, mid-upgrade.
VERSION_NUM_MAX_LENGTH = 32

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _script_directory() -> ScriptDirectory:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return ScriptDirectory.from_config(config)


def test_revision_ids_fit_the_version_table() -> None:
    too_long = {
        revision.revision: len(revision.revision)
        for revision in _script_directory().walk_revisions()
        if len(revision.revision) > VERSION_NUM_MAX_LENGTH
    }
    assert not too_long, (
        f"Revision ids longer than {VERSION_NUM_MAX_LENGTH} characters break "
        f"'UPDATE alembic_version' on PostgreSQL: {too_long}"
    )


def test_migration_chain_is_linear_and_complete() -> None:
    """One head, one base, and every down_revision resolves."""
    script = _script_directory()
    revisions = list(script.walk_revisions())

    assert len(script.get_heads()) == 1, "the migration chain has branched"

    known = {revision.revision for revision in revisions}
    for revision in revisions:
        if revision.down_revision is not None:
            assert revision.down_revision in known, (
                f"{revision.revision} points at unknown down_revision "
                f"{revision.down_revision!r}"
            )
