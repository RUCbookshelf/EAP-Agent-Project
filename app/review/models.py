"""Shared Review / Scheduling Foundation record contracts (CORE, Wave-3 WU1).

Contracts owned here (minimum qualified set):

- ``Rating``: the ordered rating space ``Again / Hard / Good / Easy``,
  equivalent to the qualified FSRS library enum (py-fsrs ``Rating``:
  Again=1, Hard=2, Good=3, Easy=4). Rating channels are NEVER collapsed
  into a weighted average.
- ``PracticeActivity``: a shared activity representation DISTINCT from
  ``LearningItem`` (stable activity identity, learner and LearningItem
  identity, activity type, creation/source, status, timestamps, provenance,
  evaluator/evaluation linkage). Practice evidence stays distinguishable
  from authentic writing evidence; practice completion never implies
  authentic transfer.
- ``ReviewEvent``: a durable review event preserving learner, LearningItem,
  the relevant PracticeActivity link, system provisional rating, learner
  self-rating, final scheduler rating, rating-rule version, review
  timestamp, scheduling result, and provenance.
- ``SchedulerStateSnapshot`` / ``SchedulingResult`` / ``SchedulerIdentity``:
  the persisted FSRS memory-scheduling state and its explicit
  implementation/version identity.

Semantic boundary (binding): FSRS stability/difficulty/due are MEMORY
SCHEDULING STATE only. They are never named or exposed as proficiency,
mastery, ability, validated acquisition, learning gain, or any
``mastery_score``/``proficiency_score``. The scheduler state is persisted
outside LearningItem v1 (whose no-FSRS contract is preserved), keyed by the
stable LearningItem identity.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import utc_now


# ---------------------------------------------------------------------------
# Ordered rating space (qualified FSRS-library equivalent)
# ---------------------------------------------------------------------------


class Rating(StrEnum):
    """Ordered review rating space; ordinals match py-fsrs ``Rating``."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


RATING_ORDINALS: dict[Rating, int] = {
    Rating.AGAIN: 1,
    Rating.HARD: 2,
    Rating.GOOD: 3,
    Rating.EASY: 4,
}


# ---------------------------------------------------------------------------
# Fixed limitation / boundary statements
# ---------------------------------------------------------------------------


PRACTICE_ACTIVITY_LIMITATION = (
    "Practice completion is activity only; it does not establish mastery, "
    "proficiency, ability, or learning gain, and it does not imply authentic "
    "writing transfer."
)

NO_TRANSFER_IMPLICATION = (
    "Practice success does not imply authentic transfer; authentic writing "
    "evidence is tracked separately and remains distinct from practice "
    "evidence."
)

FSRS_STATE_IS_SCHEDULING = (
    "FSRS stability/difficulty/due are memory scheduling state only; they "
    "are not proficiency, mastery, ability, validated acquisition, or "
    "learning gain."
)


# ---------------------------------------------------------------------------
# PracticeActivity (shared, distinct from LearningItem)
# ---------------------------------------------------------------------------


class PracticeActivityStatus(StrEnum):
    """Activity statuses only; completion never implies mastery."""

    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"
    NOT_ATTEMPTED = "not_attempted"
    ABANDONED = "abandoned"


class PracticeActivity(BaseModel):
    """One shared practice activity bound to ONE stable LearningItem.

    ``evidence_kind`` is always ``"practice"``: the record is practice
    evidence, distinguishable from authentic writing evidence. Evaluator /
    evaluation linkage is preserved where applicable (``evaluator``,
    ``evaluation_id``, ``evaluator_version``).
    """

    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1, max_length=100)
    learning_item_id: str = Field(min_length=1)
    activity_type: str = Field(min_length=1, max_length=100)
    source: str = "practice"
    status: PracticeActivityStatus
    occurred_at: datetime
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    evaluator: str | None = None
    evaluation_id: str | None = None
    evaluator_version: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    evidence_kind: Literal["practice"] = "practice"
    authentic_evidence_status: Literal["insufficient", "present"] = (
        "insufficient"
    )
    limitations: list[str] = Field(
        default_factory=lambda: [PRACTICE_ACTIVITY_LIMITATION]
    )


