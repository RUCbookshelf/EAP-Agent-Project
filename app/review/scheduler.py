"""Real FSRS scheduler adapter (CORE, Wave-3 WU1).

Wraps the actual qualified FSRS implementation shipped by the
open-spaced-repetition project (the ``fsrs`` / py-fsrs library, pinned in
``pyproject.toml`` as ``fsrs==6.3.2``) and uses its REAL semantics:
``Scheduler.review_card(card, rating, review_datetime) -> (Card, ReviewLog)``.

Determinism: the scheduler is constructed with ``enable_fuzzing=False`` so
identical (state, rating, review_datetime) vectors produce identical
results. Fuzzing-off is part of the recorded scheduler identity.

Semantic boundary: the returned state is strictly MEMORY SCHEDULING STATE
(due/stability/difficulty/state/step/last review) and is never exposed as
proficiency, mastery, ability, validated acquisition, or learning gain.
"""

from __future__ import annotations

from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from fsrs import Card, Rating as FSRsRating, Scheduler, State

from .models import (
    FSRS_STATE_IS_SCHEDULING,
    Rating,
    SchedulerIdentity,
    SchedulerStateSnapshot,
    SchedulingResult,
)


SCHEDULER_IMPLEMENTATION: str = "py-fsrs"
SCHEDULER_ALGORITHM: str = "FSRS"


def _library_version() -> str:
    try:
        return version("fsrs")
    except PackageNotFoundError:  # pragma: no cover - packaging fallback
        return "unknown"


_STATE_BY_NAME: dict[str, State] = {
    "learning": State.Learning,
    "review": State.Review,
    "relearning": State.Relearning,
}
_STATE_NAMES: dict[State, str] = {value: key for key, value in _STATE_BY_NAME.items()}


def _identity_parameters(scheduler: Scheduler) -> dict[str, Any]:
    """JSON-safe scheduler parameters (py-fsrs ``to_dict``), seconds-based."""
    # py-fsrs ``to_dict`` already serializes learning/relearning steps as
    # integer seconds and parameters as floats; pass through JSON-safe.
    return dict(scheduler.to_dict())


class FSRSSchedulerAdapter:
    """Deterministic adapter over the real py-fsrs ``Scheduler``."""

    def __init__(
        self,
        *,
        desired_retention: float = 0.9,
        enable_fuzzing: bool = False,
    ) -> None:
        if enable_fuzzing:
            raise ValueError(
                "FSRSSchedulerAdapter requires enable_fuzzing=False: "
                "deterministic vectors and persisted-state reconstruction "
                "require fuzzing off."
            )
        self._desired_retention = desired_retention
        self._enable_fuzzing = False
        self._scheduler = Scheduler(
            desired_retention=desired_retention,
            enable_fuzzing=False,
        )
        self._identity = SchedulerIdentity(
            implementation=SCHEDULER_IMPLEMENTATION,
            library_version=_library_version(),
            algorithm=SCHEDULER_ALGORITHM,
            parameters=_identity_parameters(self._scheduler),
        )

    # ------------------------------------------------------------------
    # identity
    # ------------------------------------------------------------------

    def identity(self) -> SchedulerIdentity:
        """Explicit scheduler implementation/version/parameters identity."""
        return self._identity

    # ------------------------------------------------------------------
    # state conversion
    # ------------------------------------------------------------------

    def new_state(
        self,
        *,
        card_id: int | None = None,
        due: datetime | None = None,
    ) -> SchedulerStateSnapshot:
        """A fresh initial FSRS state (Learning, step 0, no history)."""
        card = Card(card_id=card_id, due=due)
        return self.from_card(card)

    def to_card(self, snapshot: SchedulerStateSnapshot) -> Card:
        """Rebuild a py-fsrs ``Card`` from a persisted snapshot."""
        return Card(
            card_id=snapshot.card_id,
            state=_STATE_BY_NAME[snapshot.state or "learning"],
            step=snapshot.step,
            stability=snapshot.stability,
            difficulty=snapshot.difficulty,
            due=snapshot.due,
            last_review=snapshot.last_review,
        )

    def from_card(self, card: Card) -> SchedulerStateSnapshot:
        """Persist-safe snapshot of a py-fsrs ``Card``."""
        return SchedulerStateSnapshot(
            card_id=card.card_id,
            state=_STATE_NAMES[card.state],
            step=card.step,
            stability=card.stability,
            difficulty=card.difficulty,
            due=card.due,
            last_review=card.last_review,
        )

    # ------------------------------------------------------------------
    # review
    # ------------------------------------------------------------------

    def review(
        self,
        state: SchedulerStateSnapshot,
        rating: Rating,
        reviewed_at: datetime,
    ) -> tuple[SchedulerStateSnapshot, SchedulingResult]:
        """Run one review through the real FSRS scheduler.

        Returns (new state, scheduling result). Deterministic for identical
        (state, rating, reviewed_at) vectors because fuzzing is off.
        """
        fsrs_rating = {
            Rating.AGAIN: FSRsRating.Again,
            Rating.HARD: FSRsRating.Hard,
            Rating.GOOD: FSRsRating.Good,
            Rating.EASY: FSRsRating.Easy,
        }[rating]
        new_card, _log = self._scheduler.review_card(
            self.to_card(state),
            fsrs_rating,
            review_datetime=reviewed_at,
        )
        new_state = self.from_card(new_card)
        return new_state, SchedulingResult(
            next_due=new_card.due,
            state=_STATE_NAMES[new_card.state],
            step=new_card.step,
            stability=new_card.stability,
            difficulty=new_card.difficulty,
            note=FSRS_STATE_IS_SCHEDULING,
        )


__all__ = [
    "FSRSSchedulerAdapter",
    "SCHEDULER_ALGORITHM",
    "SCHEDULER_IMPLEMENTATION",
]
