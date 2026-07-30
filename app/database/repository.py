from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core import LearnerProfileSnapshot
from app.models import AnalysisResult, DiagnosisResult, EssaySubmission, HistoryResult, ProviderResult
from app.revision import RevisionGroup, RevisionSnapshot
from app.configuration import ConfigurationCreate, ConfigurationPayload, ConfigurationVersion, configuration_hash
from app.calibration import DiagnosticCalibrationResult
from app.calf import ErrorAnnotation


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
                    tool_use, essay_text, submitted_at, original_draft_stage, revision_stage,
                    writing_started_at, writing_submitted_at, active_writing_duration_seconds,
                    timing_source, timing_quality, unexplained_interruption
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    submission.student_id, submission.writing_prompt, submission.genre,
                    submission.draft_stage, int(submission.timed), submission.time_limit_minutes,
                    submission.tool_use,
                    submission.essay_text, submission.submitted_at.isoformat(),
                    submission.draft_stage, self.normalize_revision_stage(submission.draft_stage),
                    submission.writing_started_at.isoformat() if submission.writing_started_at else None,
                    submission.writing_submitted_at.isoformat() if submission.writing_submitted_at else None,
                    submission.active_writing_duration_seconds, submission.timing_source,
                    submission.timing_quality, int(submission.unexplained_interruption),
                ),
            )
            return int(cursor.lastrowid)

    def save_analysis(self, essay_id: int, analysis: AnalysisResult) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO metrics(essay_id, metrics_json, analysis_version, limitations) VALUES (?, ?, ?, ?)",
                (essay_id, json.dumps(analysis.metrics), analysis.analysis_version, analysis.limitations),
            )

    def save_analysis_run(self, essay_id: int, analysis: AnalysisResult) -> AnalysisResult:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO analysis_runs(
                    essay_id, analyzer_id, analyzer_version, backend, nlp_library,
                    nlp_library_version, nlp_model_name, nlp_model_version, parameters_json,
                    resource_versions_json, configuration_version, fallback_used, fallback_reason,
                    analysis_duration_ms, limitations, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    essay_id, analysis.analyzer_id, analysis.analyzer_version, analysis.backend,
                    analysis.nlp_library, analysis.nlp_library_version, analysis.nlp_model_name,
                    analysis.nlp_model_version, json.dumps(analysis.parameters),
                    json.dumps(analysis.resource_versions), analysis.configuration_version,
                    int(analysis.fallback_used), analysis.fallback_reason,
                    analysis.analysis_duration_ms, analysis.limitations, analysis.created_at.isoformat(),
                ),
            )
            run_id = f"AR{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE analysis_runs SET analysis_run_id=? WHERE analysis_run_row_id=?",
                (run_id, int(cursor.lastrowid)),
            )
            for item in analysis.metric_results:
                connection.execute(
                    """INSERT INTO metric_results(
                        analysis_run_id, metric_id, metric_version, value_json, unit,
                        parameters_json, analyzer_version, resource_versions_json,
                        verification_status, status, measurement_status, confidence,
                        confidence_reasons_json, risk_factors_json, eligible_for_diagnosis,
                        eligible_for_longitudinal_comparison, measurement_metadata_json,
                        evidence_json, limitations_json, construct_id, subconstruct_id,
                        automation_level, analysis_unit_version, numerator_json, denominator_json,
                        intermediate_values_json, eligible_for_revision_priority,
                        eligible_for_targeted_practice
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id, item["metric_id"], item["metric_version"], json.dumps(item.get("value")),
                        item["unit"], json.dumps(item.get("parameters", {})), item["analyzer_version"],
                        json.dumps(item.get("resource_versions", {})), item["verification_status"],
                        item.get("status", "available"), item.get("measurement_status", item.get("status", "available")),
                        item.get("confidence", "insufficient"), json.dumps(item.get("confidence_reasons", [])),
                        json.dumps(item.get("risk_factors", [])), int(item.get("eligible_for_diagnosis", False)),
                        int(item.get("eligible_for_longitudinal_comparison", False)),
                        json.dumps(item.get("measurement_metadata", {})), json.dumps(item.get("evidence", [])),
                        json.dumps(item.get("limitations", [])),
                        item.get("construct_id"), item.get("subconstruct_id"), item.get("automation_level"),
                        item.get("analysis_unit_version"), json.dumps(item.get("numerator")),
                        json.dumps(item.get("denominator")), json.dumps(item.get("intermediate_values", {})),
                        int(item.get("eligible_for_revision_priority", False)),
                        int(item.get("eligible_for_targeted_practice", False)),
                    ),
                )
            artifact_payload = {
                "input_quality": analysis.input_quality, "artifacts": analysis.artifacts,
                "legacy_metrics": analysis.metrics,
            }
            connection.execute(
                "INSERT INTO analysis_artifacts(analysis_run_id, artifact_type, schema_version, artifact_json) VALUES (?, ?, ?, ?)",
                (run_id, "nlp_analysis", "nlp-analysis-artifact-v0.4.0", json.dumps(artifact_payload)),
            )
            for unit in analysis.artifacts.get("analysis_units", []):
                cursor = connection.execute(
                    """INSERT INTO analysis_units(
                        submission_id,analysis_run_id,unit_id,unit_version,validation_status,unit_json
                    ) VALUES (?,?,?,?,?,?)""",
                    (essay_id, run_id, unit["unit_id"], unit["unit_version"],
                     unit["validation_status"], json.dumps(unit)),
                )
                unit_id = f"AU{int(cursor.lastrowid):06d}"
                stored = {**unit, "unit_record_id": unit_id, "submission_id": essay_id, "analysis_run_id": run_id}
                connection.execute(
                    "UPDATE analysis_units SET analysis_unit_id=?, unit_json=? WHERE analysis_unit_row_id=?",
                    (unit_id, json.dumps(stored), int(cursor.lastrowid)),
                )
        return analysis.model_copy(update={"analysis_run_id": run_id})

    def list_analysis_runs(self, essay_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM analysis_runs WHERE essay_id=? ORDER BY analysis_run_row_id", (essay_id,)
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["fallback_used"] = bool(item["fallback_used"])
            item["parameters"] = json.loads(item.pop("parameters_json"))
            item["resource_versions"] = json.loads(item.pop("resource_versions_json"))
            results.append(item)
        return results

    def get_latest_analysis_run(self, essay_id: int) -> dict[str, Any] | None:
        runs = self.list_analysis_runs(essay_id)
        if not runs:
            return None
        item = runs[-1]
        item["artifact"] = self.get_analysis_artifact(item["analysis_run_id"])
        item["metric_results"] = self.get_metric_results(item["analysis_run_id"])
        return item

    def get_analysis_run(self, analysis_run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT essay_id FROM analysis_runs WHERE analysis_run_id=?", (analysis_run_id,)
            ).fetchone()
        if row is None:
            return None
        return next(
            (item for item in self.list_analysis_runs(int(row[0])) if item["analysis_run_id"] == analysis_run_id),
            None,
        )

    def get_metric_results(self, analysis_run_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM metric_results WHERE analysis_run_id=? ORDER BY metric_result_id",
                (analysis_run_id,),
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            for name in ("value_json", "parameters_json", "resource_versions_json", "confidence_reasons_json",
                         "risk_factors_json", "measurement_metadata_json", "evidence_json", "limitations_json",
                         "numerator_json", "denominator_json", "intermediate_values_json"):
                item[name.removesuffix("_json")] = json.loads(item.pop(name))
            item["eligible_for_diagnosis"] = bool(item.get("eligible_for_diagnosis"))
            item["eligible_for_longitudinal_comparison"] = bool(item.get("eligible_for_longitudinal_comparison"))
            item["eligible_for_revision_priority"] = bool(item.get("eligible_for_revision_priority"))
            item["eligible_for_targeted_practice"] = bool(item.get("eligible_for_targeted_practice"))
            results.append(item)
        return results

    def get_analysis_artifact(self, analysis_run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT artifact_json FROM analysis_artifacts WHERE analysis_run_id=? ORDER BY artifact_id DESC LIMIT 1",
                (analysis_run_id,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_diagnosis(self, essay_id: int, diagnosis: DiagnosisResult) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO diagnoses(essay_id, diagnosis_json, diagnosis_version) VALUES (?, ?, ?)",
                (essay_id, diagnosis.model_dump_json(), diagnosis.diagnosis_version),
            )

    def save_diagnostic_calibration(self, essay_id: int,
                                    calibration: DiagnosticCalibrationResult) -> DiagnosticCalibrationResult:
        persisted = calibration.model_copy(update={"essay_id": essay_id})
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO diagnostic_calibrations(
                    essay_id,analysis_run_id,calibration_json,calibration_version,gate_version,
                    priority_version,evidence_validation_version,diagnosis_version,
                    configuration_version,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (essay_id, persisted.analysis_run_id, persisted.model_dump_json(),
                 persisted.calibration_version, persisted.gate_version, persisted.priority_version,
                 persisted.evidence_validation_version, persisted.diagnosis_version,
                 persisted.configuration_version, persisted.created_at.isoformat()),
            )
            calibration_id = f"DC{int(cursor.lastrowid):06d}"
            persisted = persisted.model_copy(update={"calibration_id": calibration_id})
            connection.execute(
                "UPDATE diagnostic_calibrations SET calibration_id=?, calibration_json=? WHERE calibration_row_id=?",
                (calibration_id, persisted.model_dump_json(), int(cursor.lastrowid)),
            )
        return persisted

    def get_diagnostic_calibration(self, essay_id: int) -> DiagnosticCalibrationResult | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT calibration_json FROM diagnostic_calibrations WHERE essay_id=? ORDER BY calibration_row_id DESC LIMIT 1",
                (essay_id,),
            ).fetchone()
        return DiagnosticCalibrationResult.model_validate_json(row[0]) if row else None

    def save_feedback(self, essay_id: int, result: ProviderResult, analysis_version: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO feedback_records(
                    essay_id, feedback_json, provider_name, model_name, success_status,
                    fallback_reason, prompt_version, analysis_version, system_template_hash,
                    user_template_hash, rendered_prompt_hash, schema_version, temperature,
                    request_time, response_time, validation_status, retry_count, provider_status_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    essay_id, result.feedback.model_dump_json(), result.provider_name,
                    result.model_name, result.success_status, result.fallback_reason,
                    result.prompt_version, analysis_version, result.system_template_hash,
                    result.user_template_hash, result.rendered_prompt_hash, result.schema_version,
                    result.temperature, result.request_time.isoformat(), result.response_time.isoformat(),
                    result.validation_status, result.retry_count,
                    result.feedback_provider_status.model_dump_json() if result.feedback_provider_status else "{}",
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
        tables = ("students", "essays", "metrics", "diagnoses", "feedback_records", "exercises", "learner_history", "llm_call_records", "learner_profile_snapshots", "analysis_runs", "metric_results", "analysis_artifacts", "revision_groups", "revision_snapshots", "diagnostic_calibrations", "system_versions")
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

    def list_all_students(self):
        with self.connect() as connection:
            rows = connection.execute("SELECT DISTINCT student_id FROM essays ORDER BY student_id").fetchall()
            return [{"student_id": r[0]} for r in rows]

    def list_all_submissions(self):
        with self.connect() as connection:
            rows = connection.execute("SELECT essay_id, student_id, writing_prompt, genre, draft_stage, timed, time_limit_minutes, tool_use, submitted_at, revision_of_submission_id, revision_group_id, essay_text FROM essays ORDER BY essay_id").fetchall()
            return [dict(r) for r in rows]

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT e.*, m.metrics_json, m.analysis_version, m.limitations AS analysis_limitations,
                d.diagnosis_json, d.diagnosis_version, f.feedback_json, f.provider_name, f.model_name,
                f.feedback_id,
                f.success_status, f.fallback_reason, f.prompt_version, f.schema_version,
                f.validation_status, f.retry_count, f.provider_status_json,
                h.history_summary, h.comparable_count,
                h.comparability_status, h.history_evidence_json, h.limitations_json,
                h.comparability_reasons_json
                FROM essays e
                LEFT JOIN metrics m ON m.essay_id=e.essay_id
                LEFT JOIN diagnoses d ON d.essay_id=e.essay_id
                LEFT JOIN feedback_records f ON f.feedback_id=(
                    SELECT MAX(f2.feedback_id) FROM feedback_records f2 WHERE f2.essay_id=e.essay_id
                )
                LEFT JOIN learner_history h ON h.essay_id=e.essay_id
                WHERE e.essay_id=?""",
                (essay_id,),
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        for key in ("metrics_json", "diagnosis_json", "feedback_json", "provider_status_json", "history_evidence_json", "limitations_json", "comparability_reasons_json"):
            raw = result.pop(key, None)
            result[key.removesuffix("_json")] = json.loads(raw) if raw else None
        result["timed"] = bool(result["timed"])
        result["unexplained_interruption"] = bool(result.get("unexplained_interruption"))
        return result

    def list_student_submissions(self, student_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT essay_id, student_id, writing_prompt, genre, draft_stage, timed,
                   time_limit_minutes, tool_use, submitted_at, revision_of_submission_id,
                   revision_group_id, revision_sequence, revision_stage, original_draft_stage,
                   writing_started_at, writing_submitted_at, active_writing_duration_seconds,
                   timing_source, timing_quality, unexplained_interruption
                   FROM essays WHERE student_id=? ORDER BY submitted_at, essay_id""",
                (student_id,),
            ).fetchall()
        return [{**dict(row), "timed": bool(row["timed"]),
                 "unexplained_interruption": bool(row["unexplained_interruption"])} for row in rows]

    def list_analysis_units(self, submission_id: int, analysis_run_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as connection:
            if analysis_run_id:
                rows = connection.execute(
                    "SELECT unit_json FROM analysis_units WHERE submission_id=? AND analysis_run_id=? ORDER BY analysis_unit_row_id",
                    (submission_id, analysis_run_id),
                ).fetchall()
            else:
                latest = connection.execute(
                    "SELECT analysis_run_id FROM analysis_runs WHERE essay_id=? ORDER BY analysis_run_row_id DESC LIMIT 1",
                    (submission_id,),
                ).fetchone()
                if latest is None:
                    return []
                rows = connection.execute(
                    "SELECT unit_json FROM analysis_units WHERE submission_id=? AND analysis_run_id=? ORDER BY analysis_unit_row_id",
                    (submission_id, latest[0]),
                ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_error_annotations(self, submission_id: int, annotations: list[ErrorAnnotation]) -> list[ErrorAnnotation]:
        stored: list[ErrorAnnotation] = []
        with self.connect() as connection:
            if connection.execute("SELECT 1 FROM essays WHERE essay_id=?", (submission_id,)).fetchone() is None:
                raise LookupError("Submission not found.")
            for annotation in annotations:
                if annotation.submission_id != submission_id:
                    raise ValueError("Error annotation submission_id does not match the route submission.")
                cursor = connection.execute(
                    """INSERT INTO error_annotations(
                        submission_id,start_offset,end_offset,annotation_source,annotation_status,
                        eligible_for_formal_accuracy,annotation_json
                    ) VALUES (?,?,?,?,?,?,?)""",
                    (submission_id, annotation.start_offset, annotation.end_offset,
                     annotation.annotation_source, annotation.annotation_status,
                     int(annotation.eligible_for_formal_accuracy),
                     annotation.model_dump_json(exclude={"eligible_for_formal_accuracy"})),
                )
                annotation_id = f"EA{int(cursor.lastrowid):06d}"
                item = annotation.model_copy(update={"error_annotation_id": annotation_id})
                connection.execute(
                    "UPDATE error_annotations SET error_annotation_id=?, annotation_json=? WHERE error_annotation_row_id=?",
                    (annotation_id, item.model_dump_json(exclude={"eligible_for_formal_accuracy"}), int(cursor.lastrowid)),
                )
                stored.append(item)
        return stored

    def list_error_annotations(self, submission_id: int) -> list[ErrorAnnotation]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT annotation_json FROM error_annotations WHERE submission_id=? ORDER BY error_annotation_row_id",
                (submission_id,),
            ).fetchall()
        return [ErrorAnnotation.model_validate_json(row[0]) for row in rows]

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
        with self.connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM learner_profile_snapshots WHERE student_id=? ORDER BY snapshot_row_id DESC LIMIT 1",
                (student_id,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_learner_profile_snapshot(self, snapshot: LearnerProfileSnapshot) -> LearnerProfileSnapshot:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO learner_profile_snapshots(
                student_id, snapshot_json, analysis_version, configuration_version,
                included_submission_ids_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    snapshot.student_id, snapshot.model_dump_json(), snapshot.analysis_version,
                    snapshot.configuration_version, json.dumps(snapshot.included_submission_ids),
                    snapshot.snapshot_time.isoformat(),
                ),
            )
            snapshot_id = (
                f"LPS{int(cursor.lastrowid):06d}"
                if snapshot.profile_version == "learner-profile-v0.7.0"
                else f"LP{int(cursor.lastrowid):06d}"
            )
            stored = snapshot.model_copy(update={"snapshot_id": snapshot_id})
            connection.execute(
                """UPDATE learner_profile_snapshots SET snapshot_json=?, profile_version=?,
                   source_submission_ids_json=?, representative_submission_ids_json=?
                   WHERE snapshot_row_id=?""",
                (stored.model_dump_json(), stored.profile_version,
                 json.dumps(stored.source_submission_ids),
                 json.dumps(stored.representative_submission_ids), int(cursor.lastrowid)),
            )
            for evidence in stored.history_evidence:
                evidence_cursor = connection.execute(
                    """INSERT INTO history_evidence_registry(
                        student_id,snapshot_id,task_cluster_id,evidence_type,evidence_json,
                        registry_version,created_at
                    ) VALUES (?,?,?,?,?,?,?)""",
                    (stored.student_id, snapshot_id, evidence.task_cluster_id,
                     evidence.evidence_type, evidence.model_dump_json(), evidence.registry_version,
                     stored.snapshot_time.isoformat()),
                )
                evidence_id = f"HE{int(evidence_cursor.lastrowid):06d}"
                persisted = evidence.model_copy(update={"history_evidence_id": evidence_id,
                                                        "source_snapshot_id": snapshot_id})
                connection.execute(
                    """UPDATE history_evidence_registry
                       SET history_evidence_id=?, evidence_json=? WHERE history_evidence_row_id=?""",
                    (evidence_id, persisted.model_dump_json(), int(evidence_cursor.lastrowid)),
                )
            if stored.history_evidence:
                rows = connection.execute(
                    "SELECT evidence_json FROM history_evidence_registry WHERE snapshot_id=? ORDER BY history_evidence_row_id",
                    (snapshot_id,),
                ).fetchall()
                persisted_evidence = [json.loads(row[0]) for row in rows]
                evidence_ids = [item["history_evidence_id"] for item in persisted_evidence]
                targets = []
                for target in stored.current_learning_targets:
                    mapped = []
                    for value in target.history_evidence_ids:
                        if value.startswith("PENDING-"):
                            position = int(value.split("-", 1)[1]) - 1
                            if 0 <= position < len(evidence_ids):
                                mapped.append(evidence_ids[position])
                        else:
                            mapped.append(value)
                    targets.append(target.model_copy(update={"history_evidence_ids": mapped}))
                stored = LearnerProfileSnapshot.model_validate({
                    **stored.model_dump(mode="python"),
                    "history_evidence": persisted_evidence,
                    "current_learning_targets": targets,
                })
                connection.execute(
                    "UPDATE learner_profile_snapshots SET snapshot_json=? WHERE snapshot_row_id=?",
                    (stored.model_dump_json(), int(cursor.lastrowid)),
                )
        return stored

    def list_history_evidence(self, student_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT evidence_json FROM history_evidence_registry WHERE student_id=? ORDER BY history_evidence_row_id",
                (student_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def list_learner_profile_snapshots(self, student_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT snapshot_json FROM learner_profile_snapshots WHERE student_id=? ORDER BY snapshot_row_id",
                (student_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def list_longitudinal_records(self, student_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT e.*, m.metrics_json, m.analysis_version,
                d.diagnosis_json, d.diagnosis_version
                FROM essays e
                JOIN metrics m ON m.essay_id=e.essay_id
                JOIN diagnoses d ON d.essay_id=e.essay_id
                WHERE e.student_id=? ORDER BY e.submitted_at, e.essay_id""",
                (student_id,),
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["metrics"] = json.loads(item.pop("metrics_json"))
            item["diagnosis"] = json.loads(item.pop("diagnosis_json"))
            item["timed"] = bool(item["timed"])
            results.append(item)
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in results:
            group_id = item.get("revision_group_id")
            if group_id:
                groups.setdefault(str(group_id), []).append(item)
        representative_ids: set[int] = set()
        for members in groups.values():
            final_drafts = [
                item for item in members
                if self.normalize_revision_stage(str(item.get("revision_stage") or "")) == "final_draft"
            ]
            candidates = final_drafts or members
            representative = max(
                candidates,
                key=lambda item: (int(item.get("revision_sequence") or 0), int(item["essay_id"])),
            )
            representative_ids.add(int(representative["essay_id"]))
        for item in results:
            group_id = item.get("revision_group_id")
            is_representative = not group_id or int(item["essay_id"]) in representative_ids
            item["is_longitudinal_representative"] = is_representative
            item["revision_exclusion_reason"] = (
                None if is_representative else
                "An earlier draft in the same Revision Group is excluded from the default long-term trend."
            )
        return results

    def get_system_versions(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT component, version FROM system_versions").fetchall()
        return {row["component"]: row["version"] for row in rows}

    @staticmethod
    def normalize_revision_stage(value: str) -> str:
        normalized = value.strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "first": "first_draft", "first_draft": "first_draft",
            "revised": "revised_draft", "revision": "revised_draft", "revised_draft": "revised_draft",
            "final": "final_draft", "final_draft": "final_draft",
            "independent": "independent_submission", "independent_submission": "independent_submission",
        }
        return aliases.get(normalized, "independent_submission")

    def create_revision_group(self, source_submission_id: int) -> RevisionGroup:
        existing = self.get_revision_group_for_submission(source_submission_id)
        if existing:
            return existing
        source = self.get_submission_bundle(source_submission_id)
        if source is None:
            raise LookupError("Source submission not found.")
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        consistency = {"writing_prompt": True, "genre": True, "timed": True, "time_limit_minutes": True, "tool_use": True}
        limitations = ["Revision grouping is explicit metadata, not evidence of learning or proficiency change."]
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO revision_groups(
                    student_id, writing_prompt, genre, root_submission_id, created_at, updated_at,
                    metadata_consistency_json, limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (source["student_id"], source["writing_prompt"], source["genre"], source_submission_id,
                 now, now, json.dumps(consistency), json.dumps(limitations)),
            )
            group_id = f"RG{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE revision_groups SET revision_group_id=? WHERE revision_group_row_id=?",
                (group_id, int(cursor.lastrowid)),
            )
            connection.execute(
                "UPDATE essays SET revision_group_id=?, revision_sequence=1, revision_stage=? WHERE essay_id=?",
                (group_id, self.normalize_revision_stage(source["draft_stage"]), source_submission_id),
            )
        group = self.get_revision_group(group_id)
        assert group is not None
        return group

    def link_revision(self, source_submission_id: int, target_submission_id: int, revision_group_id: str) -> None:
        source = self.get_submission_bundle(source_submission_id)
        target = self.get_submission_bundle(target_submission_id)
        if source is None or target is None:
            raise LookupError("Source or target submission not found.")
        sequence = int(source.get("revision_sequence") or 1) + 1
        consistency = {
            field: source.get(field) == target.get(field)
            for field in ("writing_prompt", "genre", "timed", "time_limit_minutes", "tool_use")
        }
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """UPDATE essays SET revision_of_submission_id=?, revision_group_id=?,
                   revision_sequence=?, revision_stage=? WHERE essay_id=?""",
                (source_submission_id, revision_group_id, sequence,
                 self.normalize_revision_stage(target["draft_stage"]), target_submission_id),
            )
            connection.execute(
                "UPDATE revision_groups SET updated_at=?, metadata_consistency_json=? WHERE revision_group_id=?",
                (now, json.dumps(consistency), revision_group_id),
            )

    def get_revision_group(self, revision_group_id: str) -> RevisionGroup | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM revision_groups WHERE revision_group_id=?", (revision_group_id,)).fetchone()
            members = connection.execute(
                "SELECT essay_id FROM essays WHERE revision_group_id=? ORDER BY revision_sequence, essay_id", (revision_group_id,)
            ).fetchall() if row else []
        if not row:
            return None
        item = dict(row)
        member_ids = [int(member[0]) for member in members]
        return RevisionGroup(
            revision_group_id=item["revision_group_id"], student_id=item["student_id"],
            writing_prompt=item["writing_prompt"], genre=item["genre"], root_submission_id=item["root_submission_id"],
            member_submission_ids=member_ids, current_revision_id=member_ids[-1],
            created_at=item["created_at"], updated_at=item["updated_at"],
            metadata_consistency=json.loads(item["metadata_consistency_json"]),
            limitations=json.loads(item["limitations_json"]),
        )

    def get_revision_group_for_submission(self, submission_id: int) -> RevisionGroup | None:
        with self.connect() as connection:
            row = connection.execute("SELECT revision_group_id FROM essays WHERE essay_id=?", (submission_id,)).fetchone()
        return self.get_revision_group(row[0]) if row and row[0] else None

    def list_revision_candidates(self, submission_id: int) -> list[dict[str, Any]]:
        target = self.get_submission_bundle(submission_id)
        if target is None:
            raise LookupError("Submission not found.")
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT essay_id, submitted_at, writing_prompt, genre, draft_stage, revision_group_id,
                   revision_sequence FROM essays WHERE student_id=? AND essay_id<>? AND submitted_at<=?
                   ORDER BY submitted_at DESC, essay_id DESC""",
                (target["student_id"], submission_id, target["submitted_at"]),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_revision_snapshot(self, snapshot: RevisionSnapshot) -> RevisionSnapshot:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO revision_snapshots(
                    revision_group_id, source_submission_id, target_submission_id, snapshot_json,
                    alignment_version, uptake_version, configuration_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (snapshot.revision_group_id, snapshot.source_submission_id, snapshot.target_submission_id,
                 snapshot.model_dump_json(), snapshot.algorithm_versions["alignment"],
                 snapshot.algorithm_versions["uptake"], snapshot.configuration_version,
                 snapshot.generated_at.isoformat()),
            )
            snapshot_id = f"RS{int(cursor.lastrowid):06d}"
            stored = snapshot.model_copy(update={"revision_snapshot_id": snapshot_id})
            connection.execute(
                "UPDATE revision_snapshots SET revision_snapshot_id=?, snapshot_json=? WHERE revision_snapshot_row_id=?",
                (snapshot_id, stored.model_dump_json(), int(cursor.lastrowid)),
            )
        return stored

    def list_revision_snapshots(self, revision_group_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT snapshot_json FROM revision_snapshots WHERE revision_group_id=? ORDER BY revision_snapshot_row_id",
                (revision_group_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get_latest_revision_snapshot(self, revision_group_id: str) -> dict[str, Any] | None:
        items = self.list_revision_snapshots(revision_group_id)
        return items[-1] if items else None

    @staticmethod
    def _configuration_from_row(row: sqlite3.Row) -> ConfigurationVersion:
        item = dict(row)
        return ConfigurationVersion(
            configuration_id=item["configuration_id"], version=item["version"], status=item["status"],
            created_at=item["created_at"], created_by=item["created_by"], parent_version=item["parent_version"],
            payload=ConfigurationPayload.model_validate_json(item["payload_json"]),
            schema_version=item["schema_version"], change_note=item["change_note"],
            validation_status=item["validation_status"],
            validation_errors=json.loads(item["validation_errors_json"]),
            activated_at=item["activated_at"], deactivated_at=item["deactivated_at"],
            content_hash=item["content_hash"],
        )

    def list_configurations(self) -> list[ConfigurationVersion]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM configuration_versions ORDER BY configuration_row_id"
            ).fetchall()
        return [self._configuration_from_row(row) for row in rows]

    def get_configuration(self, configuration_id_or_version: str) -> ConfigurationVersion | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM configuration_versions WHERE configuration_id=? OR version=?",
                (configuration_id_or_version, configuration_id_or_version),
            ).fetchone()
        return self._configuration_from_row(row) if row else None

    def get_active_configuration(self) -> ConfigurationVersion:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM configuration_versions WHERE status='active'"
            ).fetchone()
        if row is None:
            raise RuntimeError("No active configuration exists.")
        return self._configuration_from_row(row)

    def create_configuration(self, request: ConfigurationCreate, parent_version: str | None) -> ConfigurationVersion:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            number = int(connection.execute(
                "SELECT COALESCE(MAX(configuration_row_id),0)+1 FROM configuration_versions"
            ).fetchone()[0])
            existing = {str(row[0]) for row in connection.execute("SELECT version FROM configuration_versions")}
            active = self.get_active_configuration()
            family = "config-v0.8." if active.version.startswith("config-v0.8.") else "config-v0.7."
            suffix = max(
                [int(value.rsplit(".", 1)[1]) for value in existing if value.startswith(family)],
                default=-1,
            ) + 1
            version = f"{family}{suffix}"
            cursor = connection.execute(
                """INSERT INTO configuration_versions(
                    version,status,created_at,created_by,parent_version,payload_json,schema_version,
                    change_note,validation_status,validation_errors_json,content_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (version, "draft", now, request.created_by, parent_version,
                request.payload.model_dump_json(), "configuration-schema-v0.8.0", request.change_note,
                 "not_validated", "[]", configuration_hash(request.payload)),
            )
            configuration_id = f"CFG{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?",
                (configuration_id, int(cursor.lastrowid)),
            )
            self._insert_configuration_audit(
                connection, configuration_id, "create", request.created_by, request.change_note,
                {"parent_version": parent_version}, now,
            )
        result = self.get_configuration(configuration_id)
        assert result is not None
        return result

    def set_configuration_validation(self, configuration_id: str, *, passed: bool,
                                     errors: list[str], actor: str) -> ConfigurationVersion:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            updated = connection.execute(
                """UPDATE configuration_versions SET status=?, validation_status=?, validation_errors_json=?
                   WHERE configuration_id=? AND status IN ('draft','validated')""",
                ("validated" if passed else "draft", "passed" if passed else "failed",
                 json.dumps(errors), configuration_id),
            ).rowcount
            if not updated:
                raise ValueError("Only draft or validated configurations can be validated.")
            self._insert_configuration_audit(
                connection, configuration_id, "validate", actor,
                "Validation passed." if passed else "Validation failed.", {"errors": errors}, now,
            )
        result = self.get_configuration(configuration_id)
        assert result is not None
        return result

    def activate_configuration(self, configuration_id: str, *, actor: str, reason: str,
                               action: str = "activate") -> ConfigurationVersion:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            target = connection.execute(
                "SELECT * FROM configuration_versions WHERE configuration_id=?", (configuration_id,)
            ).fetchone()
            if target is None:
                raise LookupError("Configuration not found.")
            if target["validation_status"] != "passed":
                raise ValueError("Invalid or unvalidated configuration cannot be activated.")
            connection.execute(
                "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE status='active' AND configuration_id<>?",
                (now, configuration_id),
            )
            connection.execute(
                "UPDATE configuration_versions SET status='active', activated_at=?, deactivated_at=NULL WHERE configuration_id=?",
                (now, configuration_id),
            )
            self._insert_configuration_audit(
                connection, configuration_id, action, actor, reason, {}, now,
            )
        result = self.get_configuration(configuration_id)
        assert result is not None
        return result

    def list_configuration_audit(self, configuration_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as connection:
            if configuration_id:
                rows = connection.execute(
                    "SELECT * FROM configuration_audit WHERE configuration_id=? ORDER BY audit_row_id",
                    (configuration_id,),
                ).fetchall()
            else:
                rows = connection.execute("SELECT * FROM configuration_audit ORDER BY audit_row_id").fetchall()
        return [{**dict(row), "details": json.loads(row["details_json"])} for row in rows]

    @staticmethod
    def _insert_configuration_audit(connection: sqlite3.Connection, configuration_id: str,
                                    action: str, actor: str, reason: str,
                                    details: dict[str, Any], created_at: str) -> None:
        cursor = connection.execute(
            """INSERT INTO configuration_audit(
                configuration_id,action,actor,reason,details_json,created_at
            ) VALUES (?,?,?,?,?,?)""",
            (configuration_id, action, actor, reason, json.dumps(details), created_at),
        )
        connection.execute(
            "UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?",
            (f"CA{int(cursor.lastrowid):06d}", int(cursor.lastrowid)),
        )

    def list_visualization_records(self, student_id: str) -> list[dict[str, Any]]:
        records = self.list_longitudinal_records(student_id)
        for item in records:
            run = self.get_latest_analysis_run(int(item["essay_id"]))
            item["analysis_run_id"] = run.get("analysis_run_id") if run else None
            item["analyzer_id"] = run.get("analyzer_id") if run else "legacy"
            item["analyzer_version"] = run.get("analyzer_version") if run else item.get("analysis_version")
            item["configuration_version"] = run.get("configuration_version") if run else "legacy"
            item["input_quality"] = (run.get("artifact") or {}).get("input_quality", {}) if run else {}
            metric_results = run.get("metric_results", []) if run else []
            item["versioned_metrics"] = {
                metric["metric_id"]: {
                    "value": metric["value"], "metric_version": metric["metric_version"],
                    "status": metric["status"], "limitations": metric["limitations"],
                    "confidence": metric.get("confidence", "insufficient"),
                    "eligible_for_longitudinal_comparison": metric.get(
                        "eligible_for_longitudinal_comparison", False
                    ),
                }
                for metric in metric_results
            }
            legacy_metrics = (run.get("artifact") or {}).get("legacy_metrics", {}) if run else {}
            for metric_id, value in legacy_metrics.items():
                item["versioned_metrics"].setdefault(metric_id, {
                    "value": value, "metric_version": "legacy-v0.1",
                    "status": "available",
                    "limitations": ["Legacy compatibility metric; use only with the displayed version."],
                })
            calibration = self.get_diagnostic_calibration(int(item["essay_id"]))
            item["diagnostic_calibration"] = (
                calibration.model_dump(mode="json") if calibration else None
            )
        return records


SQLiteRepository = Database
