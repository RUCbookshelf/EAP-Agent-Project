"""Two-level writing task model + revision/scaffold/learning-item contracts.

Goal PDW2-C-L2-REVISION-SCAFFOLD. The two-level task model separates:

- ``task_type``: the five-type operational taxonomy, UNCHANGED from the
  qualified L2 taxonomy contract (``l2-task-type-taxonomy-v1.0.0``, Domain
  Pack v1); ``legacy_unclassified`` remains the explicit D-22 sentinel.
- ``writing_context`` (genre): CET-4/6, IELTS Task 2, TOEFL-style, course
  essay, email, application, reflective journal, other -- with optional
  metadata (audience/purpose/word constraint/assessment environment/genre
  expectations).

Revision versioning is additive: WritingTask -> Submission V1 -> V2 -> V3
with ancestry, timestamps, task-context/analysis/feedback links. A revision
never overwrites prior submissions; historical versions are evidence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.schemas import utc_now


# ---------------------------------------------------------------------------
# Two-level task model
# ---------------------------------------------------------------------------

# The five-type operational taxonomy (unchanged; Domain Pack v1).
TASK_TYPE_IDS: tuple[str, ...] = (
    "opinion",
    "argumentative",
    "discussion",
    "problem_solution",
    "general_eap",
)

# D-22 sentinel for unclassifiable legacy rows (explicit allowed value).
LEGACY_UNCLASSIFIED: str = "legacy_unclassified"

ALLOWED_TASK_TYPE_IDS: tuple[str, ...] = (*TASK_TYPE_IDS, LEGACY_UNCLASSIFIED)

# Second level: writing context / genre.
WRITING_CONTEXT_IDS: tuple[str, ...] = (
    "cet4",
    "cet6",
    "ielts_task2",
    "toefl_style",
    "course_essay",
    "email",
    "application",
    "reflective_journal",
    "other",
)


class WritingTaskMetadata(BaseModel):
    """Optional task metadata (all fields optional)."""

    model_config = ConfigDict(extra="forbid")

    audience: str | None = Field(default=None, max_length=300)
    purpose: str | None = Field(default=None, max_length=300)
    word_constraint: str | None = Field(default=None, max_length=300)
    assessment_environment: str | None = Field(default=None, max_length=300)
    genre_expectations: list[str] = Field(default_factory=list, max_length=20)


class WritingTask(BaseModel):
    """One registered writing task with task-type + context (two levels)."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1, max_length=100)
    task_type: str = Field(min_length=1, max_length=64)
    writing_context: str = Field(min_length=1, max_length=64)
    writing_prompt: str = Field(min_length=1, max_length=4000)
    metadata: WritingTaskMetadata = Field(default_factory=WritingTaskMetadata)
    modality: Literal["written", "spoken"] = "written"
    classification: dict[str, Any] = Field(default_factory=dict)
    status: Literal["active", "closed"] = "active"
    created_at: datetime = Field(default_factory=utc_now)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        if value not in ALLOWED_TASK_TYPE_IDS:
            raise ValueError(
                f"Unknown task_type {value!r}; the L2 taxonomy is fixed to "
                f"{list(TASK_TYPE_IDS)} plus the legacy sentinel "
                f"{LEGACY_UNCLASSIFIED!r}."
            )
        return value

    @field_validator("writing_context")
    @classmethod
    def validate_writing_context(cls, value: str) -> str:
        if value not in WRITING_CONTEXT_IDS:
            raise ValueError(
                f"Unknown writing_context {value!r}; valid contexts: "
                f"{list(WRITING_CONTEXT_IDS)}."
            )
        return value

    @field_validator("writing_prompt")
    @classmethod
    def strip_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("writing_prompt must not be blank")
        return value


# ---------------------------------------------------------------------------
# Revision versioning
# ---------------------------------------------------------------------------


