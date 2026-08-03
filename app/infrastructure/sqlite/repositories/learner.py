from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

from app.calibration import DiagnosticCalibrationResult
from app.core import LearnerProfileSnapshot
from app.infrastructure.sqlite import SQLiteConnectionManager
from app.infrastructure.sqlite.repositories.contracts import AnalysisRunReader


class _DiagnosticCalibrationReader(Protocol):
    def get_diagnostic_calibration(self, essay_id: int) -> DiagnosticCalibrationResult | None: ...


class SQLiteLearnerRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager,
                 analysis_reader: AnalysisRunReader,
                 calf_reader: _DiagnosticCalibrationReader,
                 revision_stage_normalizer: Callable[[str], str]):
        self._connection_manager = connection_manager
        self._analysis_reader = analysis_reader
        self._calf_reader = calf_reader
        self._normalize_revision_stage = revision_stage_normalizer

    def get_student(self, student_id: str) -> dict[str, Any] | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                """SELECT s.student_id, s.created_at, s.is_synthetic,
                COUNT(e.essay_id) AS submission_count
                FROM students s LEFT JOIN essays e ON e.student_id=s.student_id
                WHERE s.student_id=? GROUP BY s.student_id""",
                (student_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_all_students(self):
        with self._connection_manager.connect() as connection:
            rows = connection.execute("SELECT DISTINCT student_id FROM essays ORDER BY student_id").fetchall()
            return [{"student_id": r[0]} for r in rows]

    def list_student_history(self, student_id: str) -> list[dict[str, Any]]:
        with self._connection_manager.connect() as connection:
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

    def get_latest_learner_profile(self, student_id: str) -> dict[str, Any] | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM learner_profile_snapshots WHERE student_id=? ORDER BY snapshot_row_id DESC LIMIT 1",
                (student_id,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_learner_profile_snapshot(self, snapshot: LearnerProfileSnapshot) -> LearnerProfileSnapshot:
        with self._connection_manager.connect() as connection:
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
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT evidence_json FROM history_evidence_registry WHERE student_id=? ORDER BY history_evidence_row_id",
                (student_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def list_learner_profile_snapshots(self, student_id: str) -> list[dict[str, Any]]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT snapshot_json FROM learner_profile_snapshots WHERE student_id=? ORDER BY snapshot_row_id",
                (student_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def list_longitudinal_records(self, student_id: str) -> list[dict[str, Any]]:
        with self._connection_manager.connect() as connection:
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
                if self._normalize_revision_stage(str(item.get("revision_stage") or "")) == "final_draft"
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

    def list_visualization_records(self, student_id: str) -> list[dict[str, Any]]:
        records = self.list_longitudinal_records(student_id)
        for item in records:
            run = self._analysis_reader.get_latest_analysis_run(int(item["essay_id"]))
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
            calibration = self._calf_reader.get_diagnostic_calibration(int(item["essay_id"]))
            item["diagnostic_calibration"] = (
                calibration.model_dump(mode="json") if calibration else None
            )
        return records
