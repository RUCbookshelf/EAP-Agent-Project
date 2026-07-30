from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.schemas import utc_now


RevisionStage = Literal["first_draft", "revised_draft", "final_draft", "independent_submission"]
AlignmentType = Literal["unchanged", "lightly_modified", "heavily_modified", "inserted", "deleted", "split", "merged", "unaligned"]


class RevisionGroup(BaseModel):
    revision_group_id: str | None = None
    student_id: str
    writing_prompt: str
    genre: str
    root_submission_id: int
    member_submission_ids: list[int]
    current_revision_id: int
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata_consistency: dict[str, bool] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class RevisionComparabilityResult(BaseModel):
    status: Literal["direct_revision", "partial_revision", "major_rewrite", "not_comparable", "insufficient_information"]
    matched_conditions: list[str]
    mismatched_conditions: list[str]
    reasons: list[str]
    confidence: Literal["low", "medium", "insufficient"]
    rule_version: str = "revision-comparability-v0.5.0"


class SegmentAlignment(BaseModel):
    alignment_id: str
    level: Literal["paragraph", "sentence"]
    source_segment_id: str | None
    target_segment_id: str | None
    source_text: str | None
    target_text: str | None
    similarity: float = Field(ge=0, le=1)
    alignment_type: AlignmentType
    algorithm_version: str = "local-sequence-alignment-v0.5.0"
    confidence: Literal["low", "medium", "high"]
    limitations: list[str] = Field(default_factory=list)


class MetricChange(BaseModel):
    metric_id: str
    source_value: Any = None
    target_value: Any = None
    change: Any = None
    comparison_status: Literal["compatible", "incompatible_version", "insufficient_data"]
    source_analyzer_version: str
    target_analyzer_version: str
    limitations: list[str] = Field(default_factory=list)


class DiagnosisTrajectory(BaseModel):
    trajectory_id: str
    diagnosis_category: str
    status: Literal["still_observed", "not_currently_observed", "reduced_signal", "newly_observed", "changed_evidence", "not_comparable", "insufficient_evidence"]
    source_diagnosis_ids: list[str]
    target_diagnosis_ids: list[str]
    supporting_submission_ids: list[int]
    confidence: Literal["low", "medium", "insufficient"]
    limitations: list[str]


class FeedbackUptakeCandidate(BaseModel):
    uptake_id: str
    previous_feedback_id: int
    previous_diagnosis_id: str
    source_submission_id: int
    target_submission_id: int
    previous_guidance_summary: str
    observed_change: str
    supporting_alignment_ids: list[str]
    status: Literal["supported", "partially_supported", "not_observed", "contradictory", "not_assessable"]
    confidence: Literal["low", "medium", "insufficient"]
    limitations: list[str]
    rule_version: str = "feedback-uptake-v0.5.0"


class RevisionSnapshot(BaseModel):
    revision_snapshot_id: str | None = None
    revision_group_id: str
    source_submission_id: int
    target_submission_id: int
    comparability: RevisionComparabilityResult
    paragraph_alignments: list[SegmentAlignment]
    sentence_alignments: list[SegmentAlignment]
    token_changes: dict[str, Any]
    metric_changes: list[MetricChange]
    diagnosis_trajectories: list[DiagnosisTrajectory]
    uptake_candidates: list[FeedbackUptakeCandidate]
    revision_evidence: list[dict[str, Any]]
    major_rewrite: bool
    analyzer_versions: dict[str, str]
    algorithm_versions: dict[str, str]
    resource_versions: dict[str, str]
    configuration_version: str = "revision-config-v0.5.0"
    generated_at: datetime = Field(default_factory=utc_now)
    limitations: list[str]


class RevisionDraftChainItem(BaseModel):
    submission_id: int
    draft_stage: str
    revision_sequence: int
    submitted_at: datetime
    writing_prompt: str
    revision_group_id: str


class RevisionGroupSummary(BaseModel):
    revision_group_id: str
    draft_submission_count: int = Field(ge=1)
    revision_group_count: Literal[1] = 1
    independent_task_count: Literal[1] = 1
    longitudinal_representative_count: Literal[1] = 1


class RevisionTrajectoryComparison(BaseModel):
    source_submission_id: int
    target_submission_id: int
    token_changes: dict[str, Any]
    metric_changes: list[MetricChange]
    diagnosis_changes: list[DiagnosisTrajectory]
    major_rewrite: bool
    attribution_confidence: Literal["low", "insufficient"]
    limitations: list[str] = Field(default_factory=list)


class WithinTaskRevisionTrajectory(BaseModel):
    revision_group_id: str
    draft_chain: list[RevisionDraftChainItem]
    pairwise_comparisons: list[RevisionTrajectoryComparison]
    first_to_latest_comparison: RevisionTrajectoryComparison | None = None
    diagnosis_changes: list[DiagnosisTrajectory] = Field(default_factory=list)
    metric_changes: list[MetricChange] = Field(default_factory=list)
    previous_selected_priorities: list[dict[str, Any]] = Field(default_factory=list)
    current_priority_status: list[dict[str, Any]] = Field(default_factory=list)
    feedback_uptake_candidates: list[FeedbackUptakeCandidate] = Field(default_factory=list)
    attribution_confidence: Literal["low", "insufficient"]
    major_rewrite_detected: bool
    limitations: list[str] = Field(default_factory=list)
