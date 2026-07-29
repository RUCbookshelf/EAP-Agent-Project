from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Confidence = Literal["low", "medium", "high"]
ComparabilityStatus = Literal[
    "comparable", "partially_comparable", "not_comparable", "insufficient_history"
]
ExerciseType = Literal["error_identification", "sentence_rewrite", "short_writing_transfer"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EssaySubmission(BaseModel):
    student_id: str = Field(min_length=1, max_length=100)
    writing_prompt: str = Field(min_length=1, max_length=4000)
    genre: str = Field(default="argumentative essay", min_length=1, max_length=100)
    draft_stage: str = Field(default="first draft", min_length=1, max_length=100)
    timed: bool = False
    time_limit_minutes: int | None = Field(default=None, ge=1, le=1440)
    tool_use: str = Field(default="none", max_length=300)
    essay_text: str = Field(min_length=1)
    submitted_at: datetime = Field(default_factory=utc_now)
    revision_of_submission_id: int | None = Field(default=None, ge=1)

    @field_validator("student_id", "writing_prompt", "genre", "draft_stage", "essay_text")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def validate_time_limit(self) -> "EssaySubmission":
        if not self.timed and self.time_limit_minutes is not None:
            raise ValueError("time_limit_minutes must be empty when timed is false")
        return self


class AnalysisResult(BaseModel):
    metrics: dict[str, Any]
    analysis_version: str
    limitations: str
    analysis_run_id: str | None = None
    analyzer_id: str = "basic"
    analyzer_version: str = "basic-analyzer-v0.1"
    backend: str = "regex"
    nlp_library: str | None = None
    nlp_library_version: str | None = None
    nlp_model_name: str | None = None
    nlp_model_version: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    resource_versions: dict[str, str] = Field(default_factory=dict)
    configuration_version: str = "legacy-default"
    fallback_used: bool = False
    fallback_reason: str | None = None
    analysis_duration_ms: float = Field(default=0.0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    input_quality: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    metric_results: list[dict[str, Any]] = Field(default_factory=list)


class DiagnosisSignal(BaseModel):
    diagnosis_id: str = Field(pattern=r"^D\d{3}$")
    category: str
    evidence: str
    source_metrics: list[str]
    interpretation: str
    confidence: Confidence
    limitation: str
    rule_version: str
    kind: Literal["strength", "improvement"]


class DiagnosisResult(BaseModel):
    strengths: list[DiagnosisSignal] = Field(max_length=1)
    improvement_priorities: list[DiagnosisSignal] = Field(min_length=1, max_length=2)
    diagnosis_version: str
    limitation: str

    @property
    def all_signals(self) -> list[DiagnosisSignal]:
        return [*self.strengths, *self.improvement_priorities]


class HistoryEvidence(BaseModel):
    history_evidence_id: str = Field(pattern=r"^H\d{3}$")
    evidence_type: Literal[
        "metric_change", "repeated_diagnosis", "previous_flag_not_current",
        "metric_trend", "issue_trajectory",
    ]
    description: str
    supporting_submission_ids: list[str]
    comparable_submission_count: int = Field(ge=1)
    confidence: Confidence
    limitation: str


class HistoryResult(BaseModel):
    comparability_status: ComparabilityStatus
    comparable_submission_count: int = Field(ge=0)
    history_evidence: list[HistoryEvidence]
    summary: str
    limitations: list[str]
    comparability_reasons: list[str]
    excluded_submission_ids: list[str] = Field(default_factory=list)


class PositiveFinding(BaseModel):
    evidence_quote: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class FeedbackItem(BaseModel):
    diagnosis_id: str = Field(pattern=r"^D\d{3}$")
    category: str
    evidence_quote: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    revision_guidance: str = Field(min_length=1)


class ExerciseItem(BaseModel):
    diagnosis_id: str = Field(pattern=r"^D\d{3}$")
    diagnosis_category: str
    exercise_type: ExerciseType
    instructions: str = Field(min_length=1)
    exercise_content: str = Field(min_length=1)
    expected_response: str | None = None
    reference_guidance: str | None = None
    source_type: Literal["student_source_sentence", "synthetic_practice_sentence"] = "synthetic_practice_sentence"
    source_submission_id: int | None = None
    generation_version: str = "exercise-generator-v0.5.0"

    @model_validator(mode="after")
    def require_response_support(self) -> "ExerciseItem":
        if not self.expected_response and not self.reference_guidance:
            raise ValueError("expected_response or reference_guidance is required")
        return self


class LongitudinalFeedback(BaseModel):
    comment: str = Field(min_length=1)
    history_evidence_ids: list[str]
    confidence: Confidence
    limitation: str = Field(min_length=1)


class RevisionFeedback(BaseModel):
    comment: str = Field(min_length=1)
    revision_evidence_ids: list[str]
    confidence: Confidence
    limitation: str = Field(min_length=1)


class StructuredFeedback(BaseModel):
    positive_finding: PositiveFinding
    priority_feedback: list[FeedbackItem] = Field(min_length=1, max_length=2)
    exercises: list[ExerciseItem] = Field(min_length=1)
    longitudinal: LongitudinalFeedback
    revision: RevisionFeedback | None = None
    uncertainty_note: str = Field(min_length=1)


class LLMCallAudit(BaseModel):
    prompt_version: str
    system_template_hash: str
    user_template_hash: str
    rendered_prompt_hash: str
    schema_version: str
    provider_name: str
    model_name: str
    temperature: float
    request_time: datetime
    response_time: datetime
    success_status: Literal["success", "failed", "fallback_success"]
    validation_status: Literal["passed", "failed", "not_run"]
    retry_count: int = Field(ge=0, le=1)
    fallback_reason: str | None = None


class ProviderResult(BaseModel):
    feedback: StructuredFeedback
    provider_name: str
    model_name: str
    success_status: Literal["success", "fallback_success"]
    validation_status: Literal["passed"] = "passed"
    retry_count: int = Field(ge=0, le=1)
    fallback_reason: str | None = None
    prompt_version: str
    system_template_hash: str
    user_template_hash: str
    rendered_prompt_hash: str
    schema_version: str
    temperature: float
    request_time: datetime
    response_time: datetime
    call_audits: list[LLMCallAudit]


class PipelineResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    essay_id: int
    analysis: AnalysisResult
    diagnosis: DiagnosisResult
    provider: ProviderResult
    history: HistoryResult
    history_summary: str
    comparable_history_count: int
    revision_snapshot: Any | None = None