# ---------------------------------------------------------------------------
# FSRS scheduler state and identity
# ---------------------------------------------------------------------------


class SchedulerStateSnapshot(BaseModel):
    """One FSRS memory-scheduling state (py-fsrs ``Card`` fields).

    JSON-safe snapshot of due/stability/difficulty/repetition state
    (state + step) and last review: the true equivalent of the scheduler
    state required by the real library.
    """

    model_config = ConfigDict(extra="forbid")

    card_id: int | None = None
    state: Literal["learning", "review", "relearning"] | None = None
    step: int | None = Field(default=None, ge=0)
    stability: float | None = None
    difficulty: float | None = None
    due: datetime | None = None
    last_review: datetime | None = None


class SchedulingResult(BaseModel):
    """Result of one scheduler review (memory scheduling state only)."""

    model_config = ConfigDict(extra="forbid")

    next_due: datetime | None = None
    state: str | None = None
    step: int | None = None
    stability: float | None = None
    difficulty: float | None = None
    note: str = FSRS_STATE_IS_SCHEDULING


class SchedulerIdentity(BaseModel):
    """Explicit scheduler implementation/version identity for rebuildability."""

    model_config = ConfigDict(extra="forbid")

    implementation: str = Field(min_length=1)
    library_version: str = Field(min_length=1)
    algorithm: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class SchedulerStateRecord(BaseModel):
    """One persisted scheduler-state row (durable per LearningItem)."""

    model_config = ConfigDict(extra="forbid")

    learning_item_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    identity: SchedulerIdentity
    state: SchedulerStateSnapshot
    rating_rule_version: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)
    last_review_event_id: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# ReviewEvent (durable; separate rating channels)
# ---------------------------------------------------------------------------


class ReviewEvent(BaseModel):
    """One durable review event.

    The three rating channels are separate fields and are never collapsed:
    ``system_provisional_rating`` (system evaluator), ``learner_self_rating``
    (learner), ``final_scheduler_rating`` (the rating actually fed to the
    FSRS scheduler, resolved by the versioned rating rule). The prior and
    resulting scheduler states, scheduler identity, scheduler parameters,
    and rating-rule version are stored so historical scheduling behavior can
    be reconstructed deterministically.
    """

    model_config = ConfigDict(extra="forbid")

    review_event_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1, max_length=100)
    learning_item_id: str = Field(min_length=1)
    practice_activity_id: str | None = None
    reviewed_at: datetime
    system_provisional_rating: Rating
    learner_self_rating: Rating | None = None
    final_scheduler_rating: Rating
    rating_rule_version: str = Field(min_length=1)
    scheduler_implementation: str = Field(min_length=1)
    scheduler_version: str = Field(min_length=1)
    scheduler_parameters: dict[str, Any] = Field(default_factory=dict)
    state_before: SchedulerStateSnapshot = Field(
        default_factory=SchedulerStateSnapshot
    )
    state_after: SchedulerStateSnapshot = Field(
        default_factory=SchedulerStateSnapshot
    )
    scheduling_result: SchedulingResult = Field(
        default_factory=SchedulingResult
    )
    authentic_evidence_status: Literal["insufficient", "present"] = (
        "insufficient"
    )
    provenance: dict[str, Any] = Field(default_factory=dict)
    no_transfer_implication: str = NO_TRANSFER_IMPLICATION
    limitations: list[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=utc_now)


__all__ = [
    "FSRS_STATE_IS_SCHEDULING",
    "NO_TRANSFER_IMPLICATION",
    "PRACTICE_ACTIVITY_LIMITATION",
    "RATING_ORDINALS",
    "Rating",
    "ReviewEvent",
    "PracticeActivity",
    "PracticeActivityStatus",
    "SchedulerIdentity",
    "SchedulerStateRecord",
    "SchedulerStateSnapshot",
    "SchedulingResult",
]
