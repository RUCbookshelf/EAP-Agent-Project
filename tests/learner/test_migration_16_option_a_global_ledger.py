"""Option-A global integer ledger composition tests (LEARNER side).

Goal PDW3-WU2-LEARNER-MIGRATION16-PINS-OPTION-A-20260812.

The project keeps ONE shared integer migration ledger
(``schema_migrations.version INTEGER PRIMARY KEY`` + the ``MIGRATIONS``
registry + ``app.database.upgrade``/``rollback``). After the user-authorized
Option A decision, global Migration 15 is CORE-owned as
``review_scheduling_foundation`` and LEARNER acknowledgement persistence is
global Migration 16 as ``learner_acknowledgement_persistence``. These tests
pin the LEARNER-composed product path: MIGRATIONS[15] is the CORE-15 seam,
MIGRATIONS[16] is the learner acknowledgement migration, LATEST and the
platform constant are both 16, the fresh and v14-era upgrade paths execute
14->15->16 on ONE runner/ONE sqlite connection, and rollback 16->15->14 is
logical and non-destructive with exact ledger rows.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.database import LATEST_MIGRATION_VERSION, rollback, upgrade
from app.database import migrations as migrations_module
from app.database.migrations import MIGRATIONS
from app.version import PLATFORM_DATABASE_MIGRATION_VERSION


MIGRATION_15_NAME = "review_scheduling_foundation"
MIGRATION_16_NAME = "learner_acknowledgement_persistence"

CORE_REVIEW_TABLES = (
    "practice_activities",
    "review_events",
    "learning_item_scheduler_states",
)


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def _ledger_names(connection: sqlite3.Connection, version: int) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM schema_migrations WHERE version=?",
        (version,),
    ).fetchall()
    return [row[0] for row in rows]


def _seed_student_and_wave2_rows(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO students(student_id, created_at, is_synthetic)"
        " VALUES ('S1', '2026-01-01T00:00:00+00:00', 0)"
    )
    connection.execute(
        "INSERT INTO essays(student_id, writing_prompt, genre, draft_stage,"
        " timed, tool_use, essay_text, submitted_at)"
        " VALUES ('S1', 'Prompt A', 'argumentative essay', 'first draft',"
        " 0, 'none', 'Text one.', '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO writing_tasks(task_id, student_id, writing_prompt,"
        " created_at) VALUES ('WT000001', 'S1', 'Prompt A',"
        " '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO learning_items(learning_item_id, student_id,"
        " created_at, updated_at) VALUES ('LI000001', 'S1',"
        " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
    )


def test_global_ledger_15_and_16_identities_are_exact() -> None:
    """MIGRATIONS[15] is the CORE-15 seam; MIGRATIONS[16] is the learner
    acknowledgement persistence identity; both latest pins are 16."""
    assert LATEST_MIGRATION_VERSION == 16
    assert PLATFORM_DATABASE_MIGRATION_VERSION == 16
    assert MIGRATIONS[15][0] == MIGRATION_15_NAME
    assert MIGRATIONS[16][0] == MIGRATION_16_NAME
    # The real CORE Wave-3 WU1 body is the 15 entry (no substitute), and the
    # real learner acknowledgement body is the 16 entry.
    assert MIGRATIONS[15][1] is migrations_module._migration_15
    assert MIGRATIONS[16][1] is migrations_module._migration_16_learner_acknowledgement_persistence


def test_version_15_and_16_identities_are_unique_in_global_ledger() -> None:
    holders_15 = [
        version
        for version, (name, _) in MIGRATIONS.items()
        if name == MIGRATION_15_NAME
    ]
    holders_16 = [
        version
        for version, (name, _) in MIGRATIONS.items()
        if name == MIGRATION_16_NAME
    ]
    assert holders_15 == [15]
    assert holders_16 == [16]


def test_fresh_database_upgrades_through_14_15_to_16_with_exact_ledger(
    tmp_path,
) -> None:
    connection = sqlite3.connect(tmp_path / "fresh16.db")
    connection.row_factory = sqlite3.Row
    try:
        assert upgrade(connection) == 16
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 16
        assert _ledger_names(connection, 14) == ["wave2_revision_loop_and_learner_model"]
        assert _ledger_names(connection, 15) == [MIGRATION_15_NAME]
        assert _ledger_names(connection, 16) == [MIGRATION_16_NAME]
        names = _table_names(connection)
        assert set(CORE_REVIEW_TABLES) <= names
        assert "learner_acknowledgements" in names
        # One runner: the package-level upgrade is the module-level upgrade.
        from app.database import rollback as package_rollback
        from app.database import upgrade as package_upgrade

        assert package_upgrade is upgrade
        assert package_rollback is rollback
    finally:
        connection.close()


def test_v14_era_database_upgrades_through_15_to_16_preserving_wave2_rows(
    tmp_path,
) -> None:
    """A genuine v14-era database (Wave-2 rows, user_version=14) upgrades
    14->15->16: CORE review tables and the learner acknowledgement table are
    created, Wave-2 rows survive, and the ledger has exact 15/16 rows."""
    path = tmp_path / "v14to16.db"
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        # Build a genuine v14-era database by applying the real migrations
        # 1..14 only (rollback is ledger-only by design, so a rolled-back 16
        # database would still contain the CORE-15 tables; the genuine
        # v14-era database must never have run Migration 15/16).
        for version in range(1, 15):
            MIGRATIONS[version][1](connection)
            connection.execute(f"PRAGMA user_version={version}")
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 14
        names_at_14 = _table_names(connection)
        assert "review_events" not in names_at_14
        assert "learner_acknowledgements" not in names_at_14
        _seed_student_and_wave2_rows(connection)
        connection.commit()

        # The genuine v14-era upgrade path executes 14->15->16 on the SAME
        # runner/connection.
        assert upgrade(connection) == 16
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 16
        assert _ledger_names(connection, 15) == [MIGRATION_15_NAME]
        assert _ledger_names(connection, 16) == [MIGRATION_16_NAME]
        names = _table_names(connection)
        assert set(CORE_REVIEW_TABLES) <= names
        assert "learner_acknowledgements" in names
        # Wave-2 rows preserved byte-for-byte.
        assert (
            connection.execute(
                "SELECT task_id FROM writing_tasks WHERE task_id='WT000001'"
            ).fetchone()["task_id"]
            == "WT000001"
        )
        assert (
            connection.execute(
                "SELECT learning_item_id FROM learning_items"
                " WHERE learning_item_id='LI000001'"
            ).fetchone()["learning_item_id"]
            == "LI000001"
        )
    finally:
        connection.close()


def test_rollback_16_to_15_to_14_is_ledger_only_and_reattach_restores(
    tmp_path,
) -> None:
    """Rollback 16->15->14 is logical/non-destructive with exact ledger rows;
    re-apply restores exactly one row at 15 and one at 16."""
    connection = sqlite3.connect(tmp_path / "rollback16.db")
    connection.row_factory = sqlite3.Row
    try:
        assert upgrade(connection) == 16
        _seed_student_and_wave2_rows(connection)
        connection.execute(
            "INSERT INTO learner_acknowledgements("
            " acknowledgement_id, learner_id, source_kind,"
            " source_evidence_ids_json, evidence_status, epistemic_status,"
            " outcome_claim, provenance_json, record_version,"
            " acknowledgement_text, consent_json, recorded_at)"
            " VALUES ('ACK-16-1', 'S1', 'observed_evidence', '[]',"
            " 'verified', 'observed_descriptive', 'none', '{}',"
            " 'acknowledgement-record-v0.1.0', 'Descriptive text.', '{}',"
            " '2026-08-12T00:00:00+00:00')"
        )
        connection.commit()

        assert rollback(connection, 15) == 15
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 15
        assert _ledger_names(connection, 15) == [MIGRATION_15_NAME]
        assert _ledger_names(connection, 16) == []
        # Logical rollback: CORE tables and acknowledgement data are kept.
        assert set(CORE_REVIEW_TABLES) <= _table_names(connection)
        assert (
            connection.execute(
                "SELECT acknowledgement_id FROM learner_acknowledgements"
            ).fetchone()[0]
            == "ACK-16-1"
        )

        assert rollback(connection, 14) == 14
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 14
        assert _ledger_names(connection, 15) == []
        assert _ledger_names(connection, 16) == []
        assert set(CORE_REVIEW_TABLES) <= _table_names(connection)
        assert (
            connection.execute(
                "SELECT acknowledgement_id FROM learner_acknowledgements"
            ).fetchone()[0]
            == "ACK-16-1"
        )

        # Idempotent re-apply restores the exact ledger rows and preserves
        # the acknowledgement data.
        assert upgrade(connection) == 16
        assert _ledger_names(connection, 15) == [MIGRATION_15_NAME]
        assert _ledger_names(connection, 16) == [MIGRATION_16_NAME]
        assert (
            connection.execute(
                "SELECT acknowledgement_id FROM learner_acknowledgements"
            ).fetchone()[0]
            == "ACK-16-1"
        )
    finally:
        connection.close()


def test_non_adjacent_rollback_from_16_is_rejected(tmp_path) -> None:
    connection = sqlite3.connect(tmp_path / "nonadj16.db")
    connection.row_factory = sqlite3.Row
    try:
        assert upgrade(connection) == 16
        with pytest.raises(ValueError, match="one-step"):
            rollback(connection, 13)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 16
    finally:
        connection.close()


def test_learner_composed_guard_rejects_15_rename_and_16_duplicate(
    monkeypatch,
) -> None:
    """The composed-path guards fail fast on a renamed 15, a missing 16, or a
    duplicated identity -- the same protection the CORE guard provides."""
    from app.database.migrations import (
        assert_global_migration_15_identity,
        assert_global_migration_16_identity,
    )

    assert assert_global_migration_15_identity() == (15, MIGRATION_15_NAME)
    assert assert_global_migration_16_identity() == (16, MIGRATION_16_NAME)

    monkeypatch.setitem(
        MIGRATIONS,
        15,
        (MIGRATION_16_NAME, migrations_module._migration_15),
    )
    with pytest.raises(RuntimeError, match=MIGRATION_15_NAME):
        assert_global_migration_15_identity()
    monkeypatch.undo()

    # A second holder of the LEARNER identity at another version is rejected
    # by the uniqueness check (the 16 entry itself stays correct).
    monkeypatch.setitem(
        MIGRATIONS,
        17,
        (MIGRATION_16_NAME, migrations_module._migration_16_learner_acknowledgement_persistence),
    )
    with pytest.raises(RuntimeError, match="not unique"):
        assert_global_migration_16_identity()