class SubmissionVersion(BaseModel):
    """One persisted submission version (V1/V2/V3...) with full linkage.

    ``ancestry`` is the ordered chain of submission ids from the root draft
    through this version. Task prompt + context are preserved on every
    version (task_context snapshot); analysis/feedback links point into the
    existing pipeline records. Versions are append-only: a revision always
    creates a NEW submission row; prior versions are never overwritten.
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    submission_id: int = Field(ge=1)
    version_number: int = Field(ge=1)
    revision_of_submission_id: int | None = Field(default=None, ge=1)
    ancestry: list[int] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=utc_now)
    task_context: dict[str, Any] = Field(default_factory=dict)
    essay_text_hash: str = Field(min_length=1)
    draft_stage: str = Field(default="first draft", min_length=1, max_length=100)
    analysis_run_id: str | None = None
    analysis_version: str | None = None
    feedback_record_id: int | None = None
    revision_group_id: str | None = None
    revision_snapshot_id: str | None = None
    corpus_routing: dict[str, Any] | None = None
    reanalysis_events: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ancestry_consistent(self) -> "SubmissionVersion":
        if self.ancestry and self.ancestry[-1] != self.submission_id:
            raise ValueError("ancestry must end with this submission_id")
        if self.version_number > 1 and self.revision_of_submission_id is None:
            raise ValueError("a revision version must declare revision_of_submission_id")
        if self.revision_of_submission_id is not None and self.version_number == 1:
            raise ValueError("V1 must not declare revision_of_submission_id")
        return self


# ---------------------------------------------------------------------------
# Revision observation (bounded, observational language only)
# ---------------------------------------------------------------------------


class RevisionObservation(BaseModel):
    """What changed between two versions, in observational language only.

    The record describes observed text changes and which previously
    provided feedback areas appear addressed/remaining; it NEVER infers
    learner intent, ability, mastery, proficiency, or learning outcomes.
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    source_submission_id: int = Field(ge=1)
    target_submission_id: int = Field(ge=1)
    observed_at: datetime = Field(default_factory=utc_now)
    what_changed: dict[str, Any] = Field(default_factory=dict)
    feedback_areas: list[dict[str, Any]] = Field(default_factory=list)
    new_observations: list[dict[str, Any]] = Field(default_factory=list)
    apparent_independent_corrections: list[dict[str, Any]] = Field(default_factory=list)
    no_intent_inference: str = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Personalized bridge: historical feedback, priority plan, scaffold
# ---------------------------------------------------------------------------

HistoricalFeedbackStatus = Literal[
    "recurring", "stable", "reappeared", "first_observed", "insufficient_history",
]


class HistoricalFeedbackItem(BaseModel):
    """One learner-observed feedback area over stored submissions."""

    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    status: HistoricalFeedbackStatus
    occurrence_count: int = Field(ge=0)
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    supporting_submission_ids: list[int] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    revision_success_note: str | None = None
    history_state: str = "sufficient"
    history_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    claims_status: str = "observation_only"


class HistoricalFeedbackView(BaseModel):
    """Historical feedback summary with explicit sufficiency state."""

    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1)
    history_state: Literal["sufficient", "insufficient_history"]
    items: list[HistoricalFeedbackItem] = Field(default_factory=list)
    history_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class LocalObservationItem(BaseModel):
    """One bounded local observation of the current submission."""

    model_config = ConfigDict(extra="forbid")

    feature_id: str = Field(min_length=1)
    value: Any = None
    available: bool = True
    statement: str = Field(min_length=1)
    limitation: str = Field(min_length=1)


