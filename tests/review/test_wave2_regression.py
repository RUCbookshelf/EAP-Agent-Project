"""Case I: relevant Wave-2 revision, learner, and LearningItem behavior
remains operational alongside the Wave-3 Review/Scheduling Foundation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.database import Database
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    LearningObservation,
    PriorityRevisionPlan,
    RevisionObservation,
    ScaffoldEvent,
    SQLiteWave2Repository,
    WritingTask,
)
from app.review.models import Rating
from app.review.scheduler import FSRSSchedulerAdapter
from app.review.service import ReviewService


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def stack(tmp_path):
    database = Database(tmp_path / "wave2.db")
    database.initialize()
    wave2 = SQLiteWave2Repository(database._connection_manager)
    return database, wave2


def test_wave2_families_round_trip_after_review_flow(stack):
    database, wave2 = stack
    task = wave2.save_writing_task(
        WritingTask(
            task_id="WT-PENDING",
            student_id="S1",
            writing_prompt="Should cities add more parks?",
            writing_context="cet6",
            task_type="argumentative",
        )
    )
    assert task.task_id.startswith("WT")
    assert wave2.get_writing_task(task.task_id) is not None

    item = wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000001",
            student_id="S1",
            category="grammar",
            task_id=task.task_id,
        )
    )
    assert item.no_fsrs_note == (
        "no FSRS scheduling or spaced-repetition state is stored in "
        "LearningItem v1"
    )
    assert item.no_practice_note == (
        "no practice or tutor expansion is attached to LearningItem v1"
    )

    wave2.save_learning_observation(
        LearningObservation(
            observation_id="LO000001",
            student_id="S1",
            observation_type="difficulty",
            task_id=task.task_id,
            first_observed_at=T0.isoformat(),
            last_observed_at=T0.isoformat(),
        )
    )
    assert len(wave2.list_learning_observations("S1")) == 1

    wave2.save_priority_plan(
        PriorityRevisionPlan(
            plan_id="PP-PENDING",
            learner_id="S1",
            task_id=task.task_id,
            submission_id=1,
            history_state="insufficient_history",
            items=[],
        )
    )
    plans = wave2.list_priority_plans("S1")
    assert len(plans) == 1
    assert plans[0].plan_id.startswith("PP")

    wave2.save_scaffold_event(
        ScaffoldEvent(
            scaffold_event_id="SE-PENDING",
            learner_id="S1",
            learning_item_id=item.learning_item_id,
            category="grammar",
            level=3,
            default_first=True,
        )
    )
    assert len(wave2.list_scaffold_events("S1", item.learning_item_id)) == 1

    wave2.save_revision_observation(
        RevisionObservation(
            observation_id="RO000001",
            task_id=task.task_id,
            source_submission_id=1,
            target_submission_id=2,
            no_intent_inference="no intent inference is made",
        )
    )
    assert len(wave2.list_revision_observations(task.task_id)) == 1

    # Now run the review flow on the SAME learning item.
    service = ReviewService(
        database._review_repository,
        FSRSSchedulerAdapter(),
        learning_item_reader=wave2,
    )
    event = service.record_review(
        student_id="S1",
        learning_item_id=item.learning_item_id,
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
    )
    assert event.learning_item_id == item.learning_item_id

    # Wave-2 reads still behave identically afterwards.
    reloaded = wave2.get_learning_item(item.learning_item_id)
    assert reloaded is not None
    assert reloaded.category == "grammar"
    assert reloaded.no_fsrs_note == item.no_fsrs_note
    assert len(wave2.list_learning_observations("S1")) == 1


def test_learning_item_schema_has_no_fsrs_columns(stack):
    database, _wave2 = stack
    columns = {
        row["name"]
        for row in database._connection_manager.connect().execute(
            "PRAGMA table_info(learning_items)"
        ).fetchall()
    }
    assert "stability" not in columns
    assert "difficulty" not in columns
    assert "due" not in columns
    assert "no_fsrs_note" in columns
