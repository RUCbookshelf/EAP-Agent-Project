"""Review / Scheduling Foundation application service (CORE, Wave-3 WU1).

``ReviewService`` owns the shared platform workflow only:

1. Practice evidence is recorded as a ``PracticeActivity`` bound to ONE
   durable ``LearningItem`` (never per generated question).
2. A review resolves the final scheduler rating through the versioned
   rating rule (channels preserved separately), runs the REAL FSRS
   scheduler on the durable LearningItem state, and persists the
   ``ReviewEvent`` plus the resulting scheduler state atomically.

The service does not own Practice pedagogy, Tutor behavior, or UX.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Literal

from .models import (
    Rating,
    ReviewEvent,
    PracticeActivity,
    SchedulerIdentity,
    SchedulerStateSnapshot,
)
from .protocols import (
    LearningItemReaderProtocol,
    ReviewRepositoryConflictError,
    ReviewRepositoryProtocol,
    SchedulerProtocol,
    SchedulerStateRow,
)
from .rating_policy import RATING_RULE_VERSION, resolve_final_rating


def _stable_card_id(learning_item_id: str) -> int:
    """Deterministic, stable py-fsrs card id derived from the LearningItem."""
    digest = hashlib.sha256(learning_item_id.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def _coerce_rating(value: Rating | str, *, name: str) -> Rating:
    """Fail-closed rating validation: invalid values are rejected, never
    coerced or silently defaulted."""
    if isinstance(value, Rating):
        return value
    try:
        return Rating(str(value))
    except ValueError as exc:
        raise ValueError(
            f"invalid {name}: {value!r} is not in the rating space "
            "again/hard/good/easy"
        ) from exc


class ReviewError(Exception):
    """Domain error with a stable machine-readable kind."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