class GlobalObservationItem(BaseModel):
    """One bounded whole-text observation across stored submissions."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    scope: str = "whole_text"
    kind: str = Field(min_length=1)
    value: Any = None
    descriptive_statement: str = Field(min_length=1)
    limitation: str = Field(min_length=1)


class PriorityPlanItem(BaseModel):
    """One small actionable plan item (never a proficiency ranking)."""

    model_config = ConfigDict(extra="forbid")

    plan_item_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    diagnosis_id: str | None = None
    recurrence_status: HistoricalFeedbackStatus
    context: dict[str, Any] = Field(default_factory=dict)
    action_statement: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: str = "low"
    ordering_note: str = (
        "action-priority ordering only; not a learner-performance ranking"
    )
    limitations: list[str] = Field(default_factory=list)


class PriorityRevisionPlan(BaseModel):
    """Small actionable revision plan: local + global + historical feedback."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    submission_id: int = Field(ge=1)
    generated_at: datetime = Field(default_factory=utc_now)
    items: list[PriorityPlanItem] = Field(default_factory=list)
    history_state: Literal["sufficient", "insufficient_history"]
    history_reasons: list[str] = Field(default_factory=list)
    local_observations: list[LocalObservationItem] = Field(default_factory=list)
    global_observations: list[GlobalObservationItem] = Field(default_factory=list)
    historical_feedback: list[HistoricalFeedbackItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    claims_status: str = "observation_only"


class ScaffoldContent(BaseModel):
    """Content of one scaffold level (deterministic, bounded)."""

    model_config = ConfigDict(extra="forbid")

    level: int = Field(ge=1, le=7)
    kind: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ScaffoldResponse(BaseModel):
    """One scaffold reveal (default SCAFFOLD FIRST)."""

    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    level: int = Field(ge=1, le=7)
    default_first: bool
    available_levels: list[int] = Field(default_factory=lambda: list(range(1, 8)))
    content: ScaffoldContent
    learner_action: str = Field(min_length=1)
    never_writes_statement: str = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


class ScaffoldEvent(BaseModel):
    """One recorded scaffold request (scaffold history)."""

    model_config = ConfigDict(extra="forbid")

    scaffold_event_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1)
    learning_item_id: str | None = None
    plan_item_id: str | None = None
    category: str = Field(min_length=1)
    level: int = Field(ge=1, le=7)
    requested_at: datetime = Field(default_factory=utc_now)
    default_first: bool
    limitations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# LearningItem v1
# ---------------------------------------------------------------------------

LearningItemStatus = Literal["proposed", "active", "superseded", "closed"]


class LearningItem(BaseModel):
    """Durable learning target linked to learner/evidence/feedback/revisions.

    LearningItem v1 is a durable learning target derived from a priority
    plan item; it is NOT per-generated-exercise, has NO FSRS scheduling, and
    has NO practice/tutor expansion. Status transitions are explicit.
    """

    model_config = ConfigDict(extra="forbid")

    learning_item_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1)
    originating_evidence: dict[str, Any] = Field(default_factory=dict)
    feedback_reference: str | None = None
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    task_id: str | None = None
    task_context: dict[str, Any] = Field(default_factory=dict)
    status: LearningItemStatus = "proposed"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    no_fsrs_note: str = (
        "no FSRS scheduling or spaced-repetition state is stored in "
        "LearningItem v1"
    )
    no_practice_note: str = (
        "no practice or tutor expansion is attached to LearningItem v1"
    )
    limitations: list[str] = Field(default_factory=list)


__all__ = [
    "ALLOWED_TASK_TYPE_IDS",
    "HistoricalFeedbackItem",
    "HistoricalFeedbackStatus",
    "HistoricalFeedbackView",
    "LEGACY_UNCLASSIFIED",
    "LearningItem",
    "LearningItemStatus",
    "LocalObservationItem",
    "PriorityPlanItem",
    "PriorityRevisionPlan",
    "RevisionObservation",
    "ScaffoldContent",
    "ScaffoldEvent",
    "ScaffoldResponse",
    "SubmissionVersion",
    "TASK_TYPE_IDS",
    "WRITING_CONTEXT_IDS",
    "WritingTask",
    "WritingTaskMetadata",
]
