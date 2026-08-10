"""Wave-2 F-1 repair -- shared-repository consumption + fallback tests.

Goal PDW2-WU2-F1-L2-REPOSITORY-CONSUME: ``revision_api`` and
``personalized_api`` must consume ``request.app.state.wave2_repository``
(the CORE-composed shared store) when present, and fall back to the
module-local repository only for standalone test contexts.

These tests exercise the DEFAULT dependencies (no ``dependency_overrides``):

- shared consumption: a task created through the revision router must be
  visible to the personalized router through ONE shared repository (the F-1
  e2e regression: priority-plan 404 ``WT000001`` and unreachable
  LearningItems);
- fallback: without ``app.state.wave2_repository`` the dependencies build
  services over the module-local in-memory repository.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.routers.wave2_modules import personalized_api, revision_api
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from tests.wave2_l2_pipeline import V1_SHORT_REPETITIVE, build_real_services


def _request_for(app: FastAPI) -> Request:
    """Minimal ASGI scope with ``app`` so ``request.app.state`` resolves."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "app": app,
    }
    return Request(scope)


def _composed_app(
    tmp_path,
    *,
    shared_repository: InMemoryRevisionLoopRepository | None = None,
    expose_shared: bool = True,
) -> FastAPI:
    """Real composition-root services + optional shared wave2 repository."""
    _, _, submission_service, reanalysis_service = build_real_services(
        tmp_path, database_name="consume.db",
    )
    app = FastAPI()
    app.state.submission_service = submission_service
    app.state.reanalysis = reanalysis_service
    if expose_shared:
        app.state.wave2_repository = (
            shared_repository or InMemoryRevisionLoopRepository()
        )
    app.include_router(revision_api.router)
    app.include_router(personalized_api.router)
    return app


class TestSharedRepositoryConsumption:
    def test_revision_service_consumes_shared_repository(self, tmp_path) -> None:
        shared = InMemoryRevisionLoopRepository()
        app = _composed_app(tmp_path, shared_repository=shared)
        service = revision_api.get_revision_loop_service(_request_for(app))
        assert service.repository is shared

    def test_personalized_service_consumes_shared_repository(self, tmp_path) -> None:
        shared = InMemoryRevisionLoopRepository()
        app = _composed_app(tmp_path, shared_repository=shared)
        service = personalized_api.get_personalized_bridge_service(_request_for(app))
        assert service.repository is shared

    def test_both_routers_share_one_repository_instance(self, tmp_path) -> None:
        shared = InMemoryRevisionLoopRepository()
        app = _composed_app(tmp_path, shared_repository=shared)
        revision_service = revision_api.get_revision_loop_service(_request_for(app))
        personalized_service = personalized_api.get_personalized_bridge_service(
            _request_for(app)
        )
        assert revision_service.repository is personalized_service.repository is shared

    def test_revision_created_task_visible_to_personalized_router(self, tmp_path) -> None:
        """F-1 regression: default dependencies, one shared store."""
        shared = InMemoryRevisionLoopRepository()
        app = _composed_app(tmp_path, shared_repository=shared)
        with TestClient(app) as client:
            task = client.post(
                "/api/v1/wave2/revision/tasks",
                json={
                    "student_id": "L-CONSUME-01",
                    "task_type": "argumentative",
                    "writing_context": "ielts_task2",
                    "writing_prompt": "Take a position on studying abroad.",
                },
            )
            assert task.status_code == 201
            task_id = task.json()["task_id"]
            assert shared.get_writing_task(task_id) is not None

            v1 = client.post(
                f"/api/v1/wave2/revision/tasks/{task_id}/submissions",
                json={"essay_text": V1_SHORT_REPETITIVE},
            )
            assert v1.status_code == 201
            v1_body = v1.json()

            plan = client.post(
                "/api/v1/wave2/personalized/priority-plan",
                json={
                    "learner_id": "L-CONSUME-01",
                    "task_id": task_id,
                    "submission_id": v1_body["submission_id"],
                },
            )
            assert plan.status_code == 200
            plan_body = plan.json()
            assert plan_body["history_state"] == "insufficient_history"
            assert plan_body["items"]

            item = client.post(
                "/api/v1/wave2/personalized/learning-items",
                json={
                    "learner_id": "L-CONSUME-01",
                    "plan_item_id": plan_body["items"][0]["plan_item_id"],
                },
            )
            assert item.status_code == 201
            assert item.json()["status"] == "proposed"


class TestStandaloneFallback:
    def test_revision_falls_back_to_module_local_repository(self, tmp_path) -> None:
        app = _composed_app(tmp_path, expose_shared=False)
        service = revision_api.get_revision_loop_service(_request_for(app))
        assert service.repository is revision_api._DEFAULT_REPOSITORY

    def test_personalized_falls_back_to_module_local_repository(self, tmp_path) -> None:
        app = _composed_app(tmp_path, expose_shared=False)
        service = personalized_api.get_personalized_bridge_service(_request_for(app))
        assert service.repository is personalized_api._DEFAULT_REPOSITORY

    def test_standalone_flow_still_works_without_shared_store(self, tmp_path) -> None:
        """Fallback context: both routers keep working (per-router local)."""
        app = _composed_app(tmp_path, expose_shared=False)
        with TestClient(app) as client:
            task = client.post(
                "/api/v1/wave2/revision/tasks",
                json={
                    "student_id": "L-STANDALONE-01",
                    "task_type": "argumentative",
                    "writing_context": "ielts_task2",
                    "writing_prompt": "Take a position on studying abroad.",
                },
            )
            assert task.status_code == 201
            task_id = task.json()["task_id"]
            assert revision_api._DEFAULT_REPOSITORY.get_writing_task(task_id) is not None

            v1 = client.post(
                f"/api/v1/wave2/revision/tasks/{task_id}/submissions",
                json={"essay_text": V1_SHORT_REPETITIVE},
            )
            assert v1.status_code == 201

            scaffold = client.post(
                "/api/v1/wave2/personalized/scaffold",
                json={
                    "learner_id": "L-STANDALONE-01",
                    "category": "essay_length",
                    "evidence": "The draft contains 20 words.",
                },
            )
            assert scaffold.status_code == 200
            assert scaffold.json()["level"] == 1

    def test_shared_absent_falls_back_for_both_dependencies(self, tmp_path) -> None:
        app = _composed_app(tmp_path, expose_shared=False)
        revision_service = revision_api.get_revision_loop_service(_request_for(app))
        personalized_service = personalized_api.get_personalized_bridge_service(
            _request_for(app)
        )
        assert revision_service.repository is revision_api._DEFAULT_REPOSITORY
        assert (
            personalized_service.repository
            is personalized_api._DEFAULT_REPOSITORY
        )


__all__ = []
