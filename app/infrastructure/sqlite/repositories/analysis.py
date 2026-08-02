from __future__ import annotations

import json
from typing import Any

from app.infrastructure.sqlite import SQLiteConnectionManager
from app.models import AnalysisResult, DiagnosisResult


class SQLiteAnalysisRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    def save_analysis(self, essay_id: int, analysis: AnalysisResult) -> None:
        with self._connection_manager.connect() as connection:
            connection.execute(
                "INSERT INTO metrics(essay_id, metrics_json, analysis_version, limitations) VALUES (?, ?, ?, ?)",
                (essay_id, json.dumps(analysis.metrics), analysis.analysis_version, analysis.limitations),
            )

    def save_analysis_run(self, essay_id: int, analysis: AnalysisResult) -> AnalysisResult:
        with self._connection_manager.connect() as connection:
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
        with self._connection_manager.connect() as connection:
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
        with self._connection_manager.connect() as connection:
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
        with self._connection_manager.connect() as connection:
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
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT artifact_json FROM analysis_artifacts WHERE analysis_run_id=? ORDER BY artifact_id DESC LIMIT 1",
                (analysis_run_id,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_diagnosis(self, essay_id: int, diagnosis: DiagnosisResult) -> None:
        with self._connection_manager.connect() as connection:
            connection.execute(
                "INSERT INTO diagnoses(essay_id, diagnosis_json, diagnosis_version) VALUES (?, ?, ?)",
                (essay_id, diagnosis.model_dump_json(), diagnosis.diagnosis_version),
            )
