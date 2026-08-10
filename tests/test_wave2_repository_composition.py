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
