"""Wave-3 WU3 domain models (bounded, observation-only).

Every composed model is ``extra="forbid"`` and carries an explicit
``claims_status="observation_only"`` so no consumer can relabel the payload.
Practice/review evidence fields remain distinguishable from authentic-writing
observation fields; no field states or implies an outcome, rank, or cause.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.schemas import utc_now


OBSERVATION_ONLY = "observation_only"


class QualifiedActivity(BaseModel):
    """One qualified practice activity with full provenance + criteria."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1, max_length=100)
    target_code: str = Field(min_length=1)
    target_label: str = Field(min_length=1)
    category: str = Field(min_length=1)
    exercise_type: str = Field(min_length=1)
    exercise_version: str = Field(min_length=1)
    source_submission_id: int = Field(ge=1)
    source_priority_id: str | None = None
    evidence_ids: list[str] = Field(min_length=1)
    instructions: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    evaluation_criteria: dict[str, str] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)
    claims_status: Literal["observation_only"] = OBSERVATION_ONLY


class ActivityRecommendation(BaseModel):
    """Deterministic, explainable recommendation with learner choice."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1, max_length=100)
    state: Literal["recommended", "insufficient_history", "unavailable"]
    default_activity_id: str | None = None
    qualified_activities: list[QualifiedActivity] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    learner_choice_allowed: bool = True
    limitations: list[str] = Field(default_factory=list)
    claims_status: Literal["observation_only"] = OBSERVATION_ONLY


class ActivitySelection(BaseModel):
    """Explicit (or default) learner choice over a qualified activity."""

    model_config = ConfigDict(extra="forbid")

    selection_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1, max_length=100)
    recommendation_id: str = Field(min_length=1)
    activity: QualifiedActivity
    choice_kind: Literal["default", "explicit"] = "explicit"
    limitations: list[str] = Field(default_factory=list)
    claims_status: Literal["observation_only"] = OBSERVATION_ONLY


class ActivityEvaluation(BaseModel):
    """Deterministic rule-based evaluation of one attempt."""

    model_config = ConfigDict(extra="forbid")

    evaluation_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1, max_length=100)
    activity_id: str = Field(min_length=1)
    completion_status: str = Field(min_length=1)
    target_action_status: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    evaluator_version: str = Field(min_length=1)
    evaluation_method: Literal["rule_based"] = "rule_based"
    limitations: list[str] = Field(default_factory=list)
    claims_status: Literal["observation_only"] = OBSERVATION_ONLY


class MiniWritingResult(BaseModel):
    """Result of a bounded mini-writing submission through the pipeline."""

    model_config = ConfigDict(extra="forbid")

    result_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1, max_length=100)
    task_id: str = Field(min_length=1)
    submission_id: int = Field(ge=1)
    analysis_run_id: str = Field(min_length=1)
    analysis_version: str = Field(min_length=1)
    feedback_record_id: int | None = None
    essay_text_hash: str = Field(min_length=1)
    word_count: int = Field(ge=0)
    pipeline_adapter: str = Field(min_length=1)
    bounded: bool = True
    limitations: list[str] = Field(default_factory=list)
    claims_status: Literal["observation_only"] = OBSERVATION_ONLY


class TutorConsentSnapshot(BaseModel):
    """Explicit learner consent snapshot (structural LEARNER WU2 mirror).

    Consent is only ever validated by the Tutor service; missing, false,
    revoked, learner-mismatched, scoped-elsewhere, or future-dated consent
    fails closed with no execution.
    """

    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    granted: bool = False
    revoked: bool = False
    scope: str = Field(min_length=1)
    consent_version: str = Field(min_length=1)
    granted_at: datetime = Field(default_factory=utc_now)


class DueItem(BaseModel):
    """One due review item grounded in durable scheduler state."""

    model_config = ConfigDict(extra="forbid")

    learning_item_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1)
    due: datetime
    note: str = Field(min_length=1)


class PositiveObservation(BaseModel):
    """One bounded positive observation of authentic writing evidence."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1)
    target_code: str = Field(min_length=1)
    later_submission_id: int = Field(ge=1)
    statement: str = Field(min_length=1)
    non_causal_note: str = Field(min_length=1)
    evidence_kind: Literal["authentic_writing", "practice"] = "authentic_writing"
    limitations: list[str] = Field(default_factory=list)
    claims_status: Literal["observation_only"] = OBSERVATION_ONLY


class TutorRecommendation(BaseModel):
    """History/due-item grounded Tutor suggestion (never executed here)."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1, max_length=100)
    state: Literal[
        "due_item", "history_grounded", "insufficient_history",
        "positive_observation", "unavailable",
    ]
    learning_item_ids: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    suggestion: str = Field(min_length=1)
    history_reasons: list[str] = Field(default_factory=list)
    positive_observations: list[PositiveObservation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    claims_status: Literal["observation_only"] = OBSERVATION_ONLY


class TutorDecision(BaseModel):
    """Bounded outcome of a Tutor accept/decline decision."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1, max_length=100)
    recommendation_id: str = Field(min_length=1)
    decision: Literal["accept", "decline"]
    consent_applied: bool = False
    executed: bool = False
    action: str | None = None
    limitations: list[str] = Field(default_factory=list)
    claims_status: Literal["observation_only"] = OBSERVATION_ONLY


__all__ = [
    "ActivityEvaluation",
    "ActivityRecommendation",
    "ActivitySelection",
    "DueItem",
    "MiniWritingResult",
    "OBSERVATION_ONLY",
    "PositiveObservation",
    "QualifiedActivity",
    "TutorConsentSnapshot",
    "TutorDecision",
    "TutorRecommendation",
]
