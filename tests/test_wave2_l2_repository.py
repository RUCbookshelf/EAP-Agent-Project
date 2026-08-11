"""Wave-2 Goal C -- locally-defined revision-loop repository tests.

The protocol mirrors the CORE migration-14 semantics (writing tasks,
submission revisions with ancestry/task-context/analysis/feedback links,
learning items) but is defined locally because the CORE branch files land at
integration. Both implementations (in-memory + self-contained TEST-ONLY
SQLite) must round-trip the same records.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.l2.wave2.models import (
    LearningItem,
    PriorityRevisionPlan,
    RevisionObservation,
    ScaffoldEvent,
    SubmissionVersion,
    WritingTask,
    WritingTaskMetadata,
)
from app.l2.wave2.repository import (
    InMemoryRevisionLoopRepository,
    RevisionLoopRepository,
)
from app.l2.wave2.sqlite_repository import SqliteRevisionLoopRepository


def _task(task_id: str = "WT000001", student_id: str = "L-REPO-01") -> WritingTask:
    return WritingTask(
        task_id=task_id,
        student_id=student_id,
        task_type="argumentative",
        writing_context="ielts_task2",
        writing_prompt="Take a position on studying abroad.",
        metadata=WritingTaskMetadata(purpose="persuade"),
    )


def _version(
    *, task_id: str = "WT000001", submission_id: int, version_number: int,
    revision_of: int | None = None, ancestry: list[int] | None = None,
) -> SubmissionVersion:
    return SubmissionVersion(
        task_id=task_id,
        submission_id=submission_id,
        version_number=version_number,
        revision_of_submission_id=revision_of,
        ancestry=ancestry or [submission_id],
        submitted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        task_context={
            "task_type": "argumentative",
            "writing_context": "ielts_task2",
            "writing_prompt": "Take a position on studying abroad.",
        },
        essay_text_hash="abc123",
        draft_stage="first draft" if revision_of is None else "revised draft",
        analysis_run_id=f"RUN-{submission_id}",
        feedback_record_id=submission_id * 10,
    )


def _observation(task_id: str = "WT000001", observation_id: str = "RO000001") -> RevisionObservation:
    return RevisionObservation(
        observation_id=observation_id,
        task_id=task_id,
        source_submission_id=1,
        target_submission_id=2,
        observed_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        what_changed={"inserted_tokens": 30, "deleted_tokens": 5},
        feedback_areas=[],
        new_observations=[],
        apparent_independent_corrections=[],
        no_intent_inference=(
            "Observations describe observed text changes; they do not infer "
            "the learner's intent, ability, or learning outcomes."
        ),
        limitations=[],
    )


def _plan(student_id: str = "L-REPO-01", plan_id: str = "PP000001") -> PriorityRevisionPlan:
    return PriorityRevisionPlan(
        plan_id=plan_id,
        learner_id=student_id,
        task_id="WT000001",
        submission_id=1,
        generated_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        items=[],
        history_state="insufficient_history",
        history_reasons=["no stored submissions"],
        local_observations=[],
        global_observations=[],
        historical_feedback=[],
        limitations=["Plan is based on the current submission only."],
    )


def _item(student_id: str = "L-REPO-01", item_id: str = "LI000001") -> LearningItem:
    created_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    return LearningItem(
        learning_item_id=item_id,
        student_id=student_id,
        category="essay_length",
        originating_evidence={"submission_ids": [1], "diagnosis_ids": ["D001"]},
        feedback_reference="feedback:10",
        revision_history=[{"version_number": 1, "submission_id": 1}],
        task_id="WT000001",
        task_context={"task_type": "argumentative", "writing_context": "ielts_task2"},
        status="proposed",
        created_at=created_at,
        updated_at=created_at,
    )


def _event(student_id: str = "L-REPO-01") -> ScaffoldEvent:
    return ScaffoldEvent(
        scaffold_event_id="SE000001",
        learner_id=student_id,
        category="essay_length",
        level=1,
        requested_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        default_first=True,
        limitations=[],
    )


@pytest.fixture(params=["in_memory", "sqlite"])
def repository(request, tmp_path):
    if request.param == "sqlite":
        with SqliteRevisionLoopRepository(tmp_path / "wave2_l2.db") as repo:
            yield repo
    else:
        yield InMemoryRevisionLoopRepository()


class TestWritingTasks:
    def test_round_trip(self, repository: RevisionLoopRepository) -> None:
        task = _task()
        repository.save_writing_task(task)
        assert repository.get_writing_task("WT000001") == task
        listed = repository.list_writing_tasks("L-REPO-01")
        assert [item.task_id for item in listed] == ["WT000001"]


class TestSubmissionVersions:
    def test_round_trip_with_ancestry_and_links(self, repository) -> None:
        repository.save_writing_task(_task())
        repository.save_submission_version(_version(submission_id=11, version_number=1))
        repository.save_submission_version(
            _version(
                submission_id=12, version_number=2, revision_of=11,
                ancestry=[11, 12],
            )
        )
        versions = repository.list_submission_versions("WT000001")
        assert [v.version_number for v in versions] == [1, 2]
        assert versions[1].ancestry == [11, 12]
        assert versions[1].revision_of_submission_id == 11
        assert versions[1].analysis_run_id == "RUN-12"
        assert versions[1].feedback_record_id == 120
        stored = repository.get_submission_version("WT000001", 12)
        assert stored is not None and stored.version_number == 2

    def test_prior_versions_never_overwritten(self, repository) -> None:
        repository.save_writing_task(_task())
        v1 = _version(submission_id=21, version_number=1)
        repository.save_submission_version(v1)
        v2 = _version(
            submission_id=22, version_number=2, revision_of=21,
            ancestry=[21, 22],
        )
        repository.save_submission_version(v2)
        versions = repository.list_submission_versions("WT000001")
        assert len(versions) == 2
        assert versions[0].submission_id == 21
        assert versions[0].essay_text_hash == "abc123"
        assert versions[1].submission_id == 22


class TestObservationsAndPlans:
    def test_observation_round_trip(self, repository) -> None:
        repository.save_revision_observation(_observation())
        stored = repository.list_revision_observations("WT000001")
        assert len(stored) == 1
        assert stored[0].source_submission_id == 1
        assert stored[0].no_intent_inference

    def test_priority_plan_round_trip(self, repository) -> None:
        repository.save_priority_plan(_plan())
        assert repository.get_priority_plan("PP000001") == _plan()
        assert len(repository.list_priority_plans("L-REPO-01")) == 1

    def test_scaffold_events_round_trip(self, repository) -> None:
        repository.save_scaffold_event(_event())
        events = repository.list_scaffold_events("L-REPO-01")
        assert len(events) == 1
        assert events[0].level == 1
        assert events[0].default_first is True


class TestLearningItems:
    def test_round_trip_and_status_update(self, repository) -> None:
        repository.save_learning_item(_item())
        stored = repository.get_learning_item("LI000001")
        assert stored is not None
        assert stored.status == "proposed"
        assert stored.feedback_reference == "feedback:10"
        updated = repository.update_learning_item_status(
            "LI000001", "active", datetime(2026, 8, 3, tzinfo=timezone.utc),
        )
        assert updated is not None and updated.status == "active"
        assert repository.get_learning_item("LI000001").status == "active"
        assert len(repository.list_learning_items("L-REPO-01", status="active")) == 1

    def test_status_filter(self, repository) -> None:
        repository.save_learning_item(_item(item_id="LI000002"))
        assert repository.list_learning_items("L-REPO-01", status="proposed") == [_item(item_id="LI000002")]
