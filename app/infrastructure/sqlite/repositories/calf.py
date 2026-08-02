from __future__ import annotations

import json
from typing import Any

from app.calibration import DiagnosticCalibrationResult
from app.calf import ErrorAnnotation
from app.infrastructure.sqlite import SQLiteConnectionManager


class SQLiteCalfRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    def save_diagnostic_calibration(self, essay_id: int,
                                    calibration: DiagnosticCalibrationResult) -> DiagnosticCalibrationResult:
        persisted = calibration.model_copy(update={"essay_id": essay_id})
        with self._connection_manager.connect() as connection:
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
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT calibration_json FROM diagnostic_calibrations WHERE essay_id=? ORDER BY calibration_row_id DESC LIMIT 1",
                (essay_id,),
            ).fetchone()
        return DiagnosticCalibrationResult.model_validate_json(row[0]) if row else None

    def list_analysis_units(self, submission_id: int, analysis_run_id: str | None = None) -> list[dict[str, Any]]:
        with self._connection_manager.connect() as connection:
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
        with self._connection_manager.connect() as connection:
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
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT annotation_json FROM error_annotations WHERE submission_id=? ORDER BY error_annotation_row_id",
                (submission_id,),
            ).fetchall()
        return [ErrorAnnotation.model_validate_json(row[0]) for row in rows]
