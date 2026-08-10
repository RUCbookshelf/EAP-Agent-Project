"""Wave-2 Goal A repository round-trip tests (additive wave2 repository).

Exercises the additive ``SQLiteWave2Repository`` over the migration-14 table
families: writing_tasks, submission_revisions (revision ancestry links with
task-context/analysis/feedback links), learning_observations, and
learning_items.
"""

from __future__ import annotations

from app.infrastructure.sqlite import SQLiteConnectionManager
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    LearningObservation,
    SQLiteWave2Repository,
    SubmissionRevisionLink,
    WritingTask,
)


def _repository(tmp_path) -> SQLiteWave2Repository:
    return SQLiteWave2Repository(SQLiteConnectionManager(tmp_path / "wave2-repo.db"))


def _initialize(tmp_path) -> SQLiteWave2Repository:
    from app.database import Database

    repository = Database(tmp_path / "wave2-repo.db")
    repository.initialize()
    with repository.connect() as connection:
        connection.execute(
            "INSERT INTO students(student_id, created_at, is_synthetic)"
            " VALUES ('S1', '2026-01-01T00:00:00+00:00', 0)"
        )
    return _repository(tmp_path)


def _seed_submission_links(tmp_path) -> None:
    """Seed student/essays/revision group/analysis run/feedback record rows."""
    from app.database import Database

    repository = Database(tmp_path / "wave2-repo.db")
    repository.initialize()
    with repository.connect() as connection:
        connection.execute(
            "INSERT INTO students(student_id, created_at, is_synthetic)"
            " VALUES ('S1', '2026-01-01T00:00:00+00:00', 0)"
        )
        connection.execute(
            "INSERT INTO essays(student_id, writing_prompt, genre, draft_stage,"
            " timed, tool_use, essay_text, submitted_at)"
            " VALUES ('S1', 'Prompt A', 'argumentative essay', 'first draft',"
            " 0, 'none', 'Text one.', '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO essays(student_id, writing_prompt, genre, draft_stage,"
            " timed, tool_use, essay_text, submitted_at)"
            " VALUES ('S1', 'Prompt A', 'argumentative essay', 'revised draft',"
            " 0, 'none', 'Text two.', '2026-01-02T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO revision_groups(revision_group_id, student_id,"
            " writing_prompt, genre, root_submission_id, created_at,"
            " updated_at, metadata_consistency_json, limitations_json)"
            " VALUES ('RG000001', 'S1', 'Prompt A', 'argumentative essay', 1,"
            " '2026-01-01T00:00:00+00:00', '2026-01-02T00:00:00+00:00',"
            " '{}', '[]')"
        )
        connection.execute(
            "INSERT INTO analysis_runs(analysis_run_id, essay_id, analyzer_id,"
            " analyzer_version, backend, parameters_json,"
            " resource_versions_json, configuration_version, limitations,"
            " analysis_duration_ms, created_at)"
            " VALUES ('AR000001', 1, 'basic', 'v1', 'basic',"
            " '{}', '{}', 'config-v0.9.0', '[]', 0.0,"
            " '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO feedback_records(essay_id, feedback_json,"
            " provider_name, model_name, success_status, prompt_version,"
            " analysis_version) VALUES (1, '{}', 'local', 'demo', 'success',"
            " 'v1', 'v1')"
        )


def test_writing_task_round_trip(tmp_path):
    repo = _initialize(tmp_path)
    saved = repo.save_writing_task(
        WritingTask(
            student_id="S1",
            writing_prompt="Prompt A",
            metadata={"reference_group": "WECCL"},
        )
    )
    assert saved.task_id is not None
    assert saved.genre == "argumentative essay"
    assert saved.created_at is not None
    fetched = repo.get_writing_task(saved.task_id)
    assert fetched is not None
    assert fetched.student_id == "S1"
    assert fetched.writing_prompt == "Prompt A"
    assert fetched.metadata == {"reference_group": "WECCL"}
    listed = repo.list_writing_tasks("S1")
    assert [task.task_id for task in listed] == [saved.task_id]
    assert repo.list_writing_tasks("NO_SUCH_STUDENT") == []
    assert repo.get_writing_task("WT999999") is None


