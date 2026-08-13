"""Repository / scheduler protocols for the Review / Scheduling Foundation.

Core services depend on these protocols, never on ``sqlite3.connect``
directly; persistence stays in infrastructure/repository modules (one
application, one SQLite database, one composition root).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from .models import (
    Rating,
    ReviewEvent,
    PracticeActivity,
    SchedulerIdentity,
    SchedulerStateSnapshot,
    SchedulingResult,
)


class SchedulerStateRow(Protocol):
    """Persisted scheduler-state row contract (durable per LearningItem)."""

    learning_item_id: str
    student_id: str
    identity: SchedulerIdentity
    state: SchedulerStateSnapshot
    rating_rule_version: str
    updated_at: str
    last_review_event_id: str


class ReviewRepositoryConflictError(Exception):
    """Repository-level append-only conflict (durable evidence tables).

    Raised by the infrastructure repository when a client-supplied
    ``practice_activity_id`` or ``review_event_id`` already exists: durable
    review evidence must never be silently replaced. The service translates
    this signal into the stable ``ReviewError`` path with the same kind.
    """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


class ReviewRepositoryProtocol(Protocol):
    """Persistence protocol for practice activities, review events, states."""

    def record_review_event(
        self,
        event: ReviewEvent,
        state_row: dict[str, object],
    ) -> ReviewEvent: ...

    def save_practice_activity(
        self, activity: PracticeActivity
    ) -> PracticeActivity: ...

    def get_practice_activity(
        self, activity_id: str
    ) -> PracticeActivity | None: ...

    def list_practice_activities(
        self, learning_item_id: str
    ) -> list[PracticeActivity]: ...

    def get_review_event(
        self, review_event_id: str
    ) -> ReviewEvent | None: ...

    def list_review_events(
        self, learning_item_id: str
    ) -> list[ReviewEvent]: ...

    def get_scheduler_state(
        self, learning_item_id: str
    ) -> SchedulerStateRow | None: ...


class LearningItemReaderProtocol(Protocol):
    """Reader for the durable LearningItem (Wave-2 repository protocol)."""

    def get_learning_item(self, learning_item_id: str) -> Any | None: ...


@runtime_checkable
class ReviewEvidenceLookupProtocol(Protocol):
    """Learner-scoped lookup over shared review-family evidence records.

    Mechanical shared-persistence boundary only: ownership resolution and
    record lookup for practice activities (``PA*``) and review events
    (``RE*``). It carries no acknowledgement wording, consent policy,
    admission semantics, or Journey behavior; downstream consumers (for
    example the LEARNER acknowledgement evidence port) own those rules and
    qualify the returned shared records themselves.
    """

    def owner_of(self, source_id: str) -> str | None: ...

    def get_record(self, learner_id: str, source_id: str) -> Any | None: ...


class SchedulerProtocol(Protocol):
    """Deterministic FSRS scheduler surface used by the review service."""

    def identity(self) -> SchedulerIdentity: ...

    def new_state(
        self,
        *,
        card_id: int | None = None,
        due: datetime | None = None,
    ) -> SchedulerStateSnapshot: ...

    def review(
        self,
        state: SchedulerStateSnapshot,
        rating: Rating,
        reviewed_at: datetime,
    ) -> tuple[SchedulerStateSnapshot, SchedulingResult]: ...


__all__ = [
    "LearningItemReaderProtocol",
    "ReviewRepositoryConflictError",
    "ReviewRepositoryProtocol",
    "ReviewEvidenceLookupProtocol",
    "SchedulerProtocol",
    "SchedulerStateRow",
]
