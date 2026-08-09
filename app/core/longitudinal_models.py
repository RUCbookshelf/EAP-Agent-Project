from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ComparabilityDecision = Literal[
    "comparable", "partially_comparable", "not_comparable", "insufficient_information"
]
TrendDirection = Literal["increasing", "decreasing", "stable", "fluctuating", "insufficient_data"]
Variability = Literal["low", "moderate", "high", "insufficient_data"]
TrendConfidence = Literal["insufficient", "low", "medium"]
IssueStatus = Literal[
    "persistent", "recurring", "recently_reduced", "insufficient_evidence", "inconsistent"
]

DataSufficiencyStatus = Literal[
    "insufficient", "limited", "provisional", "adequate_for_descriptive_trend",
]
MetricTrajectoryDirection = Literal[
    "increasing_signal", "decreasing_signal", "stable", "variable",
    "insufficient_data", "not_comparable",
]
DiagnosticTrajectoryStatus = Literal[
    "emerging_pattern", "recurring_pattern", "persistent_pattern",
    "recently_reduced_signal", "not_currently_observed", "variable_pattern",
    "insufficient_evidence", "not_comparable",
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


class TaskCluster(BaseModel):
    task_cluster_id: str = Field(pattern=r"^TC\d{3}$")
    student_id: str
    cluster_type: str
    genre: str
    writing_purpose: str
    timed: bool
    time_limit_band: str
    tool_use: str
    task_mode: Literal["independent_task", "revision_task"]
    prompt_family: str
    analyzer_family: str
    metric_version_signature: str
    submission_ids: list[str]
    representative_submission_ids: list[str]
    excluded_submission_ids: list[str] = Field(default_factory=list)
    comparability_status: Literal["comparable", "limited", "not_comparable"]
    confidence: TrendConfidence
    rule_version: str = "task-cluster-v0.8.0"
    limitations: list[str] = Field(default_factory=list)


class DataSufficiency(BaseModel):
    status: DataSufficiencyStatus
    historical_submission_count: int = Field(ge=0)
    independent_task_count: int = Field(ge=0)
    current_task_cluster_count: int = Field(ge=0)
    valid_metric_result_count: int = Field(ge=0)
    selected_diagnosis_count: int = Field(ge=0)
    time_span_days: float = Field(ge=0)
    analyzer_compatible: bool
    metric_versions_compatible: bool
    metadata_missing_count: int = Field(ge=0)
    revision_duplicate_count: int = Field(ge=0)
    input_quality_exclusion_count: int = Field(ge=0)
    input_quality_issue_count: int = Field(default=0, ge=0)
    thresholds: dict[str, int]
    rule_version: str = "data-sufficiency-v0.7.0"
    explanation: str
    limitations: list[str] = Field(default_factory=list)


class MetricTrajectoryPoint(BaseModel):
    submission_id: str
    analysis_run_id: str | None = None
    submitted_at: datetime
    value: float
    metric_confidence: str


class MetricTrajectory(BaseModel):
    trajectory_id: str = Field(pattern=r"^MT\d{3}$")
    metric_id: str
    metric_version: str
    analyzer_version: str
    task_cluster_id: str
    data_points: list[MetricTrajectoryPoint]
    included_submission_ids: list[str]
    excluded_submission_ids: list[str]
    exclusion_reasons: dict[str, list[str]] = Field(default_factory=dict)
    direction: MetricTrajectoryDirection
    variability: Literal["low", "moderate", "high", "insufficient_data"]
    confidence: TrendConfidence
    trend_status: Literal[
        "insufficient", "limited_pairwise_comparison", "provisional_pattern",
        "adequate_for_descriptive_trend", "not_comparable",
    ]
    slope: float | None = None
    relative_change: float | None = None
    pairwise_difference: float | None = None
    algorithm_version: str = "metric-trajectory-v0.7.0"
    limitations: list[str] = Field(default_factory=list)


class DiagnosticEvidenceCount(BaseModel):
    selected_priority: int = 0
    eligible_diagnosis: int = 0
    monitored_signal: int = 0
    suppressed: int = 0
    insufficient_evidence: int = 0


class DiagnosticTrajectoryV2(BaseModel):
    trajectory_id: str = Field(pattern=r"^DTL\d{3}$")
    diagnosis_category: str
    task_cluster_id: str
    status: DiagnosticTrajectoryStatus
    comparable_task_count: int = Field(ge=0)
    evidence_counts: DiagnosticEvidenceCount
    selected_submission_ids: list[str]
    auxiliary_submission_ids: list[str]
    research_only_submission_ids: list[str]
    diagnosis_versions: list[str]
    current_selection_status: str
    current_evidence_verified: bool
    confidence: TrendConfidence
    algorithm_version: str = "diagnostic-trajectory-v0.7.0"
    limitations: list[str] = Field(default_factory=list)


class LearningTarget(BaseModel):
    target_id: str = Field(pattern=r"^LT\d{3}$")
    category: str
    status: Literal["active", "monitoring"]
    source_trajectory_id: str
    supporting_submission_ids: list[str]
    history_evidence_ids: list[str]
    current_evidence_id: str
    selection_reason: str
    confidence: TrendConfidence
    priority: int = Field(ge=1, le=2)
    algorithm_version: str = "learning-target-v0.7.0"
    limitations: list[str] = Field(default_factory=list)


class StrengthPattern(BaseModel):
    strength_pattern_id: str = Field(pattern=r"^SP\d{3}$")
    category: str
    status: Literal[
        "observed_once", "recurring_strength", "stable_strength_signal", "insufficient_evidence",
    ]
    supporting_submission_ids: list[str]
    evidence_quotes: list[str]
    confidence: TrendConfidence
    rule_version: str = "strength-pattern-v0.7.0"
    limitations: list[str] = Field(default_factory=list)


class HistoryEvidenceRecord(BaseModel):
    history_evidence_id: str | None = Field(default=None, pattern=r"^HE\d{6}$")
    student_id: str
    evidence_type: Literal[
        "metric_pairwise", "metric_trajectory", "diagnostic_trajectory",
        "current_learning_target", "strength_pattern",
    ]
    source_submission_ids: list[str]
    source_analysis_run_ids: list[str] = Field(default_factory=list)
    source_diagnosis_ids: list[str] = Field(default_factory=list)
    source_metric_ids: list[str] = Field(default_factory=list)
    source_snapshot_id: str | None = None
    task_cluster_id: str
    evidence_text: str
    character_offsets: list[dict[str, int]] = Field(default_factory=list)
    evidence_status: Literal["verified", "partially_verified", "insufficient_evidence"]
    version_compatibility: Literal["compatible", "not_comparable"]
    confidence: TrendConfidence
    registry_version: str = "history-evidence-v0.7.0"
    limitations: list[str] = Field(default_factory=list)


class LearnerProfileSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str | None = Field(default=None, pattern=r"^(LP|LPS)\d{6}$")
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
    revision_representative_policy: str = "final_draft_else_latest_v0.5"
    revision_representative_submission_ids: list[str] = Field(default_factory=list)
    profile_version: str = "learner-profile-v0.3.0"
    generated_at: datetime | None = None
    source_submission_ids: list[str] = Field(default_factory=list)
    representative_submission_ids: list[str] = Field(default_factory=list)
    excluded_submission_ids: list[str] = Field(default_factory=list)
    task_clusters: list[TaskCluster] = Field(default_factory=list)
    metric_trajectories: list[MetricTrajectory] = Field(default_factory=list)
    diagnostic_trajectories: list[DiagnosticTrajectoryV2] = Field(default_factory=list)
    current_learning_targets: list[LearningTarget] = Field(default_factory=list, max_length=2)
    strength_patterns: list[StrengthPattern] = Field(default_factory=list)
    data_sufficiency: DataSufficiency | None = None
    comparability_summary: dict[str, Any] = Field(default_factory=dict)
    analysis_versions: dict[str, list[str]] = Field(default_factory=dict)
    algorithm_versions: dict[str, str] = Field(default_factory=dict)
    history_evidence: list[HistoryEvidenceRecord] = Field(default_factory=list)
    representative_draft_strategy: str = "final_or_latest"
