from __future__ import annotations

from datetime import date, datetime, timezone
from statistics import mean, pstdev
from typing import Any

from app.config.longitudinal import (
    DESCRIPTIVE_METRICS, LENGTH_SENSITIVE_METRICS, METRIC_NAMES, RULES, LongitudinalRules,
)
from app.core import (
    ComparabilityResult, ExcludedSubmission, IssueTrajectory, LearnerProfileSnapshot,
    MetricObservation, MetricTrend, PriorityCandidate,
)
from app.repositories import LearnerProfileRepository
from app.models import HistoryEvidence, HistoryResult

from .baseline import BaselineService
from .comparability import ComparabilityService


class LongitudinalRepository(LearnerProfileRepository):
    def list_longitudinal_records(self, student_id: str) -> list[dict[str, Any]]: ...
    def save_learner_profile_snapshot(self, snapshot: LearnerProfileSnapshot) -> LearnerProfileSnapshot: ...
    def list_learner_profile_snapshots(self, student_id: str) -> list[dict[str, Any]]: ...


class ProgressService:
    def __init__(self, repository: LongitudinalRepository, rules: LongitudinalRules = RULES) -> None:
        self.repository = repository
        self.rules = rules
        self.comparability = ComparabilityService(rules)
        self.baselines = BaselineService(rules)

    def create_snapshot(
        self,
        student_id: str,
        *,
        metric: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        comparable_only: bool = True,
        analysis_version: str | None = None,
        persist: bool = True,
    ) -> LearnerProfileSnapshot:
        records = self.repository.list_longitudinal_records(student_id)
        records = [record for record in records if self._within(record, start_date, end_date)]
        if analysis_version:
            records = [record for record in records if record.get("analysis_version") == analysis_version]
        if not records:
            raise ValueError("No submissions are available for the requested longitudinal window.")
        current = records[-1]
        current_id = self._id(current)
        comparisons = {
            self._id(record): self.comparability.compare(current, record)
            for record in records[:-1]
        }
        baseline = self.baselines.build(student_id, records, comparisons, current_id)
        metric_names = [metric] if metric else list(METRIC_NAMES)
        if metric and metric not in METRIC_NAMES:
            raise ValueError(f"Unsupported metric: {metric}")
        trends = {
            name: self._trend(name, records, comparisons, current_id, comparable_only)
            for name in metric_names
        }
        trajectories = self._issue_trajectories(records, comparisons, current_id)
        persistent = [item for item in trajectories if item.status == "persistent"]
        reduced = [item for item in trajectories if item.status == "recently_reduced"]
        unstable = [item for item in trajectories if item.status in {"recurring", "inconsistent"}]
        priorities = self._priorities(current, persistent, reduced, unstable)
        included_ids = baseline.included_submission_ids
        excluded = [
            ExcludedSubmission(submission_id=key, status=value.status, reasons=value.reasons)
            for key, value in comparisons.items() if key not in included_ids
        ]
        confidences = [item.confidence for item in trends.values() if item.confidence != "insufficient"]
        summary = (
            "Prototype longitudinal evidence is available at medium confidence for some metrics."
            if "medium" in confidences else
            "Prototype longitudinal evidence is limited to low confidence."
            if confidences else
            "Insufficient comparable history; no metric trend is reported."
        )
        snapshot = LearnerProfileSnapshot(
            student_id=student_id, snapshot_time=datetime.now(timezone.utc),
            included_submission_ids=included_ids, excluded_submissions=excluded,
            baseline_status=baseline.baseline_status, baseline_profile=baseline,
            metric_trends=trends, persistent_issues=persistent,
            recently_reduced_issues=reduced, unstable_issues=unstable,
            current_priority_candidates=priorities, confidence_summary=summary,
            limitations=[
                "All directions are prototype metric trends, not language-ability growth or decline.",
                "Confidence is a heuristic evidence-strength label, not statistical significance, reliability, or validity.",
                "Only comparable submissions enter the primary baseline and trend calculations.",
            ],
            analysis_version=self.rules.analysis_version,
            configuration_version=self.rules.configuration_version,
        )
        return self.repository.save_learner_profile_snapshot(snapshot) if persist else snapshot

    def enrich_history(self, history: HistoryResult, snapshot: LearnerProfileSnapshot) -> HistoryResult:
        evidence = list(history.history_evidence)
        next_number = len(evidence) + 1
        candidates: list[HistoryEvidence] = []
        for trend in snapshot.metric_trends.values():
            if trend.direction in {"increasing", "decreasing", "stable", "fluctuating"} and trend.confidence != "insufficient":
                candidates.append(HistoryEvidence(
                    history_evidence_id=f"H{next_number + len(candidates):03d}",
                    evidence_type="metric_trend",
                    description=f"Local {trend.analysis_version} classified {trend.metric_name} as {trend.direction} across {trend.data_points} comparable submissions; this is not an ability judgment.",
                    supporting_submission_ids=trend.included_submission_ids,
                    comparable_submission_count=trend.data_points,
                    confidence="medium" if trend.confidence == "medium" else "low",
                    limitation="The local prototype engine calculated this trend; the LLM must not recalculate or strengthen it.",
                ))
                if len(candidates) >= 2: break
        issue_pool = [*snapshot.persistent_issues, *snapshot.recently_reduced_issues]
        if issue_pool:
            item = issue_pool[0]
            candidates.append(HistoryEvidence(
                history_evidence_id=f"H{next_number + len(candidates):03d}",
                evidence_type="issue_trajectory",
                description=f"Local structured-diagnosis tracking classified '{item.diagnosis_category}' as {item.status} across comparable submissions.",
                supporting_submission_ids=item.supporting_submission_ids,
                comparable_submission_count=item.comparable_submission_count,
                confidence="medium" if item.confidence == "medium" else "low",
                limitation="This is a versioned heuristic diagnosis trajectory, not mastery or validated improvement.",
            ))
        if not candidates:
            return history
        return history.model_copy(update={
            "history_evidence": [*evidence, *candidates],
            "summary": history.summary + " Local longitudinal-engine evidence is attached by ID.",
            "limitations": [*history.limitations, *snapshot.limitations],
        })

    def _trend(self, name: str, records: list[dict[str, Any]], comparisons: dict[str, ComparabilityResult], current_id: str, comparable_only: bool) -> MetricTrend:
        observations: list[MetricObservation] = []
        values: list[float] = []
        included_ids: list[str] = []
        excluded_ids: list[str] = []
        versions: set[str] = set()
        for record in records:
            submission_id = self._id(record)
            comparison = None if submission_id == current_id else comparisons[submission_id]
            status = "comparable" if comparison is None else comparison.status
            has_metric = name in record.get("metrics", {})
            include = has_metric and (status == "comparable" or (not comparable_only and status == "partially_comparable"))
            value = self._metric(record, name) if has_metric else 0.0
            reason = None if include else ("Metric missing." if not has_metric else "; ".join(comparison.reasons))
            observations.append(MetricObservation(
                submission_id=submission_id, submitted_at=self._datetime(record), metric_value=value,
                comparability_status=status, included_in_trend=include, exclusion_reason=reason,
            ))
            if include:
                values.append(value); included_ids.append(submission_id); versions.add(str(record.get("analysis_version")))
            else:
                excluded_ids.append(submission_id)
        limitations = self._metric_limitations(name)
        if len(versions) > 1:
            limitations.append("Included analysis versions differ; confidence is reduced.")
        if len(values) < self.rules.minimum_trend_points:
            return MetricTrend(
                metric_name=name, observations=observations, included_submission_ids=included_ids,
                excluded_submission_ids=excluded_ids, direction="insufficient_data", slope=None,
                variability="insufficient_data", data_points=len(values), confidence="insufficient",
                interpretation="Insufficient comparable observations; no direction is reported.",
                limitations=limitations, analysis_version=self.rules.analysis_version,
            )
        slope = self._slope(values)
        coefficient = pstdev(values) / max(abs(mean(values)), 1e-9)
        variability = "low" if coefficient <= self.rules.low_variability_cv else "high" if coefficient > self.rules.high_variability_cv else "moderate"
        relative_change = (values[-1] - values[0]) / max(abs(values[0]), 1.0)
        if variability == "high": direction = "fluctuating"
        elif relative_change >= self.rules.direction_relative_change: direction = "increasing"
        elif relative_change <= -self.rules.direction_relative_change: direction = "decreasing"
        else: direction = "stable"
        confidence = "medium" if len(values) >= 4 and variability == "low" and len(versions) == 1 else "low"
        interpretation = f"Observed {name} values are classified as {direction}; this is a descriptive metric pattern, not a judgment of writing quality or ability change."
        return MetricTrend(
            metric_name=name, observations=observations, included_submission_ids=included_ids,
            excluded_submission_ids=excluded_ids, direction=direction, slope=round(slope, 6),
            variability=variability, data_points=len(values), confidence=confidence,
            interpretation=interpretation, limitations=limitations,
            analysis_version=self.rules.analysis_version,
        )

    def _issue_trajectories(self, records: list[dict[str, Any]], comparisons: dict[str, ComparabilityResult], current_id: str) -> list[IssueTrajectory]:
        included = [record for record in records if self._id(record) == current_id or comparisons[self._id(record)].status == "comparable"]
        categories = sorted({category for record in included for category in self._categories(record)})
        results: list[IssueTrajectory] = []
        for category in categories:
            pattern = [category in self._categories(record) for record in included]
            occurrence_ids = [self._id(record) for record, occurs in zip(included, pattern) if occurs]
            count = len(occurrence_ids)
            recent = pattern[-self.rules.recent_window:]
            earlier_count = sum(pattern[:-self.rules.recent_window]) if len(pattern) > self.rules.recent_window else 0
            if count >= 3 and pattern[-1]: status = "persistent"
            elif len(pattern) >= 4 and earlier_count >= self.rules.minimum_prior_occurrences_for_reduction and not any(recent): status = "recently_reduced"
            elif count >= 2 and any(pattern) and not all(pattern): status = "recurring"
            elif count >= 2: status = "inconsistent"
            else: status = "insufficient_evidence"
            versions = sorted({str(record.get("diagnosis_version", "unknown")) for record in included})
            confidence = "medium" if len(included) >= 4 and len(versions) == 1 and status in {"persistent", "recently_reduced"} else "low" if count >= 2 else "insufficient"
            limitations = ["Trajectory uses structured heuristic diagnoses, not LLM prose or a mastery judgment."]
            if len(versions) > 1:
                confidence = "low"; limitations.append("Diagnosis rule versions differ; confidence is reduced.")
            results.append(IssueTrajectory(
                diagnosis_category=category, status=status, occurrence_count=count,
                comparable_submission_count=len(included), supporting_submission_ids=occurrence_ids,
                recent_pattern=recent, confidence=confidence, limitations=limitations,
                diagnosis_versions=versions,
            ))
        return results

    def _priorities(self, current: dict[str, Any], persistent: list[IssueTrajectory], reduced: list[IssueTrajectory], unstable: list[IssueTrajectory]) -> list[PriorityCandidate]:
        current_categories = self._categories(current)
        trajectories = {item.diagnosis_category: item for item in [*persistent, *unstable, *reduced]}
        ordered = list(dict.fromkeys([*current_categories, *(item.diagnosis_category for item in persistent)]))[:3]
        return [PriorityCandidate(
            diagnosis_category=category,
            rationale=(f"Current structured diagnosis and {trajectories[category].status} historical pattern." if category in trajectories else "Current structured diagnosis; longitudinal support is limited."),
            supporting_evidence_ids=(trajectories[category].supporting_submission_ids if category in trajectories else [self._id(current)]),
            confidence=(trajectories[category].confidence if category in trajectories else "low"),
            limitation="Candidate for teacher review and later feedback selection; not an automatic teaching prescription.",
        ) for category in ordered]

    def _metric_limitations(self, name: str) -> list[str]:
        items = ["Prototype thresholds require literature and empirical calibration."]
        if name in DESCRIPTIVE_METRICS:
            items.append("This is a descriptive output-volume metric and cannot directly indicate ability.")
        if name in LENGTH_SENSITIVE_METRICS:
            items.append("This metric is sensitive to text length and task conditions.")
        return items

    @staticmethod
    def _slope(values: list[float]) -> float:
        x_mean = (len(values) - 1) / 2
        y_mean = mean(values)
        denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
        return sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values)) / denominator

    @staticmethod
    def _metric(record: dict[str, Any], name: str) -> float:
        value = record["metrics"][name]
        return float(sum(value.values())) if isinstance(value, dict) else float(value)

    @staticmethod
    def _categories(record: dict[str, Any]) -> list[str]:
        return [item.get("category") for item in record.get("diagnosis", {}).get("improvement_priorities", []) if item.get("category")]

    @staticmethod
    def _id(record: dict[str, Any]) -> str: return f"E{int(record['essay_id']):06d}"

    @staticmethod
    def _datetime(record: dict[str, Any]) -> datetime:
        value = record["submitted_at"]
        if isinstance(value, datetime): return value
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)

    def _within(self, record: dict[str, Any], start: date | None, end: date | None) -> bool:
        observed = self._datetime(record).date()
        return (start is None or observed >= start) and (end is None or observed <= end)
