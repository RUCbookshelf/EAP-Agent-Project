"""ReviewService evidence for Wave-3 WU1 cases A-H through the REAL
shared application composition (Database -> repositories -> service ->
py-fsrs scheduler) on isolated test databases."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.database import Database
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review.models import (
    Rating,
    PracticeActivity,
    PracticeActivityStatus,
)
from app.review.rating_policy import RATING_RULE_VERSION
from app.review.scheduler import FSRSSchedulerAdapter
from app.review.service import ReviewError, ReviewService


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def stack(tmp_path):
    database = Database(tmp_path / "service.db")
    database.initialize()
    wave2 = SQLiteWave2Repository(database._connection_manager)
    service = ReviewService(
        database._review_repository,
        FSRSSchedulerAdapter(),
        learning_item_reader=wave2,
    )
    return database, wave2, service


def _learning_item(wave2, learning_item_id: str = "LI000001") -> LearningItem:
    return wave2.save_learning_item(
        LearningItem(
            learning_item_id=learning_item_id,
            student_id="S1",
            category="grammar",
            originating_evidence={"source": "priority_plan", "kind": "l2"},
        )
    )


def _activity(**overrides) -> PracticeActivity:
    values = dict(
        activity_id="PA-PENDING",
        student_id="S1",
        learning_item_id="LI000001",
        activity_type="blank_fill",
        status=PracticeActivityStatus.COMPLETED,
        occurred_at=T0,
    )
    values.update(overrides)
    return PracticeActivity(**values)


def test_case_a_initial_review_creates_durable_scheduler_state(stack):
    database, wave2, service = stack
    _learning_item(wave2)
    event = service.record_review(
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
    )
    assert event.state_after.stability is not None
    assert event.scheduling_result.next_due is not None
    state, identity = service.get_schedule("LI000001")
    assert state is not None
    assert identity is not None
    assert state.due == event.scheduling_result.next_due
    assert identity.implementation == "py-fsrs"


def test_case_b_later_review_updates_state_and_next_due(stack):
    database, wave2, service = stack
    _learning_item(wave2)
    first = service.record_review(
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
    )
    second = service.record_review(
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=first.scheduling_result.next_due,
        system_provisional_rating=Rating.GOOD,
    )
    assert second.scheduling_result.next_due != first.scheduling_result.next_due
    assert second.state_before == first.state_after
    assert second.state_after.state != first.state_after.state or (
        second.state_after.due != first.state_after.due
    )
    state, _ = service.get_schedule("LI000001")
    assert state is not None
    assert state.due == second.scheduling_result.next_due
    assert len(service.list_review_events("LI000001")) == 2


def test_case_c_rating_channels_persist_separately(stack):
    database, wave2, service = stack
    _learning_item(wave2)
    event = service.record_review(
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        learner_self_rating=Rating.HARD,
    )
    assert event.system_provisional_rating == Rating.GOOD
    assert event.learner_self_rating == Rating.HARD
    assert event.final_scheduler_rating == Rating.HARD
    reloaded = service.list_review_events("LI000001")[0]
    assert reloaded.system_provisional_rating == Rating.GOOD
    assert reloaded.learner_self_rating == Rating.HARD
    assert reloaded.final_scheduler_rating == Rating.HARD
    # Raw columns are distinct in SQLite too (no collapse).
    row = database._connection_manager.connect().execute(
        "SELECT system_provisional_rating, learner_self_rating,"
        " final_scheduler_rating FROM review_events"
    ).fetchone()
    assert tuple(row) == ("good", "hard", "hard")


def test_case_d_version_and_provenance_enable_reconstruction(stack):
    database, wave2, service = stack
    _learning_item(wave2)
    activity = service.record_practice_activity(
        _activity(activity_type="blank_fill")
    )
    event = service.record_review(
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        learner_self_rating=Rating.HARD,
        practice_activity_id=activity.activity_id,
        provenance={"source": "test", "round": 1},
    )
    assert event.rating_rule_version == RATING_RULE_VERSION
    assert event.scheduler_implementation == "py-fsrs"
    assert event.scheduler_version == "6.3.2"
    assert event.scheduler_parameters["enable_fuzzing"] is False
    assert event.practice_activity_id == activity.activity_id
    # Deterministic reconstruction: replay the real scheduler on the stored
    # inputs and require an exact match with the stored resulting state.
    scheduler = FSRSSchedulerAdapter()
    rebuilt, _ = scheduler.review(
        event.state_before, event.final_scheduler_rating, event.reviewed_at
    )
    assert rebuilt == event.state_after
    # The state row also carries the identity and rating-rule version.
    _, identity = service.get_schedule("LI000001")
    assert identity is not None
    assert identity.library_version == "6.3.2"
    assert identity.parameters["learning_steps"] == [60, 600]


def test_case_f_many_activities_and_events_one_learning_item(stack):
    database, wave2, service = stack
    _learning_item(wave2)
    for index in range(3):
        service.record_practice_activity(
            _activity(
                activity_id=f"PA-PENDING",
                activity_type=f"exercise-{index}",
                occurred_at=T0,
            )
        )
    due = T0
    for _ in range(4):
        event = service.record_review(
            student_id="S1",
            learning_item_id="LI000001",
            reviewed_at=due,
            system_provisional_rating=Rating.GOOD,
        )
        due = event.scheduling_result.next_due
    activities = service.list_practice_activities("LI000001")
    assert len(activities) == 3
    events = service.list_review_events("LI000001")
    assert len(events) == 4
    for item in activities + events:  # type: ignore[operator]
        assert item.learning_item_id == "LI000001"
    state, _ = service.get_schedule("LI000001")
    assert state is not None


def test_case_g_practice_and_authentic_evidence_stay_separate(stack):
    database, wave2, service = stack
    _learning_item(wave2)
    practice = service.record_practice_activity(
        _activity(activity_type="blank_fill")
    )
    assert practice.evidence_kind == "practice"
    assert practice.authentic_evidence_status == "insufficient"
    event = service.record_review(
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        practice_activity_id=practice.activity_id,
        authentic_evidence_status="insufficient",
        provenance={"evidence_refs": [
            {"kind": "practice", "ref": practice.activity_id},
        ]},
    )
    assert event.authentic_evidence_status == "insufficient"
    assert "does not imply authentic transfer" in event.no_transfer_implication
    # An authentic-evidence-present review is recorded as a distinct status
    # on the SAME learning item without merging the evidence kinds.
    authentic = service.record_review(
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        authentic_evidence_status="present",
        provenance={"evidence_refs": [
            {"kind": "authentic_writing", "ref": "submission:42"},
        ]},
    )
    assert authentic.authentic_evidence_status == "present"
    assert practice.evidence_kind == "practice"
    reloaded = service.list_review_events("LI000001")
    assert {event.authentic_evidence_status for event in reloaded} == {
        "insufficient", "present",
    }


def test_case_h_invalid_inputs_are_rejected_not_coerced(stack):
    database, wave2, service = stack
    _learning_item(wave2)
    with pytest.raises(ReviewError) as missing:
        service.record_review(
            student_id="S1",
            learning_item_id="LI000999",
            reviewed_at=T0,
            system_provisional_rating=Rating.GOOD,
        )
    assert missing.value.kind == "learning_item_not_found"
    with pytest.raises(ReviewError) as bad_status:
        service.record_review(
            student_id="S1",
            learning_item_id="LI000001",
            reviewed_at=T0,
            system_provisional_rating=Rating.GOOD,
            authentic_evidence_status="proven",  # type: ignore[arg-type]
        )
    assert bad_status.value.kind == "invalid_authentic_evidence_status"
    with pytest.raises(ValueError):
        service.record_review(
            student_id="S1",
            learning_item_id="LI000001",
            reviewed_at=T0,
            system_provisional_rating="excellent",  # type: ignore[arg-type]
        )
    # Nothing was silently coerced or written.
    assert service.list_review_events("LI000001") == []
    assert service.get_schedule("LI000001") == (None, None)


def test_practice_activity_requires_existing_learning_item(stack):
    database, wave2, service = stack
    with pytest.raises(ReviewError) as missing:
        service.record_practice_activity(_activity())
    assert missing.value.kind == "learning_item_not_found"
