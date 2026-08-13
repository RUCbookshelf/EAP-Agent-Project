"""Contract and semantic-boundary tests for the Review/Scheduling models."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.review.models import (
    FSRS_STATE_IS_SCHEDULING,
    NO_TRANSFER_IMPLICATION,
    PRACTICE_ACTIVITY_LIMITATION,
    Rating,
    ReviewEvent,
    PracticeActivity,
    PracticeActivityStatus,
    SchedulerStateSnapshot,
    SchedulingResult,
)


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


def _activity(**overrides) -> PracticeActivity:
    values = dict(
        activity_id="PA000001",
        student_id="S1",
        learning_item_id="LI000001",
        activity_type="blank_fill",
        status=PracticeActivityStatus.COMPLETED,
        occurred_at=T0,
    )
    values.update(overrides)
    return PracticeActivity(**values)


def _event(**overrides) -> ReviewEvent:
    values = dict(
        review_event_id="RE000001",
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        learner_self_rating=Rating.HARD,
        final_scheduler_rating=Rating.HARD,
        rating_rule_version="rating-rule-v1.0.0",
        scheduler_implementation="py-fsrs",
        scheduler_version="6.3.2",
        state_before=SchedulerStateSnapshot(card_id=1, due=T0),
        state_after=SchedulerStateSnapshot(
            card_id=1, state="learning", step=1, due=T0,
        ),
        scheduling_result=SchedulingResult(next_due=T0),
    )
    values.update(overrides)
    return ReviewEvent(**values)


def test_practice_activity_is_distinct_from_learning_item():
    activity = _activity()
    assert activity.activity_id == "PA000001"
    assert activity.learning_item_id == "LI000001"
    assert activity.evidence_kind == "practice"
    assert activity.authentic_evidence_status == "insufficient"
    assert PRACTICE_ACTIVITY_LIMITATION in activity.limitations
    # Evaluator/evaluation linkage where applicable.
    linked = _activity(
        evaluator="system-v1",
        evaluation_id="EV000001",
        evaluator_version="evaluator-v0.1.0",
    )
    assert linked.evaluator == "system-v1"
    assert linked.evaluation_id == "EV000001"
    assert linked.evaluator_version == "evaluator-v0.1.0"


def test_practice_activity_rejects_non_practice_evidence_kind():
    with pytest.raises(ValidationError):
        _activity(evidence_kind="authentic_writing")  # type: ignore[arg-type]


def test_review_event_keeps_rating_channels_separate():
    event = _event()
    assert event.system_provisional_rating == Rating.GOOD
    assert event.learner_self_rating == Rating.HARD
    assert event.final_scheduler_rating == Rating.HARD
    assert event.rating_rule_version == "rating-rule-v1.0.0"
    assert NO_TRANSFER_IMPLICATION == event.no_transfer_implication


def test_review_event_json_round_trip():
    event = _event()
    payload = event.model_dump(mode="json")
    rebuilt = ReviewEvent.model_validate(json.loads(json.dumps(payload)))
    assert rebuilt == event


def test_practice_activity_json_round_trip():
    activity = _activity()
    rebuilt = PracticeActivity.model_validate(
        json.loads(json.dumps(activity.model_dump(mode="json")))
    )
    assert rebuilt == activity


def test_invalid_ratings_are_rejected_not_coerced():
    with pytest.raises(ValidationError):
        _event(system_provisional_rating="excellent")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        _event(final_scheduler_rating=Rating.GOOD, learner_self_rating="fine")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Rating("not-a-rating")


def test_invalid_scheduler_state_is_rejected():
    with pytest.raises(ValidationError):
        SchedulerStateSnapshot(state="mastered")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        SchedulerStateSnapshot(step=-3)


def test_scheduling_result_carries_scheduling_only_note():
    result = SchedulingResult(next_due=T0)
    assert result.note == FSRS_STATE_IS_SCHEDULING


def test_unknown_fields_are_forbidden():
    with pytest.raises(ValidationError):
        _event(mastery_score=0.9)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        _activity(proficiency_score=0.9)  # type: ignore[call-arg]


def test_scheduler_state_snapshot_has_only_scheduling_fields():
    fields = set(SchedulerStateSnapshot.model_fields)
    assert fields == {
        "card_id", "state", "step", "stability", "difficulty", "due",
        "last_review",
    }


def test_review_event_cannot_carry_inference_recommendation_outcome():
    """Case G: four-way evidence-semantics distinction asserted directly.

    ReviewEvent models OBSERVED review evidence only. No field may carry
    inference, recommendation, or outcome semantics, and any such payload
    field is rejected by ``extra="forbid"`` at the model boundary.
    """
    semantic_names = {
        "inference",
        "inferred_ability",
        "inferred_mastery",
        "recommendation",
        "recommended_activity",
        "recommended_next_step",
        "outcome",
        "learning_outcome",
        "proficiency_inference",
    }
    fields = set(ReviewEvent.model_fields)
    assert not (fields & semantic_names), (
        f"ReviewEvent carries non-observed semantics: {fields & semantic_names}"
    )
    for name in ("inference", "recommendation", "outcome"):
        with pytest.raises(ValidationError):
            _event(**{name: "x"})  # type: ignore[call-arg]


def test_practice_activity_cannot_carry_inference_recommendation_outcome():
    """Case G: PracticeActivity models practice evidence only; no inference /
    recommendation / outcome semantics may be attached."""
    semantic_names = {
        "inference",
        "inferred_ability",
        "recommendation",
        "recommended_activity",
        "outcome",
        "learning_outcome",
    }
    fields = set(PracticeActivity.model_fields)
    assert not (fields & semantic_names), (
        "PracticeActivity carries non-observed semantics: "
        f"{fields & semantic_names}"
    )
    for name in ("inference", "recommendation", "outcome"):
        with pytest.raises(ValidationError):
            _activity(**{name: "x"})  # type: ignore[call-arg]


def test_malformed_provenance_is_rejected_at_model_boundary():
    """Case H: provenance must be an object; list/string payloads are
    rejected by the contracts before any persistence layer is reached."""
    for overrides in (
        {"provenance": ["malformed"]},
        {"provenance": "raw-string"},
        {"provenance": 7},
    ):
        with pytest.raises(ValidationError):
            _event(**overrides)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            _activity(**overrides)  # type: ignore[arg-type]
