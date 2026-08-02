from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.infrastructure.sqlite.connection import SQLiteConnectionManager
from app.models import EssaySubmission, HistoryResult, ProviderResult


class SQLiteSubmissionRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager,
                 revision_stage_normalizer: Callable[[str], str]):
        self._connection_manager = connection_manager
        self._normalize_revision_stage = revision_stage_normalizer

    def save_essay(self, submission: EssaySubmission, *, synthetic: bool = False) -> int:
            with self._connection_manager.connect() as connection:
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
                        submission.draft_stage, self._normalize_revision_stage(submission.draft_stage),
                        submission.writing_started_at.isoformat() if submission.writing_started_at else None,
                        submission.writing_submitted_at.isoformat() if submission.writing_submitted_at else None,
                        submission.active_writing_duration_seconds, submission.timing_source,
                        submission.timing_quality, int(submission.unexplained_interruption),
                    ),
                )
                return int(cursor.lastrowid)

    def save_feedback(self, essay_id: int, result: ProviderResult, analysis_version: str) -> None:
            with self._connection_manager.connect() as connection:
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
            with self._connection_manager.connect() as connection:
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
            with self._connection_manager.connect() as connection:
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

    def get_feedback_record(self, essay_id: int) -> dict[str, Any] | None:
            with self._connection_manager.connect() as connection:
                row = connection.execute("SELECT * FROM feedback_records WHERE essay_id = ?", (essay_id,)).fetchone()
            return dict(row) if row else None

    def get_llm_calls(self, essay_id: int) -> list[dict[str, Any]]:
            with self._connection_manager.connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM llm_call_records WHERE essay_id = ? ORDER BY call_id", (essay_id,)
                ).fetchall()
            return [dict(row) for row in rows]

    def get_history_record(self, essay_id: int) -> dict[str, Any] | None:
            with self._connection_manager.connect() as connection:
                row = connection.execute(
                    "SELECT * FROM learner_history WHERE essay_id = ?", (essay_id,)
                ).fetchone()
            return dict(row) if row else None

    def list_all_submissions(self):
            with self._connection_manager.connect() as connection:
                rows = connection.execute("SELECT essay_id, student_id, writing_prompt, genre, draft_stage, timed, time_limit_minutes, tool_use, submitted_at, revision_of_submission_id, revision_group_id, essay_text FROM essays ORDER BY essay_id").fetchall()
                return [dict(r) for r in rows]

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None:
            with self._connection_manager.connect() as connection:
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
            with self._connection_manager.connect() as connection:
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

    def get_exercises(self, essay_id: int) -> list[dict[str, Any]]:
            with self._connection_manager.connect() as connection:
                rows = connection.execute(
                    "SELECT exercise_json FROM exercises WHERE essay_id=? ORDER BY exercise_id", (essay_id,)
                ).fetchall()
            return [json.loads(row[0]) for row in rows]
