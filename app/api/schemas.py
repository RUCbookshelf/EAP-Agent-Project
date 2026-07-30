from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core import IssueTrajectory, LearnerProfileSnapshot, PriorityCandidate
from app.models import (
    AnalysisResult, DiagnosisResult, EssaySubmission, FeedbackProviderStatus,
    HistoryResult, LongitudinalAssessment, ProviderResult,
)
from app.revision import (
    RevisionGroup, RevisionGroupSummary, RevisionSnapshot, WithinTaskRevisionTrajectory,
)
from app.configuration import ConfigurationCreate, ConfigurationVersion
from app.services.admin_reanalysis import ReanalysisRequest
from app.calibration import DiagnosticCalibrationResult


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class SubmissionCreateRequest(EssaySubmission):
    essay_text: str = Field(min_length=1, max_length=50_000)


class SubmissionResponse(BaseModel):
    submission_id: int
    analysis: AnalysisResult
    diagnosis: DiagnosisResult
    feedback_result: ProviderResult
    history: HistoryResult
    revision_snapshot: RevisionSnapshot | None = None
    diagnostic_calibration: DiagnosticCalibrationResult | None = None
    feedback_provider_status: FeedbackProviderStatus | None = None
    longitudinal_assessment: LongitudinalAssessment | None = None
    revision_group_summary: RevisionGroupSummary | None = None
    within_task_revision_trajectory: WithinTaskRevisionTrajectory | None = None
    ui_empty_states: list[str] = Field(default_factory=list)


class RevisionCreateRequest(BaseModel):
    source_submission_id: int = Field(ge=1)
    target_submission_id: int = Field(ge=1)


class RevisionGroupResponse(BaseModel):
    group: RevisionGroup
    latest_snapshot: RevisionSnapshot | None = None
    snapshot_history_count: int


class SubmissionRecordResponse(BaseModel):
    submission_id: int
    student_id: str
    writing_prompt: str
    genre: str
    draft_stage: str
    timed: bool
    time_limit_minutes: int | None
    tool_use: str
    essay_text: str
    submitted_at: datetime
    analysis: dict[str, Any] | None
    diagnosis: dict[str, Any] | None
    feedback: dict[str, Any] | None
    provider_name: str | None
    model_name: str | None
    success_status: str | None
    prompt_version: str | None
    schema_version: str | None
    history_summary: str | None
    provider_status: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    application_version: str
    api_version: str
    database_status: Literal["connected", "unavailable"]
    database_migration_version: int
    prompt_version: str
    schema_version: str
    llm_provider: str
    llm_api_configured: bool
    active_analyzer: str = "basic"
    active_analyzer_version: str = "basic-analyzer-v0.1"
    spacy_installed: bool = False
    nlp_model_name: str | None = None
    nlp_model_installed: bool = False
    nlp_model_version: str | None = None
    analyzer_fallback_active: bool = False
    analyzer_fallback_reason: str | None = None


class VersionResponse(BaseModel):
    application_version: str
    api_version: str
    prompt_version: str
    schema_version: str
    analysis_version: str
    diagnosis_version: str
    database_migration_version: int
    active_analyzer: str = "basic"
    nlp_library_version: str | None = None
    nlp_model_name: str | None = None
    nlp_model_version: str | None = None
    metric_versions: dict[str, list[str]] = Field(default_factory=dict)
    comparability_version: str = "comparability-v0.3.0"
    baseline_version: str = "longitudinal-baseline-v0.3.0"
    trend_version: str = "longitudinal-trend-v0.3.0"
    revision_alignment_version: str = "local-sequence-alignment-v0.5.0"
    feedback_uptake_version: str = "feedback-uptake-v0.5.0"
    provider: str
    model: str
    active_configuration_version: str
    learner_profile_version: str = "learner-profile-v0.7.0"
    task_cluster_version: str = "task-cluster-v0.7.0"
    metric_trajectory_version: str = "metric-trajectory-v0.7.0"
    diagnostic_trajectory_version: str = "diagnostic-trajectory-v0.7.0"
    history_evidence_version: str = "history-evidence-v0.7.0"


class ConfigurationRollbackRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    actor: str = Field(default="local_researcher", min_length=1, max_length=100)


class ReanalysisResponse(BaseModel):
    submission_id: int
    analysis: AnalysisResult
    llm_called: Literal[False] = False


class StudentResponse(BaseModel):
    student_id: str
    created_at: datetime
    is_synthetic: bool
    submission_count: int


class HistoryResponse(BaseModel):
    student_id: str
    submissions: list[dict[str, Any]]
    history_records: list[dict[str, Any]]


class PlannedLongitudinalResponse(BaseModel):
    student_id: str
    status: Literal["not_available", "insufficient_history", "planned_for_v0.3"]
    submission_count: int
    message: str
    limitations: list[str]


class LearnerProfileResponse(BaseModel):
    student_id: str
    submission_count: int
    comparable_submission_count: int
    latest_snapshot: LearnerProfileSnapshot
    analysis_version: str
    history_sufficiency: Literal["available", "insufficient_history"]
    persistent_issues: list[IssueTrajectory]
    recently_reduced_issues: list[IssueTrajectory]
    current_priority_candidates: list[PriorityCandidate]
    limitations: list[str]
    snapshot_history_count: int


class LearnerModelBuildRequest(BaseModel):
    representative_draft_strategy: Literal[
        "final_or_latest", "first_draft_only", "latest_draft_only", "all_drafts_research_mode",
    ] = "final_or_latest"
    max_submissions: int = Field(default=200, ge=1, le=200)