def test_submission_revision_link_round_trip_with_links(tmp_path):
    _seed_submission_links(tmp_path)
    repo = _repository(tmp_path)
    task = repo.save_writing_task(WritingTask(student_id="S1", writing_prompt="Prompt A"))
    saved = repo.save_submission_revision(
        SubmissionRevisionLink(
            revision_group_id="RG000001",
            source_submission_id=1,
            target_submission_id=2,
            ancestry=[1, 2],
            task_id=task.task_id,
            analysis_run_id="AR000001",
            feedback_record_id=1,
            revision_sequence=2,
            limitations=["Revision links are metadata, not learning evidence."],
        )
    )
    assert saved.revision_link_id is not None
    assert saved.created_at is not None
    fetched = repo.get_submission_revision(saved.revision_link_id)
    assert fetched is not None
    assert fetched.revision_group_id == "RG000001"
    assert fetched.source_submission_id == 1
    assert fetched.target_submission_id == 2
    assert fetched.ancestry == [1, 2]
    assert fetched.task_id == task.task_id
    assert fetched.analysis_run_id == "AR000001"
    assert fetched.feedback_record_id == 1
    assert fetched.revision_sequence == 2
    assert fetched.limitations == ["Revision links are metadata, not learning evidence."]
    by_group = repo.list_submission_revisions("RG000001")
    assert [link.revision_link_id for link in by_group] == [saved.revision_link_id]
    by_target = repo.list_submission_revisions_for_submission(2)
    assert [link.revision_link_id for link in by_target] == [saved.revision_link_id]
    assert repo.get_submission_revision("SR999999") is None


def test_learning_observation_round_trip(tmp_path):
    repo = _initialize(tmp_path)
    task = repo.save_writing_task(WritingTask(student_id="S1", writing_prompt="Prompt A"))
    saved = repo.save_learning_observation(
        LearningObservation(
            student_id="S1",
            observation_type="difficulty",
            evidence_refs=["submission:1", "diagnosis:1"],
            task_id=task.task_id,
            context={"genre": "argumentative essay"},
            occurrence_count=3,
            first_observed_at="2026-01-01T00:00:00+00:00",
            last_observed_at="2026-01-03T00:00:00+00:00",
            recency="recent",
            revision_response={"uptake": "partially_addressed"},
        )
    )
    assert saved.observation_id is not None
    fetched = repo.get_learning_observation(saved.observation_id)
    assert fetched is not None
    assert fetched.student_id == "S1"
    assert fetched.observation_type == "difficulty"
    assert fetched.evidence_refs == ["submission:1", "diagnosis:1"]
    assert fetched.task_id == task.task_id
    assert fetched.context == {"genre": "argumentative essay"}
    assert fetched.occurrence_count == 3
    assert fetched.recency == "recent"
    assert fetched.revision_response == {"uptake": "partially_addressed"}
    assert repo.list_learning_observations("S1")[0].observation_id == saved.observation_id
    assert (
        repo.list_learning_observations("S1", observation_type="difficulty")[0]
        .observation_id
        == saved.observation_id
    )
    assert repo.list_learning_observations("S1", observation_type="strength") == []


def test_learning_item_round_trip_and_status_update(tmp_path):
    repo = _initialize(tmp_path)
    task = repo.save_writing_task(WritingTask(student_id="S1", writing_prompt="Prompt A"))
    saved = repo.save_learning_item(
        LearningItem(
            student_id="S1",
            originating_evidence={"submission_ids": [1]},
            feedback_reference="feedback:1",
            revision_history=[{"target_submission_id": 2}],
            task_id=task.task_id,
            context={"priority": "revision_plan"},
            status="active",
        )
    )
    assert saved.learning_item_id is not None
    assert saved.created_at is not None
    assert saved.updated_at is not None
    fetched = repo.get_learning_item(saved.learning_item_id)
    assert fetched is not None
    assert fetched.originating_evidence == {"submission_ids": [1]}
    assert fetched.feedback_reference == "feedback:1"
    assert fetched.revision_history == [{"target_submission_id": 2}]
    assert fetched.task_id == task.task_id
    assert fetched.context == {"priority": "revision_plan"}
    assert fetched.status == "active"
    assert repo.list_learning_items("S1")[0].learning_item_id == saved.learning_item_id
    assert (
        repo.list_learning_items("S1", status="active")[0].learning_item_id
        == saved.learning_item_id
    )
    assert repo.list_learning_items("S1", status="proposed") == []
    updated = repo.update_learning_item_status(
        saved.learning_item_id, "completed", "2026-01-04T00:00:00+00:00"
    )
    assert updated is not None
    assert updated.status == "completed"
    assert repo.get_learning_item(saved.learning_item_id).status == "completed"
    assert (
        repo.update_learning_item_status(
            "LI999999", "completed", "2026-01-04T00:00:00+00:00"
        )
        is None
    )
