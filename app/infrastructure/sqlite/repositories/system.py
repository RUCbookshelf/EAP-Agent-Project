from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from app.infrastructure.sqlite.connection import SQLiteConnectionManager


class SQLiteSystemRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    def connect(self) -> sqlite3.Connection:
        return self._connection_manager.connect()

    def initialize(self) -> None:
        with self.connect() as connection:
            from app.database.migrations import upgrade
            upgrade(connection)

    def record_versions(self, versions: dict[str, str]) -> None:
        with self.connect() as connection:
            connection.executemany(
                "INSERT INTO system_versions(component, version) VALUES (?, ?) "
                "ON CONFLICT(component) DO UPDATE SET version=excluded.version, recorded_at=CURRENT_TIMESTAMP",
                versions.items(),
            )

    def counts(self) -> dict[str, int]:
        tables = ("students", "essays", "metrics", "diagnoses", "feedback_records", "exercises", "learner_history", "llm_call_records", "learner_profile_snapshots", "analysis_runs", "metric_results", "analysis_artifacts", "revision_groups", "revision_snapshots", "diagnostic_calibrations", "system_versions")
        with self.connect() as connection:
            return {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}

    def ping(self) -> bool:
        try:
            with self.connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    def migration_version(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])

    @contextmanager
    def transaction(self):
        with self._connection_manager.transaction() as connection:
            yield connection

    def get_system_versions(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT component, version FROM system_versions").fetchall()
        return {row["component"]: row["version"] for row in rows}
