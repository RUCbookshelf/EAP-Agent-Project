"""Migration-15 focused tests: fresh apply, idempotence, rollback safety."""

from __future__ import annotations

import sqlite3

from app.database import Database, LATEST_MIGRATION_VERSION, rollback, upgrade
from app.database.migrations import MIGRATIONS
from app.version import PLATFORM_DATABASE_MIGRATION_VERSION


def _tables(connection) -> set[str]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row["name"] for row in rows}


def test_fresh_apply_reaches_15_with_review_tables(tmp_path):
    connection = sqlite3.connect(tmp_path / "fresh.db")
    connection.row_factory = sqlite3.Row
    try:
        assert upgrade(connection) == 15
        tables = _tables(connection)
        assert {
            "practice_activities",
            "review_events",
            "learning_item_scheduler_states",
        } <= tables
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 15
        # Migration 14 tables remain intact alongside.
        assert "learning_items" in tables
        assert "writing_tasks" in tables
    finally:
        connection.close()


def test_idempotent_reapply(tmp_path):
    connection = sqlite3.connect(tmp_path / "idem.db")
    connection.row_factory = sqlite3.Row
    try:
        assert upgrade(connection) == 15
        first = _tables(connection)
        assert upgrade(connection) == 15
        assert _tables(connection) == first
        versions = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations")
        }
        assert versions == set(range(1, 16))
    finally:
        connection.close()


def test_rollback_15_to_14_is_ledger_only_and_data_safe(tmp_path):
    connection = sqlite3.connect(tmp_path / "rollback.db")
    connection.row_factory = sqlite3.Row
    try:
        assert upgrade(connection) == 15
        connection.execute(
            "INSERT INTO students(student_id, created_at, is_synthetic)"
            " VALUES ('S1', '2026-01-01T00:00:00+00:00', 0)"
        )
        connection.execute(
            "INSERT INTO learning_items("
            " learning_item_id, student_id, no_fsrs_note, no_practice_note,"
            " category, created_at, updated_at)"
            " VALUES ('LI000001','S1','note','note','grammar',"
            " '2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00')"
        )
        assert rollback(connection, 14) == 14
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 14
        tables = _tables(connection)
        assert "review_events" in tables  # preserved (ledger-only rollback)
        assert "learning_item_scheduler_states" in tables
        versions = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations")
        }
        assert 15 not in versions
        assert 14 in versions
        # Re-apply is idempotent and preserves the data row.
        assert upgrade(connection) == 15
        row = connection.execute(
            "SELECT learning_item_id FROM learning_items"
            " WHERE learning_item_id='LI000001'"
        ).fetchone()
        assert row is not None
    finally:
        connection.close()


def test_version_single_sourcing_consistent():
    assert LATEST_MIGRATION_VERSION == 15
    assert PLATFORM_DATABASE_MIGRATION_VERSION == 15


def test_database_initialize_lands_on_15(tmp_path):
    repository = Database(tmp_path / "app.db")
    repository.initialize()
    assert repository._system_repository.migration_version() == 15


def _upgrade_to(connection: sqlite3.Connection, target_version: int) -> None:
    """Apply the REAL migration functions 1..target (mirrors ``upgrade``).

    Used to build a genuine migration-14-era database: the actual migration
    functions from the MIGRATIONS registry plus the same ledger bookkeeping
    and user_version handling the production ``upgrade`` driver performs.
    No fakes or stubs: the same SQL the product runs, stopped at 14.
    """
    for version in range(1, target_version + 1):
        name, migration = MIGRATIONS[version]
        with connection:
            migration(connection)
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER"
                " PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL"
                " DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, name)"
                " VALUES (?, ?)",
                (version, name),
            )
            connection.execute(f"PRAGMA user_version = {version}")


def test_v14_era_wave2_data_survives_upgrade_to_15(tmp_path):
    """Case D: genuine migration-14 DB with Wave-2 rows -> 15, preserved.

    Seeds learning_items / writing_tasks at a REAL version-14 database
    (no review tables exist yet), then upgrades through the real ``upgrade``
    driver and asserts the Wave-2 rows and the review table families
    coexist. This closes the Phase-1 gap (inventory C2): previously only
    fresh-path and rollback/reapply preservation were tested, never a
    genuine v14-era Wave-2 data upgrade.
    """
    path = tmp_path / "v14-era.db"
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        _upgrade_to(connection, 14)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 14
        tables = _tables(connection)
        assert "review_events" not in tables
        assert "practice_activities" not in tables
        assert "learning_item_scheduler_states" not in tables
        assert "learning_items" in tables
        assert "writing_tasks" in tables

        # Seed Wave-2 rows at version 14 (real SQLite rows, real schema).
        connection.execute(
            "INSERT INTO students(student_id, created_at, is_synthetic)"
            " VALUES ('S1', '2026-01-01T00:00:00+00:00', 0)"
        )
        connection.execute(
            "INSERT INTO writing_tasks("
            " task_id, student_id, writing_prompt, writing_context, task_type,"
            " created_at)"
            " VALUES ('WT-V14-001', 'S1',"
            " 'Should cities add more parks?', 'cet6', 'argumentative',"
            " '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO learning_items("
            " learning_item_id, student_id, originating_evidence_json,"
            " task_id, category, status, created_at, updated_at)"
            " VALUES ('LI-V14-001', 'S1',"
            " '{\"source\": \"priority_plan\", \"kind\": \"l2\"}',"
            " 'WT-V14-001', 'grammar', 'proposed',"
            " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )

        # Upgrade through the REAL production driver.
        assert upgrade(connection) == 15
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 15

        # Wave-2 rows are preserved with exact content.
        task = connection.execute(
            "SELECT * FROM writing_tasks WHERE task_id='WT-V14-001'"
        ).fetchone()
        assert task is not None
        assert task["student_id"] == "S1"
        assert task["writing_prompt"] == "Should cities add more parks?"
        assert task["writing_context"] == "cet6"
        assert task["task_type"] == "argumentative"
        item = connection.execute(
            "SELECT * FROM learning_items WHERE learning_item_id='LI-V14-001'"
        ).fetchone()
        assert item is not None
        assert item["student_id"] == "S1"
        assert item["category"] == "grammar"
        assert item["task_id"] == "WT-V14-001"
        assert item["status"] == "proposed"
        assert item["no_fsrs_note"] == (
            "no FSRS scheduling or spaced-repetition state is stored in "
            "LearningItem v1"
        )
        assert item["no_practice_note"] == (
            "no practice or tutor expansion is attached to LearningItem v1"
        )

        # Review table families now coexist with the preserved Wave-2 rows.
        tables = _tables(connection)
        assert {
            "practice_activities",
            "review_events",
            "learning_item_scheduler_states",
        } <= tables
        versions = {
            row["version"]
            for row in connection.execute(
                "SELECT version FROM schema_migrations"
            )
        }
        assert versions == set(range(1, 16))

        # Re-apply remains idempotent and data-preserving.
        assert upgrade(connection) == 15
        assert connection.execute(
            "SELECT 1 FROM learning_items WHERE learning_item_id='LI-V14-001'"
        ).fetchone() is not None
    finally:
        connection.close()
