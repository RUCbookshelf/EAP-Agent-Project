# v0.9 Practice schemas — Feedback–Practice–Transfer Foundation
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import utc_now


class PracticeTargetStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PRACTICE_NOT_AVAILABLE = "practice_not_available"
    ARCHIVED = "archived"


class ExerciseType(StrEnum):
    GUIDED_SENTENCE_REWRITE = "guided_sentence_rewrite"
    CONSTRAINED_MICRO_REVISION = "constrained_micro_revision"
    TARGET_FEATURE_IDENTIFICATION = "target_feature_identification"


class AttemptStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    ABANDONED = "abandoned"
    INVALID_INPUT = "invalid_input"


class CompletionStatus(StrEnum):
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


class TargetActionStatus(StrEnum):
    CANDIDATE_DETECTED = "candidate_detected"
    CANDIDATE_NOT_DETECTED = "candidate_not_detected"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"


class EvaluationMethod(StrEnum):
    RULE_BASED = "rule_based"
    LLM_ASSISTED_CANDIDATE = "llm_assisted_candidate"


class TraceStatus(StrEnum):
    TARGET_IDENTIFIED = "target_identified"
    PRACTICE_AVAILABLE = "practice_available"
    PRACTICE_ATTEMPTED = "practice_attempted"
    PRACTICE_RESPONSE_CANDIDATE = "practice_response_candidate"
    WITHIN_TASK_RESPONSE_CANDIDATE = "within_task_response_candidate"
    LATER_TASK_RECURRENCE = "later_task_recurrence"
    LATER_TASK_NONRECURRENCE = "later_task_nonrecurrence"
    LATER_TASK_MIXED_EVIDENCE = "later_task_mixed_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ARCHIVED = "archived"


class TransferObservedStatus(StrEnum):
    RECURRENCE_SIGNAL = "recurrence_signal"
    NONRECURRENCE_SIGNAL = "nonrecurrence_signal"
    MIXED_SIGNAL = "mixed_signal"
    NOT_COMPARABLE = "not_comparable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    VERSION_INCOMPATIBLE = "version_incompatible"


class PracticeTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    practice_target_id: str = Field(default="")
    student_id: str
    source_submission_id: int
    source_analysis_run_id: str | None = None
    source_diagnosis_id: str
    source_priority_id: str | None = None
    target_code: str
    target_label: str
    target_scope: str = "within_task"
    evidence_ids: list[str] = Field(default_factory=list)
    diagnostic_gate_status: str = "selected"
    diagnostic_version: str = "diagnostic-v0.6.1"
    configuration_version: str = "config-v0.9.0"
    status: PracticeTargetStatus = PracticeTargetStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class ExerciseSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exercise_type: ExerciseType
    exercise_version: str = "exercise-v0.9.0"
    supported_target_codes: list[str]
    learner_instructions: dict[str, str]
    input_requirements: str
    generation_method: str = "deterministic_template"
    evaluation_method: str = "rule_based"
    completion_criteria: str
    observable_target_criteria: str
    limitations: list[str] = Field(default_factory=list)
    student_eligible: bool = True
    localization_keys: dict[str, str] = Field(default_factory=dict)


class ExerciseInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exercise_id: str | None = Field(default=None, pattern=r"^EX\d{6}$")
    practice_target_id: str = ""
    student_id: str = ""
    source_submission_id: int
    exercise_type: ExerciseType
    exercise_version: str = "exercise-v0.9.0"
    instructions: str
    source_text: str
    target_evidence_ids: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    generation_provider: str = "deterministic_template"
    generation_model: str | None = None
    generation_prompt_version: str | None = None
    validation_status: str = "passed"
    limitations: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class ExerciseAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt_id: str | None = Field(default=None, pattern=r"^EA\d{6}$")
    exercise_id: str
    student_id: str
    attempt_number: int = Field(ge=1)
    response_text: str
    started_at: str | None = None
    submitted_at: str = Field(default_factory=lambda: utc_now().isoformat())
    duration_seconds: float | None = None
    timing_source: str = "server_timestamp"
    hint_count: int = 0
    status: AttemptStatus = AttemptStatus.SUBMITTED
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class PracticeEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluation_id: str | None = Field(default=None, pattern=r"^PE\d{6}$")
    attempt_id: str | None = None
    practice_target_id: str | None = None
    evaluation_method: EvaluationMethod = EvaluationMethod.RULE_BASED
    completion_status: CompletionStatus
    target_action_status: TargetActionStatus
    evidence: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    limitations: list[str] = Field(default_factory=list)
    evaluator_version: str = "practice-evaluator-v0.9.0"
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class FeedbackEngagementTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trace_id: str | None = Field(default=None, pattern=r"^FET\d{6}$")
    student_id: str
    target_code: str
    source_priority_id: str | None = None
    practice_target_id: str | None = None
    exercise_ids: list[str] = Field(default_factory=list)
    attempt_ids: list[str] = Field(default_factory=list)
    within_task_evidence_ids: list[str] = Field(default_factory=list)
    later_task_evidence_ids: list[str] = Field(default_factory=list)
    status: TraceStatus = TraceStatus.TARGET_IDENTIFIED
    confidence: str = "limited"
    limitations: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class WithinTaskResponseCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    response_id: str | None = Field(default=None, pattern=r"^WTR\d{6}$")
    student_id: str
    practice_target_id: str = ""
    source_submission_id: int
    later_submission_id: int
    revision_group_id: str | None = None
    target_code: str
    observed_status: str
    comparison_version: str = "revision-comparison-v0.7.1"
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "limited"
    limitations: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class TransferEvidenceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transfer_evidence_id: str | None = Field(default=None, pattern=r"^TE\d{6}$")
    student_id: str
    practice_target_id: str = ""
    source_submission_id: int
    later_submission_id: int
    task_comparability: str
    target_code: str
    observed_status: TransferObservedStatus
    history_evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "limited"
    limitations: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class PracticeStateSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    practice_state_snapshot_id: str | None = Field(default=None, pattern=r"^PSS\d{6}$")
    student_id: str
    snapshot_version: str = "practice-state-v0.9.0"
    current_targets: list[dict[str, Any]] = Field(default_factory=list)
    practice_summary: dict[str, Any] = Field(default_factory=dict)
    within_task_response_summary: dict[str, Any] = Field(default_factory=dict)
    later_task_evidence_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


def default_exercise_specifications() -> dict[str, ExerciseSpecification]:
    return {
        ExerciseType.GUIDED_SENTENCE_REWRITE.value: ExerciseSpecification(
            exercise_type=ExerciseType.GUIDED_SENTENCE_REWRITE,
            supported_target_codes=["lexical_repetition_local", "connective_overuse", "long_sentence"],
            learner_instructions={"en": "Rewrite the following sentence to address the selected priority.", "zh_CN": "请重写以下句子以解决选定的优先级问题。"},
            input_requirements="A source sentence from the student's essay.",
            completion_criteria="A non-empty rewritten sentence that addresses the target.",
            observable_target_criteria="The targeted feature is reduced or removed.",
            limitations=["Completion does not prove mastery or learning."],
        ),
        ExerciseType.CONSTRAINED_MICRO_REVISION.value: ExerciseSpecification(
            exercise_type=ExerciseType.CONSTRAINED_MICRO_REVISION,
            supported_target_codes=["lexical_repetition_local", "connective_overuse", "vague_organization"],
            learner_instructions={"en": "Revise this short text under the given constraints.", "zh_CN": "请在给定约束下修改这段短文。"},
            input_requirements="A short text span from the student's essay.",
            completion_criteria="A revised text that meets all constraints.",
            observable_target_criteria="The constraint is satisfied without adding unsupported content.",
            limitations=["Meeting constraints does not prove proficiency."],
        ),
        ExerciseType.TARGET_FEATURE_IDENTIFICATION.value: ExerciseSpecification(
            exercise_type=ExerciseType.TARGET_FEATURE_IDENTIFICATION,
            supported_target_codes=["lexical_repetition_local", "connective_overuse", "long_sentence"],
            learner_instructions={"en": "Identify which part of the passage illustrates the selected issue.", "zh_CN": "请指出文章中哪个部分体现了所选问题。"},
            input_requirements="A short passage containing the target feature.",
            completion_criteria="A valid identification or selection.",
            observable_target_criteria="The learner identifies the correct feature.",
            limitations=["Identification does not prove writing transfer."],
        ),
    }
