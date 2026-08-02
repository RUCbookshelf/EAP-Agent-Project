from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.analysis import MetricRegistry
from app.services.comparability import ComparabilityService
from app.services.progress import ProgressService


@runtime_checkable
class DashboardReadPort(Protocol):
    def list_visualization_records(self, student_id: str) -> list[dict[str, Any]]: ...


class DashboardService:
    """Prepare chart-ready evidence; Streamlit only renders this API result."""

    version = "progress-visualization-data-v0.6.0"

    def __init__(
        self,
        repository: DashboardReadPort,
        metrics: MetricRegistry,
        progress_service: ProgressService,
    ) -> None:
        self.repository = repository
        self.metrics = metrics
        self.comparability = ComparabilityService()
        self.progress = progress_service

    def build(self, student_id: str, metric_id: str = "word_count") -> dict[str, Any]:
        definition = self.metrics.get(metric_id)
        records = self.repository.list_visualization_records(student_id)
        if not records:
            raise LookupError("Student has no submissions.")
        representative = [row for row in records if row.get("is_longitudinal_representative", True)]
        current = representative[-1]
        comparisons = {
            int(row["essay_id"]): self.comparability.compare(current, row)
            for row in representative[:-1]
        }
        timeline = []
        points = []
        partial_count = 0
        exclusion_reasons: list[str] = []
        for row in records:
            essay_id = int(row["essay_id"])
            if not row.get("is_longitudinal_representative", True):
                status, included = "revision_non_representative", False
                reasons = [row.get("revision_exclusion_reason")]
            elif essay_id == int(current["essay_id"]):
                status, included, reasons = "current_anchor", True, []
            else:
                comparison = comparisons[essay_id]
                status = comparison.status
                included = status == "comparable"
                reasons = comparison.reasons
                if status == "partially_comparable":
                    partial_count += 1
            exclusion_reasons.extend(reason for reason in reasons if reason)
            timeline.append({
                "submission_id": essay_id, "submitted_at": row["submitted_at"],
                "writing_prompt": row["writing_prompt"], "genre": row["genre"],
                "draft_stage": row["draft_stage"], "timed": bool(row["timed"]),
                "time_limit_minutes": row.get("time_limit_minutes"), "tool_use": row["tool_use"],
                "analysis_run_id": row.get("analysis_run_id"), "analyzer_id": row.get("analyzer_id"),
                "analyzer_version": row.get("analyzer_version"),
                "configuration_version": row.get("configuration_version"),
                "revision_group_id": row.get("revision_group_id"),
                "comparability_status": status, "included_in_longitudinal": included,
                "exclusion_reasons": reasons,
                "is_revision_representative": row.get("is_longitudinal_representative", True),
            })
            metric = row.get("versioned_metrics", {}).get(metric_id)
            value = metric.get("value") if metric else None
            available = isinstance(value, (int, float)) and not isinstance(value, bool)
            points.append({
                "submission_id": essay_id, "submitted_at": row["submitted_at"],
                "value": value if available else None,
                "included": included and available, "exclusion_reasons": reasons if not included else [],
                "metric_id": metric_id, "metric_version": metric.get("metric_version") if metric else None,
                "analyzer_version": row.get("analyzer_version"),
                "configuration_version": row.get("configuration_version"),
                "limitations": metric.get("limitations", []) if metric else ["Metric is unavailable for this AnalysisRun."],
            })
        segments: dict[tuple[str, str, str], list[dict]] = {}
        for point in points:
            if not point["included"]:
                continue
            key = (
                str(point["analyzer_version"]), str(point["metric_version"]),
                str(point["configuration_version"]),
            )
            segments.setdefault(key, []).append(point)
        snapshot = self.progress.create_snapshot(student_id, persist=False)
        trend = snapshot.metric_trends.get(metric_id)
        trend_summary = (
            {
                "direction": trend.direction, "variability": trend.variability,
                "confidence": trend.confidence, "data_points": trend.data_points,
                "analysis_version": trend.analysis_version, "limitations": trend.limitations,
            }
            if trend else {
                "direction": "insufficient_data", "variability": "insufficient_data",
                "confidence": "insufficient", "data_points": sum(point["included"] for point in points),
                "analysis_version": self.version,
                "limitations": ["This registered v0.4 metric has no calibrated v0.3 trend rule; points are shown without a direction."],
            }
        )
        issues = []
        for status, items in (
            ("persistent", snapshot.persistent_issues),
            ("recently_reduced", snapshot.recently_reduced_issues),
            ("recurring", snapshot.unstable_issues),
        ):
            for item in items:
                issues.append({**item.model_dump(mode="json"), "display_status": status})
        represented_categories = {item["diagnosis_category"] for item in issues}
        current_categories = {
            item.get("category")
            for item in current.get("diagnosis", {}).get("improvement_priorities", [])
            if item.get("category")
        }
        previous_categories = {
            item.get("category")
            for row in representative[:-1]
            for item in row.get("diagnosis", {}).get("improvement_priorities", [])
            if item.get("category")
        }
        for category in sorted(current_categories - represented_categories):
            issues.append({
                "diagnosis_category": category,
                "display_status": "newly_observed" if representative[:-1] and category not in previous_categories else "insufficient_evidence",
                "supporting_submission_ids": [f"E{int(current['essay_id']):06d}"],
                "confidence": "low" if representative[:-1] else "insufficient",
                "diagnosis_versions": [str(current.get("diagnosis_version", "unknown"))],
                "limitations": ["A current heuristic signal is not proof of a new learner problem or ability state."],
            })
        return {
            "student_id": student_id, "timeline": timeline,
            "metric": definition.model_dump(mode="json"), "metric_points": points,
            "metric_segments": [
                {
                    "segment_id": f"SEG{index:03d}", "analyzer_version": key[0],
                    "metric_version": key[1], "configuration_version": key[2], "points": values,
                    "limitations": ["Only version-compatible points are connected in this segment."],
                }
                for index, (key, values) in enumerate(sorted(segments.items()), 1)
            ],
            "issue_trajectories": issues,
            "trend_summary": trend_summary,
            "comparability_summary": {
                "historical_submission_count": max(len(records) - 1, 0),
                "included_count": sum(1 for item in timeline if item["included_in_longitudinal"]),
                "excluded_count": sum(1 for item in timeline if not item["included_in_longitudinal"]),
                "partially_comparable_count": partial_count,
                "exclusion_reasons": sorted(set(exclusion_reasons)),
                "revision_representative_policy": snapshot.revision_representative_policy,
            },
            "analysis_version": self.version,
            "limitations": [
                "Metric trends are descriptive prototype observations, not ability development.",
                "Version-incompatible points are separated rather than silently connected.",
                *definition.limitations,
            ],
        }
