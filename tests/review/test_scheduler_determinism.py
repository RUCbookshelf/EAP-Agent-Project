"""Deterministic FSRS vectors through the REAL py-fsrs scheduler adapter.

Expected values below were recorded from the pinned real library
(``fsrs==6.3.2``, fuzzing off) on 2026-08-11; identical vectors must
reproduce them exactly. This is the deterministic-vector evidence for the
Wave-3 WU1 mandatory contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.review.models import Rating
from app.review.scheduler import FSRSSchedulerAdapter


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def adapter() -> FSRSSchedulerAdapter:
    return FSRSSchedulerAdapter()


def _initial(adapter: FSRSSchedulerAdapter):
    return adapter.new_state(card_id=1, due=T0)


def test_first_review_good_vector_is_exact(adapter):
    state, result = adapter.review(_initial(adapter), Rating.GOOD, T0)
    assert state.state == "learning"
    assert state.step == 1
    assert state.stability == 2.3065
    assert state.difficulty == 2.118103970459016
    assert state.due == datetime(2026, 1, 1, 8, 10, 0, tzinfo=timezone.utc)
    assert state.last_review == T0
    assert result.next_due == state.due


def test_second_review_vector_is_exact(adapter):
    first_state, _ = adapter.review(_initial(adapter), Rating.GOOD, T0)
    second_state, _ = adapter.review(first_state, Rating.GOOD, first_state.due)
    assert second_state.state == "review"
    assert second_state.step is None
    assert second_state.stability == 2.3065
    assert second_state.difficulty == 2.111214235785395
    assert second_state.due == datetime(2026, 1, 3, 8, 10, 0, tzinfo=timezone.utc)
    assert second_state.last_review == first_state.due


def test_again_vector_moves_to_relearning(adapter):
    first_state, _ = adapter.review(_initial(adapter), Rating.GOOD, T0)
    second_state, _ = adapter.review(first_state, Rating.GOOD, first_state.due)
    again_state, _ = adapter.review(
        second_state, Rating.AGAIN, second_state.due
    )
    assert again_state.state == "relearning"
    assert again_state.step == 0
    assert again_state.difficulty > 7.0
    assert again_state.stability < 1.0


def test_rating_ordering_is_preserved_for_first_reviews(adapter):
    dues = {}
    for rating in (Rating.AGAIN, Rating.HARD, Rating.GOOD, Rating.EASY):
        _, result = adapter.review(_initial(adapter), rating, T0)
        dues[rating] = result.next_due
    assert dues[Rating.AGAIN] < dues[Rating.HARD] < dues[Rating.GOOD] < dues[Rating.EASY]
    # Easy promotes to Review state immediately on a first review.
    easy_state, _ = adapter.review(_initial(adapter), Rating.EASY, T0)
    assert easy_state.state == "review"


def test_vectors_are_deterministic_across_repeats(adapter):
    first = adapter.review(_initial(adapter), Rating.GOOD, T0)
    second = adapter.review(_initial(adapter), Rating.GOOD, T0)
    assert first == second
    for _ in range(3):
        again = adapter.review(_initial(adapter), Rating.GOOD, T0)
        assert again == first


def test_scheduler_identity_is_explicit(adapter):
    identity = adapter.identity()
    assert identity.implementation == "py-fsrs"
    assert identity.library_version == "6.3.2"
    assert identity.algorithm == "FSRS"
    assert identity.parameters["enable_fuzzing"] is False
    assert identity.parameters["desired_retention"] == 0.9
    assert identity.parameters["learning_steps"] == [60, 600]
    assert identity.parameters["relearning_steps"] == [600]
    assert len(identity.parameters["parameters"]) == 21


def test_fuzzing_is_rejected(adapter):
    with pytest.raises(ValueError):
        FSRSSchedulerAdapter(enable_fuzzing=True)


def test_snapshot_round_trip_through_real_card(adapter):
    state = _initial(adapter)
    card = adapter.to_card(state)
    rebuilt = adapter.from_card(card)
    assert rebuilt == state
