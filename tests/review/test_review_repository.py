"""Repository persistence round trips for the Review/Scheduling Foundation.

Includes close/reopen survival (Case E) on a real SQLite file through the
real connection manager.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.database import Database
from app.infrastructure.sqlite.repositories.review import (
    SQLiteReviewEvidenceLookup,
    SQLiteReviewRepository,
)
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review.models import (
    Rating,
    ReviewEvent,
    PracticeActivity,
    PracticeActivityStatus,
    SchedulerIdentity,
    SchedulerStateSnapshot,
    SchedulingResult,
)
from app.review.scheduler import FSRSSchedulerAdapter


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


def _repository(tmp_path) -> SQLiteReviewRepository:
    database = Database(tmp_path / "review.db")
    database.initialize()
    wave2 = SQLiteWave2Repository(database._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000001",
            student_id="S1",
            category="grammar",
        )
    )
    return database._review_repository


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


def _event(review_event_id: str = "RE-PENDING", **overrides) -> ReviewEvent:
    values = dict(
        review_event_id=review_event_id,
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        learner_self_rating=Rating.HARD,
        final_scheduler_rating=Rating.HARD,
        rating_rule_version="rating-rule-v1.0.0",
        scheduler_implementation="py-fsrs",
        scheduler_version="6.3.2",
        state_before=SchedulerStateSnapshot(card_id=7, due=T0),
        state_after=SchedulerStateSnapshot(
            card_id=7, state="learning", step=1, due=T0,
        ),
        scheduling_result=SchedulingResult(next_due=T0),
    )
    values.update(overrides)
    return ReviewEvent(**values)


def _state_row(
    learning_item_id: str = "LI000001",
    review_event_id: str = "RE000001",
) -> dict[str, object]:
    identity = FSRSSchedulerAdapter().identity()
    return {
        "learning_item_id": learning_item_id,
        "student_id": "S1",
        "identity": identity.model_dump(mode="json"),
        "state": SchedulerStateSnapshot(
            card_id=7, state="review", stability=2.3065, due=T0
        ).model_dump(mode="json"),
        "rating_rule_version": "rating-rule-v1.0.0",
        "updated_at": "2026-01-01T08:00:00+00:00",
        "last_review_event_id": review_event_id,
    }


def test_practice_activity_round_trip(tmp_path):
    repository = _repository(tmp_path)
    saved = repository.save_practice_activity(_activity())
    assert saved.activity_id.startswith("PA")
    loaded = repository.get_practice_activity(saved.activity_id)
    assert loaded is not None
    assert loaded.model_dump() == saved.model_dump()


def test_practice_activity_keeps_provided_id(tmp_path):
    repository = _repository(tmp_path)
    saved = repository.save_practice_activity(
        _activity(activity_id="PA000042")
    )
    assert saved.activity_id == "PA000042"


def test_review_event_and_state_persist_atomically(tmp_path):
    repository = _repository(tmp_path)
    persisted = repository.record_review_event(
        _event(), _state_row(review_event_id="RE-PENDING")
    )
    assert persisted.review_event_id.startswith("RE")
    loaded = repository.get_review_event(persisted.review_event_id)
    assert loaded is not None
    assert loaded.model_dump() == persisted.model_dump()
    state = repository.get_scheduler_state("LI000001")
    assert state is not None
    assert state.last_review_event_id == persisted.review_event_id
    assert state.identity.library_version == "6.3.2"
    assert state.state.state == "review"


def test_list_review_events_and_activities_by_item(tmp_path):
    repository = _repository(tmp_path)
    activity = repository.save_practice_activity(_activity())
    repository.record_review_event(
        _event(review_event_id="RE000001"),
        _state_row(review_event_id="RE000001"),
    )
    repository.record_review_event(
        _event(review_event_id="RE000002", reviewed_at=T0),
        _state_row(review_event_id="RE000002"),
    )
    events = repository.list_review_events("LI000001")
    assert [event.review_event_id for event in events] == [
        "RE000001", "RE000002",
    ]
    activities = repository.list_practice_activities("LI000001")
    assert [item.activity_id for item in activities] == [activity.activity_id]
    assert repository.list_practice_activities("LI000999") == []


def test_state_and_events_survive_close_reopen(tmp_path):
    """Case E: durable state survives repository close/reopen."""
    path = tmp_path / "survive.db"
    first = Database(path)
    first.initialize()
    wave2 = SQLiteWave2Repository(first._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000001",
            student_id="S1",
            category="grammar",
        )
    )
    repository = first._review_repository
    repository.record_review_event(
        _event(), _state_row(review_event_id="RE-PENDING")
    )
    # Simulate repository close: drop every reference and reopen the file.
    del repository
    del first

    second = Database(path)
    second.initialize()
    reopened = second._review_repository
    events = reopened.list_review_events("LI000001")
    assert len(events) == 1
    state = reopened.get_scheduler_state("LI000001")
    assert state is not None
    assert state.state.state == "review"
    assert state.identity.library_version == "6.3.2"


def test_evidence_lookup_owner_and_record_round_trip(tmp_path):
    """WU2: shared evidence lookup resolves PA/RE ownership and returns
    the durable record only to its owner; unknown ids fail closed."""
    repository = _repository(tmp_path)
    activity = repository.save_practice_activity(_activity())
    event = repository.record_review_event(_event(), _state_row())
    lookup = SQLiteReviewEvidenceLookup(repository._connection_manager)

    assert lookup.owner_of(activity.activity_id) == "S1"
    assert lookup.owner_of(event.review_event_id) == "S1"

    loaded = lookup.get_record("S1", activity.activity_id)
    assert isinstance(loaded, PracticeActivity)
    assert loaded.activity_id == activity.activity_id
    assert loaded.evidence_kind == "practice"

    event_loaded = lookup.get_record("S1", event.review_event_id)
    assert isinstance(event_loaded, ReviewEvent)
    assert event_loaded.review_event_id == event.review_event_id

    assert lookup.get_record("S2", activity.activity_id) is None
    assert lookup.get_record("S1", "PA-NOPE") is None
    assert lookup.owner_of("WT000001") is None
    assert lookup.owner_of("") is None


def test_evidence_lookup_survives_close_reopen(tmp_path):
    """WU2: the shared evidence lookup stays durable across close/reopen
    of the SAME single SQLite file."""
    path = tmp_path / "lookup.db"
    first = Database(path)
    first.initialize()
    wave2 = SQLiteWave2Repository(first._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000001",
            student_id="S1",
            category="grammar",
        )
    )
    activity = first._review_repository.save_practice_activity(_activity())
    activity_id = activity.activity_id
    del first

    second = Database(path)
    second.initialize()
    lookup = SQLiteReviewEvidenceLookup(second._connection_manager)
    assert lookup.owner_of(activity_id) == "S1"
    record = lookup.get_record("S1", activity_id)
    assert record is not None
    assert record.activity_id == activity_id
