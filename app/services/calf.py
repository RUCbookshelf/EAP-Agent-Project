from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.calf import accuracy_availability, default_calf_registry


class CalfService:
    """Read-only research views over append-only Analyzer and annotation evidence."""

    def __init__(self, repository) -> None:
        self.repository = repository
        self.registry = default_calf_registry()

    def submission_report(self, submission_id: int) -> dict[str, Any]:
        submission = self.repository.get_submission_bundle(submission_id)
        if submission is None:
            raise LookupError("Submission not found.")
        run = self.repository.get_latest_analysis_run(submission_id)
        metrics = run.get("metric_results", []) if run else []
        by_id = {item["metric_id"]: item for item in metrics}
        result_items: list[dict[str, Any]] = []
        for specification in self.registry.list_specifications():
            stored = by_id.get(specification.metric_id)
            if stored is not None:
                result_items.append({
                    **stored, "measurement_specification": specification.model_dump(mode="json"),
                })
            elif specification.metric_id == "lexical_sophistication":
                result_items.append(self._unavailable(specification, "No authorized versioned frequency resource is configured."))
        annotations = self.repository.list_error_annotations(submission_id)
        accuracy = accuracy_availability(annotations)
        for specification in self.registry.list_specifications(construct_id="accuracy"):
            result_items.append({
                **self._unavailable(specification, accuracy["reason"]),
                "eligible_annotation_count": accuracy["eligible_annotation_count"],
            })
        units = self.repository.list_analysis_units(submission_id, run.get("analysis_run_id") if run else None)
        grouped: dict[str, list[dict]] = defaultdict(list)
        for item in result_items:
            grouped[item["construct_id"]].append(item)
        return {
            "submission_id": submission_id,
            "analysis_run_id": run.get("analysis_run_id") if run else None,
            "configuration_version": run.get("configuration_version") if run else None,
            "construct_groups": dict(grouped), "metric_results": result_items,
            "analysis_units": units,
            "timing": {
                "timed": submission["timed"], "time_limit_minutes": submission.get("time_limit_minutes"),
                "writing_started_at": submission.get("writing_started_at"),
                "writing_submitted_at": submission.get("writing_submitted_at"),
                "active_writing_duration_seconds": submission.get("active_writing_duration_seconds"),
                "timing_source": submission.get("timing_source", "unknown"),
                "timing_quality": submission.get("timing_quality", "unavailable"),
                "time_limit_is_actual_duration": False,
            },
            "accuracy_annotation_availability": accuracy,
            "interpretation_boundary": "Research measures are not writing scores or ability judgments.",
        }

    @staticmethod
    def _unavailable(specification, reason: str) -> dict[str, Any]:
        return {
            "metric_id": specification.metric_id, "metric_version": specification.metric_version,
            "construct_id": specification.construct_id, "subconstruct_id": specification.subconstruct_id,
            "value": None, "status": "insufficient_data", "measurement_status": "unavailable",
            "automation_level": specification.automation_level.value,
            "analysis_unit_version": specification.analysis_unit_version,
            "confidence": "insufficient", "confidence_reasons": [], "risk_factors": [reason],
            "eligible_for_diagnosis": False, "eligible_for_longitudinal_comparison": False,
            "eligible_for_revision_priority": False, "eligible_for_targeted_practice": False,
            "parameters": specification.parameters, "measurement_metadata": {"reason": reason},
            "intermediate_values": {}, "limitations": [reason],
            "measurement_specification": specification.model_dump(mode="json"),
        }

    def trajectories(self, student_id: str) -> dict[str, Any]:
        if self.repository.get_student(student_id) is None:
            raise LookupError("Student not found.")
        series: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
        excluded: list[dict] = []
        for submission in self.repository.list_student_submissions(student_id):
            run = self.repository.get_latest_analysis_run(int(submission["essay_id"]))
            if not run:
                continue
            for item in run.get("metric_results", []):
                try:
                    specification = self.registry.get_specification(item["metric_id"])
                except ValueError:
                    continue
                reason = None
                if not specification.eligible_for_longitudinal_tracking:
                    reason = "Measurement specification excludes longitudinal tracking."
                elif not item.get("eligible_for_longitudinal_comparison"):
                    reason = "Metric confidence or data requirements exclude this observation."
                elif item.get("status") != "available":
                    reason = "The measure is unavailable for this submission."
                if reason:
                    excluded.append({"submission_id": submission["essay_id"], "metric_id": item["metric_id"], "reason": reason})
                    continue
                task_cluster = "|".join([
                    str(submission.get("genre") or "unknown"),
                    "timed" if submission.get("timed") else "untimed",
                    str(submission.get("time_limit_minutes") or "na"),
                    str(submission.get("tool_use") or "unknown"),
                ])
                key = (item["metric_id"], item["metric_version"], item.get("analysis_unit_version") or "legacy", task_cluster)
                series[key].append({
                    "submission_id": submission["essay_id"], "submitted_at": submission["submitted_at"],
                    "value": item["value"], "confidence": item.get("confidence"),
                    "task_conditions": {"genre": submission["genre"], "timed": submission["timed"],
                                        "time_limit_minutes": submission.get("time_limit_minutes"),
                                        "tool_use": submission["tool_use"]},
                })
        return {
            "student_id": student_id,
            "series": [
                {"metric_id": key[0], "metric_version": key[1], "analysis_unit_version": key[2],
                 "task_cluster_signature": key[3],
                 "version_compatibility_rule": "exact", "observations": values,
                 "interpretation_boundary": "Observed comparable values only; no ability or improvement claim."}
                for key, values in sorted(series.items())
            ],
            "excluded_observations": excluded,
        }

    def import_error_annotations(self, submission_id: int, annotations: list) -> list:
        submission = self.repository.get_submission_bundle(submission_id)
        if submission is None:
            raise LookupError("Submission not found.")
        text = submission["essay_text"]
        for annotation in annotations:
            if annotation.end_offset > len(text):
                raise ValueError("Error annotation offsets exceed the stored essay text.")
            if text[annotation.start_offset:annotation.end_offset] != annotation.original_text:
                raise ValueError("Error annotation original_text must exactly match the stored essay span.")
        return self.repository.save_error_annotations(submission_id, annotations)