class ReviewService:
    """Shared review / scheduling workflow over real FSRS scheduling."""

    def __init__(
        self,
        repository: ReviewRepositoryProtocol,
        scheduler: SchedulerProtocol,
        *,
        learning_item_reader: LearningItemReaderProtocol | None = None,
        rating_rule_version: str = RATING_RULE_VERSION,
    ) -> None:
        self._repository = repository
        self._scheduler = scheduler
        self._learning_item_reader = learning_item_reader
        self._rating_rule_version = rating_rule_version

    # ------------------------------------------------------------------
    # identity
    # ------------------------------------------------------------------

    def scheduler_identity(self) -> SchedulerIdentity:
        return self._scheduler.identity()

    @property
    def rating_rule_version(self) -> str:
        return self._rating_rule_version

    # ------------------------------------------------------------------
    # learning item guard
    # ------------------------------------------------------------------

    def _require_learning_item(self, learning_item_id: str) -> Any:
        """Return the durable LearningItem or fail closed (404 signal)."""
        if self._learning_item_reader is None:
            raise ReviewError(
                "learning_item_reader_unavailable",
                "ReviewService cannot verify the LearningItem without a "
                "learning_item_reader.",
            )
        item = self._learning_item_reader.get_learning_item(learning_item_id)
        if item is None:
            raise ReviewError(
                "learning_item_not_found",
                f"No durable LearningItem exists for {learning_item_id!r}; "
                "review scheduling requires a persisted LearningItem.",
            )
        return item

    @staticmethod
    def _require_utc_datetime(value: datetime, *, name: str) -> None:
        """Fail-closed: reject naive or non-UTC timestamps before any write."""
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(
            None
        ):
            raise ReviewError(
                "invalid_reviewed_at",
                f"{name} must be timezone-aware and set to UTC, got "
                f"{value.isoformat()!r}.",
            )

    # ------------------------------------------------------------------
    # practice activities
    # ------------------------------------------------------------------

    def record_practice_activity(
        self, activity: PracticeActivity
    ) -> PracticeActivity:
        """Persist one shared practice activity for a durable LearningItem."""
        item = self._require_learning_item(activity.learning_item_id)
        if activity.student_id != item.student_id:
            raise ReviewError(
                "practice_activity_owner_mismatch",
                f"Practice activity student {activity.student_id!r} does not "
                f"match the owner {item.student_id!r} of LearningItem "
                f"{activity.learning_item_id!r}.",
            )
        try:
            return self._repository.save_practice_activity(activity)
        except ReviewRepositoryConflictError as exc:
            raise ReviewError(exc.kind, exc.message) from exc

    def list_practice_activities(
        self, learning_item_id: str
    ) -> list[PracticeActivity]:
        return self._repository.list_practice_activities(learning_item_id)

    # ------------------------------------------------------------------
    # reviews
    # ------------------------------------------------------------------

    def record_review(
        self,
        *,
        student_id: str,
        learning_item_id: str,
        reviewed_at: datetime,
        system_provisional_rating: Rating,
        learner_self_rating: Rating | None = None,
        practice_activity_id: str | None = None,
        authentic_evidence_status: Literal["insufficient", "present"] = (
            "insufficient"
        ),
        provenance: dict[str, Any] | None = None,
    ) -> ReviewEvent:
        """Record one review and advance the durable FSRS scheduler state.

        Rating channels are persisted separately; the final scheduler
        rating is resolved by the versioned conservative rule. The event and
        the resulting scheduler state are written atomically.
        """
        self._require_utc_datetime(reviewed_at, name="reviewed_at")
        if authentic_evidence_status not in ("insufficient", "present"):
            raise ReviewError(
                "invalid_authentic_evidence_status",
                f"authentic_evidence_status must be 'insufficient' or "
                f"'present', got {authentic_evidence_status!r}.",
            )
        item = self._require_learning_item(learning_item_id)
        if student_id != item.student_id:
            raise ReviewError(
                "learning_item_owner_mismatch",
                f"Review event student {student_id!r} does not match the "
                f"owner {item.student_id!r} of LearningItem "
                f"{learning_item_id!r}.",
            )
        if practice_activity_id is not None:
            activity = self._repository.get_practice_activity(
                practice_activity_id
            )
            if activity is None:
                raise ReviewError(
                    "practice_activity_not_found",
                    f"No durable PracticeActivity exists for "
                    f"{practice_activity_id!r}; a review event may only "
                    "reference an existing activity.",
                )
            if activity.student_id != student_id:
                raise ReviewError(
                    "practice_activity_owner_mismatch",
                    f"Practice activity {practice_activity_id!r} belongs to "
                    f"student {activity.student_id!r}, not {student_id!r}.",
                )
        system_rating = _coerce_rating(
            system_provisional_rating, name="system_provisional_rating"
        )
        learner_rating = (
            None
            if learner_self_rating is None
            else _coerce_rating(learner_self_rating, name="learner_self_rating")
        )

        existing = self._repository.get_scheduler_state(learning_item_id)
        if existing is not None:
            state_before = SchedulerStateSnapshot.model_validate(
                existing.state.model_dump(mode="json")
            )
        else:
            state_before = self._scheduler.new_state(
                card_id=_stable_card_id(learning_item_id),
                due=reviewed_at,
            )

        final_rating = resolve_final_rating(
            system_rating, learner_rating
        )
        identity = self._scheduler.identity()
        state_after, scheduling_result = self._scheduler.review(
            state_before, final_rating, reviewed_at
        )

        event = ReviewEvent(
            review_event_id="RE-PENDING",  # replaced by the repository
            student_id=student_id,
            learning_item_id=learning_item_id,
            practice_activity_id=practice_activity_id,
            reviewed_at=reviewed_at,
            system_provisional_rating=system_rating,
            learner_self_rating=learner_rating,
            final_scheduler_rating=final_rating,
            rating_rule_version=self._rating_rule_version,
            scheduler_implementation=identity.implementation,
            scheduler_version=identity.library_version,
            scheduler_parameters=identity.parameters,
            state_before=state_before,
            state_after=state_after,
            scheduling_result=scheduling_result,
            authentic_evidence_status=authentic_evidence_status,
            provenance=provenance or {},
        )

        state_row: dict[str, object] = {
            "learning_item_id": learning_item_id,
            "student_id": student_id,
            "identity": identity.model_dump(mode="json"),
            "state": state_after.model_dump(mode="json"),
            "rating_rule_version": self._rating_rule_version,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_review_event_id": event.review_event_id,
        }
        try:
            return self._repository.record_review_event(event, state_row)
        except ReviewRepositoryConflictError as exc:
            raise ReviewError(exc.kind, exc.message) from exc

    def get_schedule(
        self, learning_item_id: str
    ) -> tuple[SchedulerStateSnapshot | None, SchedulerIdentity | None]:
        """Current durable FSRS memory-scheduling state for the LearningItem."""
        row: SchedulerStateRow | None = self._repository.get_scheduler_state(
            learning_item_id
        )
        if row is None:
            return None, None
        return row.state, row.identity

    def list_review_events(
        self, learning_item_id: str
    ) -> list[ReviewEvent]:
        return self._repository.list_review_events(learning_item_id)


__all__ = ["ReviewError", "ReviewService", "_stable_card_id"]
