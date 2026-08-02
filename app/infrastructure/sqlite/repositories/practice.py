from __future__ import annotations

import json

from app.infrastructure.sqlite.connection import SQLiteConnectionManager


class SQLitePracticeRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    def _next_practice_id(self, table_prefix: str) -> str:
            with self._connection_manager.connect() as connection:
                table = {
                    "practice_target": "practice_targets",
                    "exercise_instance": "exercise_instances",
                    "exercise_attempt": "exercise_attempts",
                    "practice_evaluation": "practice_evaluations",
                    "engagement_trace": "feedback_engagement_traces",
                    "within_task_response": "within_task_response_candidates",
                    "transfer_evidence": "transfer_evidence_candidates",
                    "practice_state_snapshot": "practice_state_snapshots",
                }[table_prefix]
                id_col = {
                    "practice_target": "practice_target_id",
                    "exercise_instance": "exercise_id",
                    "exercise_attempt": "attempt_id",
                    "practice_evaluation": "evaluation_id",
                    "engagement_trace": "trace_id",
                    "within_task_response": "response_id",
                    "transfer_evidence": "transfer_evidence_id",
                    "practice_state_snapshot": "practice_state_snapshot_id",
                }[table_prefix]
                q = f"SELECT COALESCE(MAX(CAST(SUBSTR({id_col}, 3) AS INTEGER)), 0) + 1 FROM {table}"
                cursor = connection.execute(q)
                return int(cursor.fetchone()[0])

    def save_practice_target(self, target: dict) -> dict:
            from app.practice.schemas import PracticeTarget
            obj = PracticeTarget(**target) if not isinstance(target, PracticeTarget) else target
            n = self._next_practice_id("practice_target")
            obj.practice_target_id = f"PT{n:06d}"
            sv = obj.status.value if hasattr(obj.status, "value") else str(obj.status)
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT INTO practice_targets VALUES (?,?,?,?,?,?,?,?,?)",
                    (obj.practice_target_id, obj.student_id, obj.source_submission_id,
                     obj.source_diagnosis_id, obj.target_code, obj.target_label,
                     sv, obj.created_at, json.dumps(obj.model_dump(mode="json"))))
            return obj.model_dump(mode="json")

    def list_practice_targets(self, student_id: str) -> list[dict]:
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    "SELECT target_json FROM practice_targets WHERE student_id=? ORDER BY created_at", (student_id,)
                ).fetchall()
            return [json.loads(r[0]) for r in rows]

    def get_practice_target(self, pid: str) -> dict | None:
            with self._connection_manager.connect() as c:
                row = c.execute("SELECT target_json FROM practice_targets WHERE practice_target_id=?", (pid,)).fetchone()
            return json.loads(row[0]) if row else None

    def save_exercise_instance(self, instance: dict) -> dict:
            from app.practice.schemas import ExerciseInstance
            obj = ExerciseInstance(**instance) if not isinstance(instance, ExerciseInstance) else instance
            n = self._next_practice_id("exercise_instance")
            obj.exercise_id = f"EX{n:06d}"
            et = obj.exercise_type.value if hasattr(obj.exercise_type, "value") else str(obj.exercise_type)
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT INTO exercise_instances VALUES (?,?,?,?,?,?)",
                    (obj.exercise_id, obj.practice_target_id, obj.student_id,
                     et, obj.created_at, json.dumps(obj.model_dump(mode="json"))))
            return obj.model_dump(mode="json")

    def list_exercise_instances(self, practice_target_id=None, student_id=None) -> list[dict]:
            with self._connection_manager.connect() as c:
                if practice_target_id:
                    rows = c.execute(
                        "SELECT instance_json FROM exercise_instances WHERE practice_target_id=? ORDER BY created_at",
                        (practice_target_id,)).fetchall()
                elif student_id:
                    rows = c.execute(
                        "SELECT instance_json FROM exercise_instances WHERE student_id=? ORDER BY created_at",
                        (student_id,)).fetchall()
                else: return []
            return [json.loads(r[0]) for r in rows]

    def get_exercise_instance(self, eid: str) -> dict | None:
            with self._connection_manager.connect() as c:
                row = c.execute("SELECT instance_json FROM exercise_instances WHERE exercise_id=?", (eid,)).fetchone()
            return json.loads(row[0]) if row else None

    def save_exercise_attempt(self, attempt: dict) -> dict:
            from app.practice.schemas import ExerciseAttempt
            obj = ExerciseAttempt(**attempt) if not isinstance(attempt, ExerciseAttempt) else attempt
            n = self._next_practice_id("exercise_attempt")
            obj.attempt_id = f"EA{n:06d}"
            sv = obj.status.value if hasattr(obj.status, "value") else str(obj.status)
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT INTO exercise_attempts VALUES (?,?,?,?,?,?,?)",
                    (obj.attempt_id, obj.exercise_id, obj.student_id, obj.attempt_number,
                     sv, obj.created_at, json.dumps(obj.model_dump(mode="json"))))
            return obj.model_dump(mode="json")

    def list_exercise_attempts(self, exercise_id: str) -> list[dict]:
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    "SELECT attempt_json FROM exercise_attempts WHERE exercise_id=? ORDER BY attempt_number", (exercise_id,)
                ).fetchall()
            return [json.loads(r[0]) for r in rows]

    def save_practice_evaluation(self, evaluation: dict) -> dict:
            from app.practice.schemas import PracticeEvaluation
            obj = PracticeEvaluation(**evaluation) if not isinstance(evaluation, PracticeEvaluation) else evaluation
            n = self._next_practice_id("practice_evaluation")
            obj.evaluation_id = f"PE{n:06d}"
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT INTO practice_evaluations VALUES (?,?,?,?,?)",
                    (obj.evaluation_id, obj.attempt_id, obj.practice_target_id,
                     obj.created_at, json.dumps(obj.model_dump(mode="json"))))
            return obj.model_dump(mode="json")

    def list_practice_evaluations(self, attempt_id=None, practice_target_id=None) -> list[dict]:
            with self._connection_manager.connect() as c:
                if attempt_id:
                    rows = c.execute(
                        "SELECT evaluation_json FROM practice_evaluations WHERE attempt_id=? ORDER BY created_at", (attempt_id,)
                    ).fetchall()
                elif practice_target_id:
                    rows = c.execute(
                        "SELECT evaluation_json FROM practice_evaluations WHERE practice_target_id=? ORDER BY created_at", (practice_target_id,)
                    ).fetchall()
                else: return []
            return [json.loads(r[0]) for r in rows]

    def list_practice_evaluations_by_student(self, student_id: str) -> list[dict]:
            """All practice evaluations for a learner (joined through attempts)."""
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    """SELECT pe.evaluation_json FROM practice_evaluations pe
                    JOIN exercise_attempts ea ON ea.attempt_id = pe.attempt_id
                    WHERE ea.student_id=? ORDER BY pe.created_at""",
                    (student_id,),
                ).fetchall()
            return [json.loads(r[0]) for r in rows]

    def list_essays_by_student(self, student_id: str) -> list[dict]:
            """All essays for a learner, oldest first."""
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    "SELECT * FROM essays WHERE student_id=? ORDER BY submitted_at, essay_id", (student_id,)
                ).fetchall()
            return [dict(r) for r in rows]

    def list_analysis_runs_for_student(self, student_id: str) -> list[dict]:
            """All analysis runs for a learner (joined through essays)."""
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    """SELECT ar.* FROM analysis_runs ar
                    JOIN essays e ON e.essay_id = ar.essay_id
                    WHERE e.student_id=? ORDER BY ar.created_at, ar.analysis_run_row_id""",
                    (student_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    def list_feedback_records_for_student(self, student_id: str) -> list[dict]:
            """All feedback records for a learner (joined through essays)."""
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    """SELECT fr.* FROM feedback_records fr
                    JOIN essays e ON e.essay_id = fr.essay_id
                    WHERE e.student_id=? ORDER BY fr.created_at, fr.feedback_id""",
                    (student_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    def list_exercise_attempts_by_student(self, student_id: str) -> list[dict]:
            """All exercise attempts for a learner."""
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    "SELECT * FROM exercise_attempts WHERE student_id=? ORDER BY created_at, attempt_number", (student_id,)
                ).fetchall()
            return [dict(r) for r in rows]

    def save_feedback_engagement_trace(self, trace: dict) -> dict:
            from app.practice.schemas import FeedbackEngagementTrace
            obj = FeedbackEngagementTrace(**trace) if not isinstance(trace, FeedbackEngagementTrace) else trace
            n = self._next_practice_id("engagement_trace")
            obj.trace_id = f"FET{n:06d}"
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT INTO feedback_engagement_traces VALUES (?,?,?,?,?)",
                    (obj.trace_id, obj.student_id, obj.target_code,
                     obj.created_at, json.dumps(obj.model_dump(mode="json"))))
            return obj.model_dump(mode="json")

    def list_feedback_engagement_traces(self, student_id: str) -> list[dict]:
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    "SELECT trace_json FROM feedback_engagement_traces WHERE student_id=? ORDER BY created_at", (student_id,)
                ).fetchall()
            return [json.loads(r[0]) for r in rows]

    def save_within_task_response_candidate(self, candidate: dict) -> dict:
            from app.practice.schemas import WithinTaskResponseCandidate
            obj = WithinTaskResponseCandidate(**candidate) if not isinstance(candidate, WithinTaskResponseCandidate) else candidate
            n = self._next_practice_id("within_task_response")
            obj.response_id = f"WTR{n:06d}"
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT INTO within_task_response_candidates VALUES (?,?,?,?,?)",
                    (obj.response_id, obj.student_id, obj.practice_target_id,
                     obj.created_at, json.dumps(obj.model_dump(mode="json"))))
            return obj.model_dump(mode="json")

    def list_within_task_responses(self, student_id: str) -> list[dict]:
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    "SELECT response_json FROM within_task_response_candidates WHERE student_id=? ORDER BY created_at", (student_id,)
                ).fetchall()
            return [json.loads(r[0]) for r in rows]

    def save_transfer_evidence_candidate(self, candidate: dict) -> dict:
            from app.practice.schemas import TransferEvidenceCandidate
            obj = TransferEvidenceCandidate(**candidate) if not isinstance(candidate, TransferEvidenceCandidate) else candidate
            n = self._next_practice_id("transfer_evidence")
            obj.transfer_evidence_id = f"TE{n:06d}"
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT INTO transfer_evidence_candidates VALUES (?,?,?,?,?)",
                    (obj.transfer_evidence_id, obj.student_id, obj.practice_target_id,
                     obj.created_at, json.dumps(obj.model_dump(mode="json"))))
            return obj.model_dump(mode="json")

    def list_transfer_evidence_candidates(self, student_id: str) -> list[dict]:
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    "SELECT transfer_json FROM transfer_evidence_candidates WHERE student_id=? ORDER BY created_at", (student_id,)
                ).fetchall()
            return [json.loads(r[0]) for r in rows]

    def save_practice_state_snapshot(self, snapshot: dict) -> dict:
            from app.practice.schemas import PracticeStateSnapshot
            obj = PracticeStateSnapshot(**snapshot) if not isinstance(snapshot, PracticeStateSnapshot) else snapshot
            n = self._next_practice_id("practice_state_snapshot")
            obj.practice_state_snapshot_id = f"PSS{n:06d}"
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT INTO practice_state_snapshots VALUES (?,?,?,?)",
                    (obj.practice_state_snapshot_id, obj.student_id, obj.created_at,
                     json.dumps(obj.model_dump(mode="json"))))
            return obj.model_dump(mode="json")

    def list_practice_state_snapshots(self, student_id: str) -> list[dict]:
            with self._connection_manager.connect() as c:
                rows = c.execute(
                    "SELECT snapshot_json FROM practice_state_snapshots WHERE student_id=? ORDER BY created_at", (student_id,)
                ).fetchall()
            return [json.loads(r[0]) for r in rows]
