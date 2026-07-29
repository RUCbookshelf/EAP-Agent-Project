from __future__ import annotations

import sqlite3
from collections.abc import Callable


LATEST_MIGRATION_VERSION = 4


def _add_column_if_missing(
    connection: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migration_1(connection: sqlite3.Connection) -> None:
    from app.database.repository import SCHEMA

    connection.executescript(SCHEMA)
    additions = {
        "essays": {"time_limit_minutes": "INTEGER"},
        "feedback_records": {
            "system_template_hash": "TEXT NOT NULL DEFAULT ''",
            "user_template_hash": "TEXT NOT NULL DEFAULT ''",
            "rendered_prompt_hash": "TEXT NOT NULL DEFAULT ''",
            "schema_version": "TEXT NOT NULL DEFAULT ''",
            "temperature": "REAL NOT NULL DEFAULT 0.0",
            "request_time": "TEXT", "response_time": "TEXT",
            "validation_status": "TEXT NOT NULL DEFAULT 'not_run'",
            "retry_count": "INTEGER NOT NULL DEFAULT 0",
        },
        "exercises": {"diagnosis_id": "TEXT NOT NULL DEFAULT ''"},
        "learner_history": {
            "comparability_status": "TEXT NOT NULL DEFAULT 'insufficient_history'",
            "history_evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "limitations_json": "TEXT NOT NULL DEFAULT '[]'",
            "comparability_reasons_json": "TEXT NOT NULL DEFAULT '[]'",
        },
    }
    for table, columns in additions.items():
        for column, definition in columns.items():
            _add_column_if_missing(connection, table, column, definition)


def _migration_2(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_essays_student_submitted ON essays(student_id, submitted_at)"
    )


def _migration_3(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS learner_profile_snapshots (
        snapshot_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL REFERENCES students(student_id),
        snapshot_json TEXT NOT NULL,
        analysis_version TEXT NOT NULL,
        configuration_version TEXT NOT NULL,
        included_submission_ids_json TEXT NOT NULL,
        created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_profile_student_created ON learner_profile_snapshots(student_id, created_at, snapshot_row_id)"
    )


def _migration_4(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS analysis_runs (
            analysis_run_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_run_id TEXT UNIQUE,
            essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
            analyzer_id TEXT NOT NULL,
            analyzer_version TEXT NOT NULL,
            backend TEXT NOT NULL,
            nlp_library TEXT,
            nlp_library_version TEXT,
            nlp_model_name TEXT,
            nlp_model_version TEXT,
            parameters_json TEXT NOT NULL,
            resource_versions_json TEXT NOT NULL,
            configuration_version TEXT NOT NULL,
            fallback_used INTEGER NOT NULL DEFAULT 0,
            fallback_reason TEXT,
            analysis_duration_ms REAL NOT NULL,
            limitations TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_analysis_runs_essay_created
            ON analysis_runs(essay_id, analysis_run_row_id);
        CREATE TABLE IF NOT EXISTS metric_results (
            metric_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(analysis_run_id),
            metric_id TEXT NOT NULL,
            metric_version TEXT NOT NULL,
            value_json TEXT,
            unit TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            analyzer_version TEXT NOT NULL,
            resource_versions_json TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            limitations_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_metric_results_run_metric
            ON metric_results(analysis_run_id, metric_id, metric_version);
        CREATE TABLE IF NOT EXISTS analysis_artifacts (
            artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(analysis_run_id),
            artifact_type TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            artifact_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_analysis_artifacts_run
            ON analysis_artifacts(analysis_run_id, artifact_id);
        """
    )


MIGRATIONS: dict[int, tuple[str, Callable[[sqlite3.Connection], None]]] = {
    1: ("preserve_v0_1_1_schema", _migration_1),
    2: ("cloud_ready_repository_indexes", _migration_2),
    3: ("longitudinal_profile_snapshots", _migration_3),
    4: ("versioned_nlp_analysis_runs", _migration_4),
}


def upgrade(connection: sqlite3.Connection) -> int:
    current = int(connection.execute("PRAGMA user_version").fetchone()[0])
    for version in range(current + 1, LATEST_MIGRATION_VERSION + 1):
        name, migration = MIGRATIONS[version]
        with connection:
            migration(connection)
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
                (version, name),
            )
            connection.execute(f"PRAGMA user_version = {version}")
    return int(connection.execute("PRAGMA user_version").fetchone()[0])
