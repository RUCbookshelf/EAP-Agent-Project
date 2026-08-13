"""Wave-2 Goal A migration tests: additive migration 14 under LATEST=16.

Covers: fresh-DB upgrade to LATEST (15) with the four Wave-2 table families,
non-destructive one-step logical rollback chain 15->14->13 (ledger only;
tables and data preserved), idempotent re-apply, legacy-DB upgrade without
history loss, DEFAULT coverage for minimal inserts, and the v14-era upgrade
path (a genuine migration-14 database with Wave-2 rows upgraded to 16)
preserving data.

Contract (Goal PDW2-A-CORE-PERSISTENCE): migration 14 is additive and
non-destructive: it creates only new tables (writing_tasks,
submission_revisions, learning_observations, learning_items) plus indexes.
It does not alter existing table DDL and does not touch the deferred
``essays.domain`` discriminator / D-09 lanes. Under the user-authorized
Option A ledger (PDW3-WU2-LEARNER-MIGRATION16-PINS-OPTION-A-20260812),
Migration 15 is CORE-owned ``review_scheduling_foundation`` and Migration 16
is LEARNER acknowledgement persistence (``learner_acknowledgement_persistence``);
16 is the current LATEST. Historical v14-era upgrade paths must still prove
data preservation.
"""

from __future__ import annotations

import sqlite3

from app.database import Database, LATEST_MIGRATION_VERSION, rollback

MIGRATION_14_NAME = "wave2_revision_loop_and_learner_model"
MIGRATION_15_NAME = "review_scheduling_foundation"
MIGRATION_16_NAME = "learner_acknowledgement_persistence"
WAVE2_TABLES = (
    "writing_tasks",
    "submission_revisions",
    "learning_observations",
    "learning_items",
)
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


def _seed_student_and_essays(connection: sqlite3.Connection) -> None:
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


def test_fresh_db_upgrades_to_latest_with_wave2_tables(tmp_path):
    repository = Database(tmp_path / "wave2.db")
    repository.initialize()
    assert repository._system_repository.migration_version() == LATEST_MIGRATION_VERSION
    with repository.connect() as connection:
        names = _table_names(connection)
        assert set(WAVE2_TABLES) <= names
        ledger_14 = connection.execute(
            "SELECT name FROM schema_migrations WHERE version=14"
        ).fetchone()
        assert ledger_14 is not None
        assert ledger_14["name"] == MIGRATION_14_NAME
        ledger_15 = connection.execute(
            "SELECT name FROM schema_migrations WHERE version=15"
        ).fetchone()
        assert ledger_15 is not None
        assert ledger_15["name"] == MIGRATION_15_NAME
        ledger_16 = connection.execute(
            "SELECT name FROM schema_migrations WHERE version=16"
        ).fetchone()
        assert ledger_16 is not None
        assert ledger_16["name"] == MIGRATION_16_NAME
        assert set(CORE_REVIEW_TABLES) <= names
        assert "learner_acknowledgements" in names


def test_v14_era_wave2_data_survives_one_step_rollbacks_and_latest_upgrade(
    tmp_path,
):
    repository = Database(tmp_path / "rollback14.db")
    repository.initialize()
    with repository.connect() as connection:
        # Construct a genuine migration-14-era database: one-step rollbacks
        # from LATEST (16) to 15 then 14, then seed Wave-2 rows at version 14.
        assert rollback(connection, 15) == 15
        assert rollback(connection, 14) == 14
        assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == 14
        _seed_student_and_essays(connection)
        connection.execute(
            "INSERT INTO writing_tasks(task_id, student_id, writing_prompt,"
            " created_at) VALUES ('WT000001', 'S1', 'Prompt A',"
            " '2026-01-01T00:00:00+00:00')"
        )
    with repository.connect() as connection:
        # One-step logical rollback 14 -> 13: ledger only, tables and data
        # preserved.
        result = rollback(connection, 13)
        assert result == 13
        assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == 13
        assert set(WAVE2_TABLES) <= _table_names(connection)
        assert (
            connection.execute(
                "SELECT version FROM schema_migrations WHERE version=14"
            ).fetchone()
            is None
        )
        assert (
            connection.execute(
                "SELECT task_id FROM writing_tasks WHERE task_id='WT000001'"
            ).fetchone()
            is not None
        )
    # Re-apply: the v14-era Wave-2 rows must survive the 13 -> 14 -> 15 -> 16
    # upgrade (v14-era upgrade path to LATEST preserves data).
    repository.initialize()
    assert repository._system_repository.migration_version() == LATEST_MIGRATION_VERSION
    with repository.connect() as connection:
        assert (
            connection.execute(
                "SELECT task_id FROM writing_tasks WHERE task_id='WT000001'"
            ).fetchone()
            is not None
        )


