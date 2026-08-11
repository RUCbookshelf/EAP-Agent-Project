"""Wave-2 shared-repository composition tests (F-1 repair).

The ``app.api.routers.wave2`` assembly composes ONE shared
``SQLiteWave2Repository`` over the composition-root Database and exposes it
at ``app.state.wave2_repository`` so the revision/personalized/learner
sub-routers resolve the same store.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException, Request

from app.api.routers.wave2 import build_wave2_repository, get_wave2_repository
from app.config import Settings
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
    WritingTask,
)


def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wave2-composition.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )


def _request_for(app) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/wave2/revision/tasks",
            "query_string": b"",
            "headers": [],
            "app": app,
        }
    )


def _seed_student(app, student_id: str = "S1") -> None:
    """writing_tasks carries a students FK (migration-14 contract); seed the
    learner row exactly like the CORE repository tests do."""
    with app.state.repository.connect() as connection:
        connection.execute(
            "INSERT INTO students(student_id, created_at, is_synthetic)"
            " VALUES (?, '2026-01-01T00:00:00+00:00', 0)",
            (student_id,),
        )


def test_build_wave2_repository_composes_over_app_database(tmp_path):
    """The shared repository reuses the app Database's connection manager
    (one SQLite database for the whole application)."""
    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    database = app.state.repository
    _seed_student(app)
    repository = build_wave2_repository(database)

    assert isinstance(repository, SQLiteWave2Repository)
    assert repository._connection_manager is database._connection_manager

    # The composed store persists through the migration-14 tables of the
    # same database file the composition root initialized.
    saved = repository.save_writing_task(
        WritingTask(student_id="S1", writing_prompt="Prompt A")
    )
    assert saved.task_id is not None and saved.task_id.startswith("WT")
    with database.connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM writing_tasks WHERE task_id=?", (saved.task_id,)
        ).fetchone()
    assert row is not None


def test_get_wave2_repository_exposes_one_shared_instance_on_state(tmp_path):
    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    assert not hasattr(app.state, "wave2_repository")

    request = _request_for(app)
    first = get_wave2_repository(request)
    second = get_wave2_repository(request)

    assert isinstance(first, SQLiteWave2Repository)
    assert first is second, "every wave2 consumer must share ONE store instance"
    assert app.state.wave2_repository is first
    assert first._connection_manager is app.state.repository._connection_manager


def test_shared_store_makes_revision_tasks_visible_across_router_families(tmp_path):
    """A task saved through the shared store is visible to the personalized /
    learner router families: they all resolve the same store instance over
    the same database."""
    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    request = _request_for(app)

    revision_store = get_wave2_repository(request)
    _seed_student(app)
    task = revision_store.save_writing_task(
        WritingTask(
            student_id="S1",
            writing_prompt="Prompt A",
            genre="argumentative essay",
        )
    )

    personalized_store = get_wave2_repository(request)
    learner_store = get_wave2_repository(request)
    assert personalized_store is revision_store
    assert learner_store is revision_store
    assert personalized_store.get_writing_task(task.task_id).task_id == task.task_id


def test_get_wave2_repository_503_without_composition_root_database():
    from app.api.main import create_app

    app = create_app()  # production app: no state until lifespan startup
    with pytest.raises(HTTPException) as exc_info:
        get_wave2_repository(_request_for(app))
    assert exc_info.value.status_code == 503


def test_prepopulated_state_repository_is_served_as_is(tmp_path):
    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    marker = object()
    app.state.wave2_repository = marker  # type: ignore[assignment]
    request = _request_for(app)
    assert get_wave2_repository(request) is marker


# ---------------------------------------------------------------------------
# F-5 repair: real-store L2 RevisionLoopRepository contract (PDW2-WU2-INT
# INTEGRATION-GATE-RE-GATE finding F-5; repair owner CORE).
#
# The shared SQLiteWave2Repository is consumed by the mounted L2 wave-2
# routers (revision/personalized) through the L2 ``RevisionLoopRepository``
# protocol with the L2 WritingTask/LearningItem shapes (writing_context,
# classification, status, category, task_context, limitations). These tests
# exercise the REAL CORE-composed store with L2-shaped duck-typed records so
# the contract is verified against the composed SQLite implementation and
# never only against in-memory stand-ins.
# ---------------------------------------------------------------------------

L2_PROTOCOL_METHODS = [
    "save_writing_task",
    "get_writing_task",
    "list_writing_tasks",
    "save_submission_version",
    "get_submission_version",
    "list_submission_versions",
    "find_task_id_for_submission",
    "save_revision_observation",
    "list_revision_observations",
    "save_priority_plan",
    "get_priority_plan",
    "list_priority_plans",
    "save_scaffold_event",
    "list_scaffold_events",
    "save_learning_item",
    "get_learning_item",
    "list_learning_items",
    "update_learning_item_status",
]


class _TaskMetadata:
    """Duck-typed L2 ``WritingTaskMetadata`` (pydantic model_dump shape)."""

    def __init__(self, **values: object) -> None:
        self._values = dict(values)

    def model_dump(self, mode: str = "python", **_: object) -> dict:
        return dict(self._values)


class _L2WritingTask:
    """L2-shaped task: ``writing_context``; deliberately NO ``genre`` field."""

    def __init__(
        self,
        *,
        student_id: str,
        task_type: str,
        writing_context: str,
        writing_prompt: str,
        metadata: _TaskMetadata | None = None,
        classification: dict | None = None,
        status: str = "active",
        created_at=None,
        limitations: list[str] | None = None,
        task_id: str = "WT-PENDING",
    ) -> None:
        self.task_id = task_id
        self.student_id = student_id
        self.task_type = task_type
        self.writing_context = writing_context
        self.writing_prompt = writing_prompt
        self.metadata = metadata or _TaskMetadata()
        self.modality = "written"
        self.classification = classification or {}
        self.status = status
        self.created_at = created_at
        self.limitations = limitations or []


class _SubmissionVersion:
    """L2-shaped submission version (V1/V2 append-only with full linkage)."""

    def __init__(
        self,
        *,
        task_id: str,
        submission_id: int,
        version_number: int,
        revision_of_submission_id: int | None = None,
        ancestry: list[int] | None = None,
        submitted_at=None,
        task_context: dict | None = None,
        essay_text_hash: str = "abc",
        draft_stage: str = "first draft",
        analysis_run_id: str | None = None,
        analysis_version: str | None = None,
        feedback_record_id: int | None = None,
        revision_group_id: str | None = None,
        revision_snapshot_id: str | None = None,
        corpus_routing: dict | None = None,
        reanalysis_events: list[dict] | None = None,
        limitations: list[str] | None = None,
    ) -> None:
        self.task_id = task_id
        self.submission_id = submission_id
        self.version_number = version_number
        self.revision_of_submission_id = revision_of_submission_id
        self.ancestry = ancestry or []
        self.submitted_at = submitted_at
        self.task_context = task_context or {}
        self.essay_text_hash = essay_text_hash
        self.draft_stage = draft_stage
        self.analysis_run_id = analysis_run_id
        self.analysis_version = analysis_version
        self.feedback_record_id = feedback_record_id
        self.revision_group_id = revision_group_id
        self.revision_snapshot_id = revision_snapshot_id
        self.corpus_routing = corpus_routing
        self.reanalysis_events = reanalysis_events or []
        self.limitations = limitations or []


class _RevisionObservation:
    """L2-shaped bounded revision observation."""

    def __init__(
        self,
        *,
        observation_id: str,
        task_id: str,
        source_submission_id: int,
        target_submission_id: int,
        observed_at=None,
        what_changed: dict | None = None,
        feedback_areas: list[dict] | None = None,
        new_observations: list[dict] | None = None,
        apparent_independent_corrections: list[dict] | None = None,
        no_intent_inference: str = "observational language only",
        limitations: list[str] | None = None,
    ) -> None:
        self.observation_id = observation_id
        self.task_id = task_id
        self.source_submission_id = source_submission_id
        self.target_submission_id = target_submission_id
        self.observed_at = observed_at
        self.what_changed = what_changed or {}
        self.feedback_areas = feedback_areas or []
        self.new_observations = new_observations or []
        self.apparent_independent_corrections = (
            apparent_independent_corrections or []
        )
        self.no_intent_inference = no_intent_inference
        self.limitations = limitations or []


class _PlanItem:
    """L2-shaped PriorityPlanItem."""

    def __init__(
        self,
        *,
        plan_item_id: str,
        category: str,
        diagnosis_id: str | None = None,
        evidence_refs: list[str] | None = None,
        context: dict | None = None,
    ) -> None:
        self.plan_item_id = plan_item_id
        self.category = category
        self.diagnosis_id = diagnosis_id
        self.evidence_refs = evidence_refs or []
        self.context = context or {}

    def model_dump(self, mode: str = "python", **_: object) -> dict:
        return {
            "plan_item_id": self.plan_item_id,
            "category": self.category,
            "diagnosis_id": self.diagnosis_id,
            "evidence_refs": self.evidence_refs,
            "context": self.context,
        }


class _PriorityPlan:
    """L2-shaped PriorityRevisionPlan."""

    def __init__(
        self,
        *,
        learner_id: str,
        task_id: str,
        submission_id: int,
        items: list[_PlanItem] | None = None,
        generated_at=None,
        history_state: str = "insufficient_history",
        plan_id: str = "PP-PENDING",
    ) -> None:
        self.plan_id = plan_id
        self.learner_id = learner_id
        self.task_id = task_id
        self.submission_id = submission_id
        self.generated_at = generated_at
        self.items = items or []


class _ScaffoldEvent:
    """L2-shaped ScaffoldEvent."""

    def __init__(
        self,
        *,
        learner_id: str,
        category: str,
        level: int = 1,
        learning_item_id: str | None = None,
        plan_item_id: str | None = None,
        requested_at=None,
        default_first: bool = True,
        scaffold_event_id: str = "SE-PENDING",
    ) -> None:
        self.scaffold_event_id = scaffold_event_id
        self.learner_id = learner_id
        self.learning_item_id = learning_item_id
        self.plan_item_id = plan_item_id
        self.category = category
        self.level = level
        self.requested_at = requested_at
        self.default_first = default_first
        self.limitations = []


def _seed_essay(app, essay_id: int, text: str = "Essay text.") -> None:
    with app.state.repository.connect() as connection:
        connection.execute(
            "INSERT INTO essays(essay_id, student_id, writing_prompt, genre,"
            " draft_stage, timed, tool_use, essay_text, submitted_at)"
            " VALUES (?, 'S1', 'Prompt A', 'argumentative essay',"
            " 'first draft', 0, 'none', ?, '2026-01-01T00:00:00+00:00')",
            (essay_id, text),
        )


def test_shared_store_implements_full_l2_revision_loop_protocol(tmp_path):
    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    repository = build_wave2_repository(app.state.repository)
    missing = [m for m in L2_PROTOCOL_METHODS if not hasattr(repository, m)]
    assert missing == [], f"missing L2 protocol methods: {missing}"


def test_shared_store_persists_l2_writing_task_without_genre(tmp_path):
    from datetime import datetime, timezone

    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    _seed_student(app)
    repository = build_wave2_repository(app.state.repository)

    task = repository.save_writing_task(_L2WritingTask(
        student_id="S1",
        task_type="argumentative",
        writing_context="ielts_task2",
        writing_prompt="Take a position on studying abroad.",
        metadata=_TaskMetadata(
            audience="IELTS examiner", word_constraint="at least 250 words",
        ),
        classification={
            "outcome": "classified", "task_type": "argumentative",
            "reason_code": "keywords", "taxonomy_version": "l2-task-type-v1.0.0",
        },
        status="active",
        created_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
        limitations=["Task metadata is routing/context metadata only."],
    ))
    assert task.task_id is not None and task.task_id.startswith("WT")
    assert task.writing_context == "ielts_task2"
    assert task.classification["reason_code"] == "keywords"
    assert task.status == "active"

    fetched = repository.get_writing_task(task.task_id)
    assert fetched is not None
    assert fetched.writing_context == "ielts_task2"
    assert fetched.task_type == "argumentative"
    assert fetched.classification["reason_code"] == "keywords"
    assert fetched.status == "active"
    assert fetched.metadata["audience"] == "IELTS examiner"
    assert fetched.limitations == ["Task metadata is routing/context metadata only."]
    assert [t.task_id for t in repository.list_writing_tasks("S1")] == [task.task_id]

    payload = task.model_dump(mode="json")
    assert payload["writing_context"] == "ielts_task2"
    assert payload["classification"]["reason_code"] == "keywords"
    assert payload["status"] == "active"


def test_shared_store_submission_version_family_round_trip(tmp_path):
    from datetime import datetime, timezone

    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    _seed_student(app)
    _seed_essay(app, 1, "First draft text.")
    _seed_essay(app, 2, "Revised text.")
    repository = build_wave2_repository(app.state.repository)
    task = repository.save_writing_task(_L2WritingTask(
        student_id="S1",
        task_type="argumentative",
        writing_context="ielts_task2",
        writing_prompt="Take a position on studying abroad.",
    ))

    v1 = repository.save_submission_version(_SubmissionVersion(
        task_id=task.task_id,
        submission_id=1,
        version_number=1,
        ancestry=[1],
        submitted_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
        task_context={"task_type": "argumentative", "writing_context": "ielts_task2"},
        essay_text_hash="hash-v1",
        draft_stage="first draft",
        analysis_run_id="AR000001",
        analysis_version="v1",
        feedback_record_id=1,
        corpus_routing={"routed": False},
    ))
    assert v1.task_id == task.task_id
    assert v1.submission_id == 1
    assert v1.version_number == 1

    v2 = repository.save_submission_version(_SubmissionVersion(
        task_id=task.task_id,
        submission_id=2,
        version_number=2,
        revision_of_submission_id=1,
        ancestry=[1, 2],
        submitted_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
        task_context={"task_type": "argumentative", "writing_context": "ielts_task2"},
        essay_text_hash="hash-v2",
        draft_stage="revised draft",
        revision_group_id="RG000001",
        revision_snapshot_id="RS000001",
        limitations=["Versions are append-only."],
    ))
    assert v2.revision_of_submission_id == 1
    assert v2.ancestry == [1, 2]

    fetched = repository.get_submission_version(task.task_id, 2)
    assert fetched is not None
    assert fetched.revision_of_submission_id == 1
    assert fetched.ancestry == [1, 2]
    assert fetched.task_context["writing_context"] == "ielts_task2"
    assert fetched.limitations == ["Versions are append-only."]
    assert repository.get_submission_version(task.task_id, 999) is None

    versions = repository.list_submission_versions(task.task_id)
    assert [v.version_number for v in versions] == [1, 2]
    assert repository.find_task_id_for_submission(2) == task.task_id
    assert repository.find_task_id_for_submission(999) is None


def test_shared_store_revision_observation_round_trip(tmp_path):
    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    _seed_student(app)
    _seed_essay(app, 1)
    _seed_essay(app, 2)
    repository = build_wave2_repository(app.state.repository)
    task = repository.save_writing_task(_L2WritingTask(
        student_id="S1",
        task_type="argumentative",
        writing_context="ielts_task2",
        writing_prompt="Take a position on studying abroad.",
    ))

    repository.save_revision_observation(_RevisionObservation(
        observation_id="RO-1-2",
        task_id=task.task_id,
        source_submission_id=1,
        target_submission_id=2,
        what_changed={"inserted_tokens": 5, "deleted_tokens": 1},
        feedback_areas=[{"category": "essay_length", "status": "appears_addressed"}],
        no_intent_inference="Observations describe observed text changes only.",
    ))
    observations = repository.list_revision_observations(task.task_id)
    assert len(observations) == 1
    assert observations[0].observation_id == "RO-1-2"
    assert observations[0].what_changed["inserted_tokens"] == 5
    assert observations[0].feedback_areas[0]["status"] == "appears_addressed"
    assert observations[0].no_intent_inference.startswith("Observations describe")
    assert repository.list_revision_observations("WT999999") == []


def test_shared_store_priority_plan_and_scaffold_families(tmp_path):
    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    _seed_student(app)
    _seed_essay(app, 1)
    repository = build_wave2_repository(app.state.repository)
    task = repository.save_writing_task(_L2WritingTask(
        student_id="S1",
        task_type="argumentative",
        writing_context="ielts_task2",
        writing_prompt="Take a position on studying abroad.",
    ))

    repository.save_priority_plan(_PriorityPlan(
        learner_id="S1",
        task_id=task.task_id,
        submission_id=1,
        items=[_PlanItem(
            plan_item_id="PPI000001",
            category="essay_length",
            diagnosis_id="DG000001",
            evidence_refs=["submission:1"],
            context={"task_type": "argumentative"},
        )],
    ))
    plans = repository.list_priority_plans("S1")
    assert len(plans) == 1
    plan = plans[0]
    assert plan.plan_id is not None and plan.plan_id.startswith("PP")
    assert plan.task_id == task.task_id
    assert plan.submission_id == 1
    assert plan.items[0].plan_item_id == "PPI000001"
    assert plan.items[0].category == "essay_length"
    assert plan.items[0].evidence_refs == ["submission:1"]
    fetched_plan = repository.get_priority_plan(plan.plan_id)
    assert fetched_plan is not None
    assert fetched_plan.items[0].plan_item_id == "PPI000001"
    assert repository.list_priority_plans("NO_SUCH_LEARNER") == []

    repository.save_scaffold_event(_ScaffoldEvent(
        learner_id="S1",
        category="essay_length",
        level=1,
        plan_item_id="PPI000001",
        default_first=True,
    ))
    events = repository.list_scaffold_events("S1")
    assert len(events) == 1
    assert events[0].scaffold_event_id is not None
    assert events[0].scaffold_event_id.startswith("SE")
    assert events[0].category == "essay_length"
    assert events[0].level == 1
    assert events[0].default_first is True
    assert repository.list_scaffold_events("S1", learning_item_id="LI000001") == []


def test_shared_store_learning_item_l2_fields_round_trip(tmp_path):
    from datetime import datetime, timezone

    from app.api.main import create_app

    app = create_app(_settings(tmp_path))
    _seed_student(app)
    repository = build_wave2_repository(app.state.repository)

    saved = repository.save_learning_item(LearningItem(
        student_id="S1",
        category="essay_length",
        originating_evidence={"submission_ids": [1]},
        feedback_reference="feedback:1",
        revision_history=[{"version_number": 2, "submission_id": 2}],
        task_id=None,
        task_context={"task_type": "argumentative", "writing_context": "ielts_task2"},
        status="proposed",
        updated_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
        limitations=["LearningItem v1 is a durable learning target."],
    ))
    assert saved.learning_item_id is not None
    assert saved.learning_item_id.startswith("LI")
    assert saved.category == "essay_length"

    fetched = repository.get_learning_item(saved.learning_item_id)
    assert fetched is not None
    assert fetched.category == "essay_length"
    assert fetched.task_context == {
        "task_type": "argumentative", "writing_context": "ielts_task2",
    }
    assert fetched.limitations == ["LearningItem v1 is a durable learning target."]
    assert fetched.originating_evidence == {"submission_ids": [1]}
    assert fetched.revision_history == [{"version_number": 2, "submission_id": 2}]
    assert [i.learning_item_id for i in repository.list_learning_items("S1")] == [
        saved.learning_item_id,
    ]

    payload = saved.model_dump(mode="json")
    assert payload["category"] == "essay_length"
    assert payload["task_context"]["writing_context"] == "ielts_task2"
    assert payload["limitations"] == ["LearningItem v1 is a durable learning target."]

    updated = repository.update_learning_item_status(
        saved.learning_item_id, "active",
        datetime(2026, 8, 11, 1, 0, tzinfo=timezone.utc),
    )
    assert updated is not None
    assert updated.status == "active"
    assert repository.get_learning_item(saved.learning_item_id).status == "active"
