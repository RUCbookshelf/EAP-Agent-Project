from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.models import AnalysisResult, DiagnosisResult, EssaySubmission, HistoryResult, ProviderResult


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
    essay_id INTEGER NOT NULL UNIQUE REFERENCES essays(essay_id),
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


class ClosingConnection(sqlite3.Connection):
    """SQLite connection that closes after the outermost context manager exits."""

    _context_depth = 0

    def __enter__(self):
        self._context_depth += 1
        return super().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self._context_depth -= 1
            if self._context_depth == 0:
                self.close()


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            from app.database.migrations import upgrade
            upgrade(connection)

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

    def record_versions(self, versions: dict[str, str]) -> None:
        with self.connect() as connection:
            connection.executemany(
                "INSERT INTO system_versions(component, version) VALUES (?, ?) "
                "ON CONFLICT(component) DO UPDATE SET version=excluded.version, recorded_at=CURRENT_TIMESTAMP",
                versions.items(),
            )

    def save_essay(self, submission: EssaySubmission, *, synthetic: bool = False) -> int:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO students(student_id, created_at, is_synthetic) VALUES (?, ?, ?)",
                (submission.student_id, submission.submitted_at.isoformat(), int(synthetic)),
            )
            cursor = connection.execute(
                """INSERT INTO essays(
                    student_id, writing_prompt, genre, draft_stage, timed, time_limit_minutes,
                    tool_use, essay_text, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    submission.student_id, submission.writing_prompt, submission.genre,
                    submission.draft_stage, int(submission.timed), submission.time_limit_minutes,
                    submission.tool_use,
                    submission.essay_text, submission.submitted_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def save_analysis(self, essay_id: int, analysis: AnalysisResult) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO metrics(essay_id, metrics_json, analysis_version, limitations) VALUES (?, ?, ?, ?)",
                (essay_id, json.dumps(analysis.metrics), analysis.analysis_version, analysis.limitations),
            )

    def save_diagnosis(self, essay_id: int, diagnosis: DiagnosisResult) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO diagnoses(essay_id, diagnosis_json, diagnosis_version) VALUES (?, ?, ?)",
                (essay_id, diagnosis.model_dump_json(), diagnosis.diagnosis_version),
            )

    def save_feedback(self, essay_id: int, result: ProviderResult, analysis_version: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO feedback_records(
                    essay_id, feedback_json, provider_name, model_name, success_status,
                    fallback_reason, prompt_version, analysis_version, system_template_hash,
                    user_template_hash, rendered_prompt_hash, schema_version, temperature,
                    request_time, response_time, validation_status, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    essay_id, result.feedback.model_dump_json(), result.provider_name,
                    result.model_name, result.success_status, result.fallback_reason,
                    result.prompt_version, analysis_version, result.system_template_hash,
                    result.user_template_hash, result.rendered_prompt_hash, result.schema_version,
                    result.temperature, result.request_time.isoformat(), result.response_time.isoformat(),
                    result.validation_status, result.retry_count,
                ),
            )
            connection.executemany(
                """INSERT INTO exercises(
                    essay_id, diagnosis_id, diagnosis_category, exercise_type, exercise_json
                ) VALUES (?, ?, ?, ?, ?)""",
                [
                    (essay_id, item.diagnosis_id, item.diagnosis_category,
                     item.exercise_type, item.model_dump_json())
                    for item in result.feedback.exercises
                ],
            )
            connection.executemany(
                """INSERT INTO llm_call_records(
                    essay_id, prompt_version, system_template_hash, user_template_hash,
                    rendered_prompt_hash, schema_version, provider_name, model_name,
                    temperature, request_time, response_time, success_status,
                    validation_status, retry_count, fallback_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        essay_id, audit.prompt_version, audit.system_template_hash,
                        audit.user_template_hash, audit.rendered_prompt_hash,
                        audit.schema_version, audit.provider_name, audit.model_name,
                        audit.temperature, audit.request_time.isoformat(),
                        audit.response_time.isoformat(), audit.success_status,
                        audit.validation_status, audit.retry_count, audit.fallback_reason,
                    )
                    for audit in result.call_audits
                ],
            )

    def save_history(self, student_id: str, essay_id: int, history: HistoryResult) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO learner_history(
                    student_id, essay_id, history_summary, comparable_count, comparability_status,
                    history_evidence_json, limitations_json, comparability_reasons_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    student_id, essay_id, history.summary, history.comparable_submission_count,
                    history.comparability_status,
                    json.dumps([item.model_dump(mode="json") for item in history.history_evidence]),
                    json.dumps(history.limitations), json.dumps(history.comparability_reasons),
                ),
            )

    def prior_records(self, submission: EssaySubmission) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT e.*, m.metrics_json, d.diagnosis_json
                FROM essays e
                LEFT JOIN metrics m ON m.essay_id = e.essay_id
                LEFT JOIN diagnoses d ON d.essay_id = e.essay_id
                WHERE e.student_id = ? AND e.submitted_at < ?
                ORDER BY e.submitted_at, e.essay_id""",
                (submission.student_id, submission.submitted_at.isoformat()),
            ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["metrics"] = json.loads(record.pop("metrics_json")) if record.get("metrics_json") else {}
            record["diagnosis"] = json.loads(record.pop("diagnosis_json")) if record.get("diagnosis_json") else {}
            records.append(record)
        return records

    def counts(self) -> dict[str, int]:
        tables = ("students", "essays", "metrics", "diagnoses", "feedback_records", "exercises", "learner_history", "llm_call_records", "system_versions")
        with self.connect() as connection:
            return {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}

    def get_feedback_record(self, essay_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM feedback_records WHERE essay_id = ?", (essay_id,)).fetchone()
        return dict(row) if row else None

    def get_llm_calls(self, essay_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM llm_call_records WHERE essay_id = ? ORDER BY call_id", (essay_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_history_record(self, essay_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learner_history WHERE essay_id = ?", (essay_id,)
            ).fetchone()
        return dict(row) if row else None

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
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_student(self, student_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT s.student_id, s.created_at, s.is_synthetic,
                COUNT(e.essay_id) AS submission_count
                FROM students s LEFT JOIN essays e ON e.student_id=s.student_id
                WHERE s.student_id=? GROUP BY s.student_id""",
                (student_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT e.*, m.metrics_json, m.analysis_version, m.limitations AS analysis_limitations,
                d.diagnosis_json, f.feedback_json, f.provider_name, f.model_name,
                f.success_status, f.fallback_reason, f.prompt_version, f.schema_version,
                f.validation_status, f.retry_count, h.history_summary, h.comparable_count,
                h.comparability_status, h.history_evidence_json, h.limitations_json,
                h.comparability_reasons_json
                FROM essays e
                LEFT JOIN metrics m ON m.essay_id=e.essay_id
                LEFT JOIN diagnoses d ON d.essay_id=e.essay_id
                LEFT JOIN feedback_records f ON f.essay_id=e.essay_id
                LEFT JOIN learner_history h ON h.essay_id=e.essay_id
                WHERE e.essay_id=?""",
                (essay_id,),
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        for key in ("metrics_json", "diagnosis_json", "feedback_json", "history_evidence_json", "limitations_json", "comparability_reasons_json"):
            raw = result.pop(key, None)
            result[key.removesuffix("_json")] = json.loads(raw) if raw else None
        result["timed"] = bool(result["timed"])
        return result

    def list_student_submissions(self, student_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT essay_id, student_id, writing_prompt, genre, draft_stage, timed, time_limit_minutes, tool_use, submitted_at FROM essays WHERE student_id=? ORDER BY submitted_at, essay_id",
                (student_id,),
            ).fetchall()
        return [{**dict(row), "timed": bool(row["timed"])} for row in rows]

    def list_student_history(self, student_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM learner_history WHERE student_id=? ORDER BY created_at, history_id",
                (student_id,),
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["history_evidence"] = json.loads(item.pop("history_evidence_json"))
            item["limitations"] = json.loads(item.pop("limitations_json"))
            item["comparability_reasons"] = json.loads(item.pop("comparability_reasons_json"))
            results.append(item)
        return results

    def get_exercises(self, essay_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT exercise_json FROM exercises WHERE essay_id=? ORDER BY exercise_id", (essay_id,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get_latest_learner_profile(self, student_id: str) -> dict[str, Any] | None:
        return None

    def get_system_versions(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT component, version FROM system_versions").fetchall()
        return {row["component"]: row["version"] for row in rows}


SQLiteRepository = Database