def test_legacy_database_upgrades_to_latest_without_losing_history(tmp_path):
    path = tmp_path / "legacy14.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE students(
                student_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                is_synthetic INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE essays(
                essay_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL REFERENCES students(student_id),
                writing_prompt TEXT NOT NULL, genre TEXT NOT NULL,
                draft_stage TEXT NOT NULL, timed INTEGER NOT NULL,
                tool_use TEXT NOT NULL, essay_text TEXT NOT NULL,
                submitted_at TEXT NOT NULL
            );
            INSERT INTO students VALUES('LEGACY','2026-01-01T00:00:00+00:00',0);
            INSERT INTO essays(student_id,writing_prompt,genre,draft_stage,timed,
                tool_use,essay_text,submitted_at)
            VALUES('LEGACY','Prompt','argumentative essay','first draft',0,
                'none','Legacy essay.','2026-01-01T00:00:00+00:00');
            """
        )
    repository = Database(path)
    repository.initialize()
    assert repository._system_repository.migration_version() == LATEST_MIGRATION_VERSION
    assert (
        repository._submission_repository.get_submission_bundle(1)["essay_text"]
        == "Legacy essay."
    )
    with repository.connect() as connection:
        assert set(WAVE2_TABLES) <= _table_names(connection)


def test_wave2_tables_are_default_covered_for_minimal_inserts(tmp_path):
    repository = Database(tmp_path / "defaults14.db")
    repository.initialize()
    with repository.connect() as connection:
        _seed_student_and_essays(connection)
        connection.execute(
            "INSERT INTO revision_groups(revision_group_id, student_id,"
            " writing_prompt, genre, root_submission_id, created_at,"
            " updated_at, metadata_consistency_json, limitations_json)"
            " VALUES ('RG000001', 'S1', 'Prompt A', 'argumentative essay', 1,"
            " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00',"
            " '{}', '[]')"
        )
        # Minimal inserts: only NOT NULL columns without DEFAULTs are given.
        connection.execute(
            "INSERT INTO writing_tasks(task_id, student_id, writing_prompt,"
            " created_at) VALUES ('WT000001', 'S1', 'Prompt A',"
            " '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO submission_revisions(revision_link_id,"
            " revision_group_id, source_submission_id, target_submission_id,"
            " created_at) VALUES ('SR000001', 'RG000001', 1, 1,"
            " '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO learning_observations(observation_id, student_id,"
            " first_observed_at, last_observed_at, created_at)"
            " VALUES ('LO000001', 'S1', '2026-01-01T00:00:00+00:00',"
            " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO learning_items(learning_item_id, student_id,"
            " created_at, updated_at) VALUES ('LI000001', 'S1',"
            " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        task = connection.execute(
            "SELECT * FROM writing_tasks WHERE task_id='WT000001'"
        ).fetchone()
        assert task["genre"] == "argumentative essay"
        assert task["task_type"] == "independent_writing"
        assert task["modality"] == "written"
        assert task["metadata_json"] == "{}"
        assert task["limitations_json"] == "[]"
        link = connection.execute(
            "SELECT * FROM submission_revisions WHERE revision_link_id='SR000001'"
        ).fetchone()
        assert link["ancestry_json"] == "[]"
        assert link["revision_sequence"] == 1
        assert link["task_id"] is None
        assert link["analysis_run_id"] is None
        assert link["feedback_record_id"] is None
        assert link["limitations_json"] == "[]"
        observation = connection.execute(
            "SELECT * FROM learning_observations WHERE observation_id='LO000001'"
        ).fetchone()
        assert observation["observation_type"] == "difficulty"
        assert observation["evidence_refs_json"] == "[]"
        assert observation["context_json"] == "{}"
        assert observation["occurrence_count"] == 1
        assert observation["recency"] == "unknown"
        assert observation["revision_response_json"] == "{}"
        assert observation["limitations_json"] == "[]"
        item = connection.execute(
            "SELECT * FROM learning_items WHERE learning_item_id='LI000001'"
        ).fetchone()
        assert item["originating_evidence_json"] == "{}"
        assert item["feedback_reference"] is None
        assert item["revision_history_json"] == "[]"
        assert item["context_json"] == "{}"
        assert item["status"] == "proposed"
