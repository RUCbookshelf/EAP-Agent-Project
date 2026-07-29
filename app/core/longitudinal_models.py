from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ComparabilityDecision = Literal[
    "comparable", "partially_comparable", "not_comparable", "insufficient_information"
]
TrendDirection = Literal["increasing", "decreasing", "stable", "fluctuating", "insufficient_data"]
Variability = Literal["low", "moderate", "high", "insufficient_data"]
TrendConfidence = Literal["insufficient", "low", "medium"]
IssueStatus = Literal[
    "persistent", "recurring", "recently_reduced", "insufficient_evidence", "inconsistent"
]


class ComparabilityResult(BaseModel):
    current_submission_id: str
    historical_submission_id: str
    status: ComparabilityDecision
    matched_conditions: list[str]
    mismatched_conditions: list[str]
    reasons: list[str]
    confidence: TrendConfidence
    rule_version: str


class BaselineProfile(BaseModel):
    student_id: str
    baseline_status: Literal["available", "insufficient_history"]
    included_submission_ids: list[str]
    excluded_submission_ids: list[str]
    baseline_window: dict[str, Any]
    metric_summaries: dict[str, dict[str, float]]
    diagnosis_frequencies: dict[str, int]
    created_at: datetime
    analysis_version: str
    limitations: list[str]


class MetricObservation(BaseModel):
    submission_id: str
    submitted_at: datetime
    metric_value: float
    comparability_status: ComparabilityDecision
    included_in_trend: bool
    exclusion_reason: str | None = None


class MetricTrend(BaseModel):
    metric_name: str
    observations: list[MetricObservation]
    included_submission_ids: list[str]
    excluded_submission_ids: list[str]
    direction: TrendDirection
    slope: float | None
    variability: Variability
    data_points: int
    confidence: TrendConfidence
    interpretation: str
    limitations: list[str]
    analysis_version: str


class IssueTrajectory(BaseModel):
    diagnosis_category: str
    status: IssueStatus
    occurrence_count: int
    comparable_submission_count: int
    supporting_submission_ids: list[str]
    recent_pattern: list[bool]
    confidence: TrendConfidence
    limitations: list[str]
    diagnosis_versions: list[str]


class PriorityCandidate(BaseModel):
    diagnosis_category: str
    rationale: str
    supporting_evidence_ids: list[str]
    confidence: TrendConfidence
    limitation: str


class ExcludedSubmission(BaseModel):
    submission_id: str
    status: ComparabilityDecision
    reasons: list[str]


class LearnerProfileSnapshot(BaseModel):
    snapshot_id: str | None = Field(default=None, pattern=r"^LP\d{6}$")
    student_id: str
    snapshot_time: datetime
    included_submission_ids: list[str]
    excluded_submissions: list[ExcludedSubmission]
    baseline_status: Literal["available", "insufficient_history"]
    baseline_profile: BaselineProfile
    metric_trends: dict[str, MetricTrend]
    persistent_issues: list[IssueTrajectory]
    recently_reduced_issues: list[IssueTrajectory]
    unstable_issues: list[IssueTrajectory]
    current_priority_candidates: list[PriorityCandidate] = Field(max_length=3)
    confidence_summary: str
    limitations: list[str]
    analysis_version: str
    configuration_version: str
