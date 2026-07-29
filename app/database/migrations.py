from __future__ import annotations

import sqlite3
from collections.abc import Callable


LATEST_MIGRATION_VERSION = 2


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


MIGRATIONS: dict[int, tuple[str, Callable[[sqlite3.Connection], None]]] = {
    1: ("preserve_v0_1_1_schema", _migration_1),
    2: ("cloud_ready_repository_indexes", _migration_2),
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
