"""Case B: invalid state/rating transition vectors through the REAL scheduler.

The vectors below were recorded from the pinned real library (``fsrs==6.3.2``,
``py-fsrs``, fuzzing off, adapter identity asserted in
``test_scheduler_identity_is_pinned``) on 2026-08-11; see
``docs/integration/pdw3-wu1-recovery-20260811/repairs/R3-TESTS-REVIEW-COVERAGE/
evidence/probe-real-fsrs-transitions.log``. This closes the Phase-1 Case B
gap (inventory C3): only invalid state *values* were tested at the model
boundary, never impossible state/step combinations through the real
scheduler.

Where the real library fails closed (AssertionError for scheduler-impossible
vectors: relearning step overflow, review state carrying a residual step,
review state without history), the adapter propagates that rejection and the
service aborts before any write. Tolerated vectors (learning step overflow
graduates or resets) are pinned exactly so any library change is detected.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.database import Database
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review.models import Rating, SchedulerStateSnapshot
from app.review.scheduler import FSRSSchedulerAdapter
from app.review.service import ReviewService


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 1, 5, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def adapter() -> FSRSSchedulerAdapter:
    return FSRSSchedulerAdapter()


@pytest.fixture
def stack(tmp_path):
    database = Database(tmp_path / "transitions.db")
    database.initialize()
    wave2 = SQLiteWave2Repository(database._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000001",
            student_id="S1",
            category="grammar",
        )
    )
    service = ReviewService(
        database._review_repository,
        FSRSSchedulerAdapter(),
        learning_item_reader=wave2,
    )
    return database, wave2, service


def test_scheduler_identity_is_pinned(adapter):
    """All exact vectors below are bound to this pinned identity."""
    identity = adapter.identity()
    assert identity.implementation == "py-fsrs"
    assert identity.library_version == "6.3.2"
    assert identity.algorithm == "FSRS"
    assert identity.parameters["enable_fuzzing"] is False
    assert identity.parameters["learning_steps"] == [60, 600]
    assert identity.parameters["relearning_steps"] == [600]


def test_learning_step_overflow_graduates_on_good(adapter):
    """learning step=2 exceeds learning_steps [60, 600]; real library
    graduates the card to review with an exact deterministic vector."""
    state = SchedulerStateSnapshot(card_id=1, state="learning", step=2, due=T0)
    new_state, result = adapter.review(state, Rating.GOOD, T0)
    assert new_state.state == "review"
    assert new_state.step is None
    assert new_state.stability == 2.3065
    assert new_state.difficulty == 2.118103970459016
    assert new_state.due == datetime(2026, 1, 3, 8, 0, 0, tzinfo=timezone.utc)
    assert new_state.last_review == T0
    assert result.next_due == new_state.due


def test_learning_step_overflow_again_resets_to_step_zero(adapter):
    """learning step=2 rated Again: the real library resets to learning
    step 0 with a short interval (exact recorded vector)."""
    state = SchedulerStateSnapshot(card_id=1, state="learning", step=2, due=T0)
    new_state, result = adapter.review(state, Rating.AGAIN, T0)
    assert new_state.state == "learning"
    assert new_state.step == 0
    assert new_state.stability == 0.212
    assert new_state.difficulty == 6.4133
    assert new_state.due == datetime(
        2026, 1, 1, 8, 1, 0, tzinfo=timezone.utc
    )
    assert result.next_due == new_state.due


def test_relearning_step_overflow_is_rejected_by_real_library(adapter):
    """relearning step=1 exceeds relearning_steps [600]; the real library
    fails closed (AssertionError) instead of producing a bogus schedule."""
    state = SchedulerStateSnapshot(
        card_id=1, state="relearning", step=1, due=T0
    )
    with pytest.raises(AssertionError):
        adapter.review(state, Rating.GOOD, T0)


def test_review_state_with_residual_step_is_rejected(adapter):
    """A review-state card may not carry a step; the real library rejects it."""
    state = SchedulerStateSnapshot(card_id=1, state="review", step=0, due=T0)
    with pytest.raises(AssertionError):
        adapter.review(state, Rating.GOOD, T0)


def test_review_state_without_history_is_rejected(adapter):
    """A review-state card without stability/difficulty history is
    scheduler-impossible; the real library rejects it."""
    state = SchedulerStateSnapshot(card_id=1, state="review", due=T0)
    with pytest.raises(AssertionError):
        adapter.review(state, Rating.GOOD, T0)


def test_learning_step_none_is_treated_as_step_zero(adapter):
    """step=None on a learning card behaves like step 0 (exact vector)."""
    state = SchedulerStateSnapshot(
        card_id=1, state="learning", step=None, due=T0
    )
    new_state, _ = adapter.review(state, Rating.GOOD, T0)
    assert new_state.state == "learning"
    assert new_state.step == 1
    assert new_state.stability == 2.3065
    assert new_state.difficulty == 2.118103970459016
    assert new_state.due == datetime(
        2026, 1, 1, 8, 10, 0, tzinfo=timezone.utc
    )


def test_overdue_review_vectors_are_exact(adapter):
    """Overdue reviews (review time after due) are deterministic."""
    new_state, _ = adapter.review(
        adapter.new_state(card_id=1, due=T0), Rating.GOOD, LATER
    )
    assert new_state.state == "learning"
    assert new_state.step == 1
    assert new_state.stability == 2.3065
    assert new_state.difficulty == 2.118103970459016
    assert new_state.due == datetime(
        2026, 1, 5, 8, 10, 0, tzinfo=timezone.utc
    )
    assert new_state.last_review == LATER

    # A review-state card reviewed 2 days overdue (due 2026-01-03, reviewed
    # 2026-01-05): exact recorded vector.
    first_state, _ = adapter.review(
        adapter.new_state(card_id=1, due=T0), Rating.GOOD, T0
    )
    review_state, _ = adapter.review(
        first_state, Rating.GOOD, first_state.due
    )
    assert review_state.state == "review"
    overdue_state, result = adapter.review(
        review_state, Rating.GOOD, LATER
    )
    assert overdue_state.state == "review"
    assert overdue_state.step is None
    assert overdue_state.stability == 13.835840133660218
    assert overdue_state.difficulty == 2.1043313908464483
    assert overdue_state.due == datetime(
        2026, 1, 19, 8, 0, 0, tzinfo=timezone.utc
    )
    assert overdue_state.last_review == LATER
    assert result.next_due == overdue_state.due


def test_invalid_state_and_step_values_rejected_at_model_boundary():
    """Fail-closed at the model boundary: scheduler-impossible state values
    and negative steps never reach the real library."""
    for overrides in ({"state": "mastered"}, {"state": "graduated"}):
        with pytest.raises(ValidationError):
            SchedulerStateSnapshot(card_id=1, due=T0, **overrides)
    with pytest.raises(ValidationError):
        SchedulerStateSnapshot(card_id=1, state="learning", step=-1, due=T0)


def test_impossible_persisted_state_fails_closed_with_no_write(stack):
    """A persisted scheduler-state row holding a scheduler-impossible vector
    (relearning step overflow) must fail closed through the real service:
    the review raises and NO evidence row is written."""
    database, wave2, service = stack
    service.record_review(
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
    )
    events_before = len(service.list_review_events("LI000001"))
    with database._connection_manager.connect() as connection:
        connection.execute(
            "UPDATE learning_item_scheduler_states SET state_json=?"
            " WHERE learning_item_id=?",
            (
                json.dumps(
                    {
                        "card_id": 1,
                        "state": "relearning",
                        "step": 1,
                        "due": T0.isoformat(),
                    }
                ),
                "LI000001",
            ),
        )
    with pytest.raises(AssertionError):
        service.record_review(
            student_id="S1",
            learning_item_id="LI000001",
            reviewed_at=T0,
            system_provisional_rating=Rating.GOOD,
        )
    assert len(service.list_review_events("LI000001")) == events_before
