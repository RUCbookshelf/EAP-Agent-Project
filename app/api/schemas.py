from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core import IssueTrajectory, LearnerProfileSnapshot, PriorityCandidate
from app.models import AnalysisResult, DiagnosisResult, EssaySubmission, HistoryResult, ProviderResult


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


class VersionResponse(BaseModel):
    application_version: str
    api_version: str
    prompt_version: str
    schema_version: str
    analysis_version: str
    diagnosis_version: str
    database_migration_version: int


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
