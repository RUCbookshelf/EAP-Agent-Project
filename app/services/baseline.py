from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from statistics import mean, median
from typing import Any

from app.config.longitudinal import METRIC_NAMES, RULES, LongitudinalRules
from app.core import BaselineProfile, ComparabilityResult


class BaselineService:
    def __init__(self, rules: LongitudinalRules = RULES) -> None:
        self.rules = rules

    def build(
        self,
        student_id: str,
        records: list[dict[str, Any]],
        comparisons: dict[str, ComparabilityResult],
        current_submission_id: str,
    ) -> BaselineProfile:
        included: list[dict[str, Any]] = []
        excluded: list[str] = []
        for record in records:
            submission_id = self._id(record)
            if submission_id == current_submission_id or comparisons[submission_id].status == "comparable":
                included.append(record)
            else:
                excluded.append(submission_id)
        available = len(included) >= self.rules.minimum_baseline_submissions
        summaries: dict[str, dict[str, float]] = {}
        frequencies: Counter[str] = Counter()
        if available:
            for metric in METRIC_NAMES:
                values = [self._metric(record, metric) for record in included if metric in record.get("metrics", {})]
                if values:
                    summaries[metric] = {
                        "mean": round(mean(values), 4), "median": round(median(values), 4),
                        "minimum": round(min(values), 4), "maximum": round(max(values), 4),
                    }
            for record in included:
                frequencies.update(self._categories(record))
        limitations = [
            "This baseline is a prototype descriptive reference, not true language ability.",
            f"The minimum of {self.rules.minimum_baseline_submissions} comparable submissions is a configurable working assumption.",
            "Text-length-sensitive metrics require cautious interpretation.",
        ]
        if not available:
            limitations.insert(0, "Insufficient comparable history; no stable personal baseline is claimed.")
        return BaselineProfile(
            student_id=student_id,
            baseline_status="available" if available else "insufficient_history",
            included_submission_ids=[self._id(item) for item in included],
            excluded_submission_ids=excluded,
            baseline_window={
                "minimum_submissions": self.rules.minimum_baseline_submissions,
                "observed_submissions": len(included),
                "start": included[0]["submitted_at"] if included else None,
                "end": included[-1]["submitted_at"] if included else None,
            },
            metric_summaries=summaries,
            diagnosis_frequencies=dict(sorted(frequencies.items())),
            created_at=datetime.now(timezone.utc),
            analysis_version=self.rules.analysis_version,
            limitations=limitations,
        )

    @staticmethod
    def _id(record: dict[str, Any]) -> str:
        return f"E{int(record['essay_id']):06d}"

    @staticmethod
    def _metric(record: dict[str, Any], metric: str) -> float:
        value = record["metrics"][metric]
        return float(sum(value.values())) if isinstance(value, dict) else float(value)

    @staticmethod
    def _categories(record: dict[str, Any]) -> list[str]:
        return [item.get("category") for item in record.get("diagnosis", {}).get("improvement_priorities", []) if item.get("category")]
