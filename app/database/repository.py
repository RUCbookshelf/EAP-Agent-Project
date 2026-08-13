from __future__ import annotations

import sqlite3
from pathlib import Path

from app.infrastructure.sqlite import SQLiteConnectionManager
from app.infrastructure.sqlite.repositories import (
    SQLiteAnalysisRepository,
    SQLiteCalfRepository,
    SQLiteConfigurationRepository,
    SQLiteLearnerRepository,
    SQLitePracticeRepository,
    SQLiteResearchRepository,
    SQLiteReviewRepository,
    SQLiteRevisionRepository,
    SQLiteSubmissionRepository,
    SQLiteSystemRepository,
    SQLiteWave2Repository,
)


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    is_synthetic INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS essays (
    essay_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL REFERENCES students(student_id),
    writing_prompt TEXT NOT NULL,
    genre TEXT NOT NULL,
    draft_stage TEXT NOT NULL,
    timed INTEGER NOT NULL,
    time_limit_minutes INTEGER,
    tool_use TEXT NOT NULL,
    essay_text TEXT NOT NULL,
    submitted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
    metrics_json TEXT NOT NULL,
    analysis_version TEXT NOT NULL,
    limitations TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS diagnoses (
    diagnosis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL UNIQUE REFERENCES essays(essay_id),
    diagnosis_json TEXT NOT NULL,
    diagnosis_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS feedback_records (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL UNIQUE REFERENCES essays(essay_id),
    feedback_json TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    success_status TEXT NOT NULL,
    fallback_reason TEXT,
    prompt_version TEXT NOT NULL,
    analysis_version TEXT NOT NULL,
    system_template_hash TEXT NOT NULL DEFAULT '',
    user_template_hash TEXT NOT NULL DEFAULT '',
    rendered_prompt_hash TEXT NOT NULL DEFAULT '',
    schema_version TEXT NOT NULL DEFAULT '',
    temperature REAL NOT NULL DEFAULT 0.0,
    request_time TEXT,
    response_time TEXT,
    validation_status TEXT NOT NULL DEFAULT 'not_run',
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS exercises (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
    diagnosis_id TEXT NOT NULL DEFAULT '',
    diagnosis_category TEXT NOT NULL,
    exercise_type TEXT NOT NULL,
    exercise_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS learner_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL REFERENCES students(student_id),
    essay_id INTEGER NOT NULL UNIQUE REFERENCES essays(essay_id),
    history_summary TEXT NOT NULL,
    comparable_count INTEGER NOT NULL,
    comparability_status TEXT NOT NULL DEFAULT 'insufficient_history',
    history_evidence_json TEXT NOT NULL DEFAULT '[]',
    limitations_json TEXT NOT NULL DEFAULT '[]',
    comparability_reasons_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS llm_call_records (
    call_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
    prompt_version TEXT NOT NULL,
    system_template_hash TEXT NOT NULL,
    user_template_hash TEXT NOT NULL,
    rendered_prompt_hash TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    temperature REAL NOT NULL,
    request_time TEXT NOT NULL,
    response_time TEXT NOT NULL,
    success_status TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    retry_count INTEGER NOT NULL,
    fallback_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS system_versions (
    component TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._connection_manager = SQLiteConnectionManager(self.path)
        self._system_repository = SQLiteSystemRepository(self._connection_manager)
        self._configuration_repository = SQLiteConfigurationRepository(self._connection_manager)
        self._analysis_repository = SQLiteAnalysisRepository(self._connection_manager)
        self._calf_repository = SQLiteCalfRepository(self._connection_manager)
        self._submission_repository = SQLiteSubmissionRepository(
            self._connection_manager, SQLiteRevisionRepository.normalize_revision_stage
        )
        self._revision_repository = SQLiteRevisionRepository(
            self._connection_manager, self._submission_repository,
            self._analysis_repository,
        )
        self._learner_repository = SQLiteLearnerRepository(
            self._connection_manager, self._analysis_repository, self._calf_repository,
            SQLiteRevisionRepository.normalize_revision_stage,
        )
        self._practice_repository = SQLitePracticeRepository(self._connection_manager)
        self._research_repository = SQLiteResearchRepository(self._connection_manager)
        self._wave2_repository = SQLiteWave2Repository(self._connection_manager)
        self._review_repository = SQLiteReviewRepository(self._connection_manager)

    def connect(self) -> sqlite3.Connection:
        return self._system_repository.connect()

    def initialize(self) -> None:
        return self._system_repository.initialize()

    @staticmethod
    def _add_column_if_missing(connection: sqlite3.Connection, table: str,
                                   column: str, definition: str) -> None:
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            if column not in columns:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _migrate_v0_1_to_v0_1_1(self, connection: sqlite3.Connection) -> None:
            additions = {
                "essays": {"time_limit_minutes": "INTEGER"},
                "feedback_records": {
                    "system_template_hash": "TEXT NOT NULL DEFAULT ''",
                    "user_template_hash": "TEXT NOT NULL DEFAULT ''",
                    "rendered_prompt_hash": "TEXT NOT NULL DEFAULT ''",
                    "schema_version": "TEXT NOT NULL DEFAULT ''",
                    "temperature": "REAL NOT NULL DEFAULT 0.0",
                    "request_time": "TEXT",
                    "response_time": "TEXT",
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
                    self._add_column_if_missing(connection, table, column, definition)
