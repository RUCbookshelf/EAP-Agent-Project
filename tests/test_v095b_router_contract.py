"""v0.9.5-B router-decomposition and health-contract tests.

Pins the public route contract (path+method surface), the single canonical
lifecycle-based /api/v1/system/health handler, production/test parity, the
unchanged live/ready endpoints, and the request-ID/error-envelope behavior.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.api.routers import (
    admin,
    analysis,
    calf,
    journey,
    practice,
    research,
    revisions,
    students,
    submissions,
)
from app.config import Settings
from app.database import LATEST_MIGRATION_VERSION
from app.version import PLATFORM_APPLICATION_VERSION
from app.lifecycle import ServiceState, lifecycle


_BUSINESS_ROUTERS = (
    submissions,
    analysis,
    calf,
    revisions,
    students,
    admin,
    practice,
    journey,
    research,
)


def make_test_app_settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "prod-contract.db", llm_provider="local",
        deepseek_api_key=None, deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )


def make_test_app(tmp_path):
    settings = Settings(
        database_path=tmp_path / "api.db", llm_provider="local",
        deepseek_api_key=None, deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    return create_app(settings)


def make_prod_app_with_business_routers(settings):
    """Production builder at steady state: system router + startup business routers."""
    app = create_app(settings)
    for module in _BUSINESS_ROUTERS:
        app.include_router(module.router)
    return app


def route_surface(app):
    pairs = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                pairs.add((method, path))
    return pairs


@pytest.fixture(autouse=True)
def _restore_lifecycle():
    saved = (
        lifecycle.state,
        lifecycle.database_status,
        lifecycle.migration_version,
        lifecycle.active_configuration,
        lifecycle.application_version,
    )
    yield
    (
        lifecycle.state,
        lifecycle.database_status,
        lifecycle.migration_version,
        lifecycle.active_configuration,
        lifecycle.application_version,
    ) = saved


EXPECTED_ROUTE_CONTRACT = {
    ("GET", "/api/v1/admin/algorithms"),
    ("GET", "/api/v1/admin/configurations"),
    ("GET", "/api/v1/admin/metrics"),
    ("GET", "/api/v1/admin/registries"),
    ("GET", "/api/v1/calf/analysis-units"),
    ("GET", "/api/v1/calf/constructs"),
    ("GET", "/api/v1/calf/metrics"),
    ("GET", "/api/v1/calf/metrics/{metric_id}"),
    ("GET", "/api/v1/exercises/{exercise_id}/attempts"),
    ("GET", "/api/v1/practice-targets/{practice_target_id}/exercises"),
    ("GET", "/api/v1/research/data-quality"),
    ("GET", "/api/v1/research/export/{export_id}"),
    ("GET", "/api/v1/research/export/{export_id}/manifest"),
    ("GET", "/api/v1/research/export/history"),
    ("GET", "/api/v1/research/export/schema"),
    ("GET", "/api/v1/research/reviews"),
    ("GET", "/api/v1/revisions/{revision_group_id}"),
    ("GET", "/api/v1/revisions/{revision_group_id}/comparison"),
    ("GET", "/api/v1/revisions/{revision_group_id}/trajectory"),
    ("GET", "/api/v1/review/events/{learning_item_id}"),
    ("GET", "/api/v1/review/practice-activities/{learning_item_id}"),
    ("GET", "/api/v1/review/schedule/{learning_item_id}"),
    ("GET", "/api/v1/students/{student_id}"),
    ("GET", "/api/v1/students/{student_id}/calf-trajectories"),
    ("GET", "/api/v1/students/{student_id}/dashboard"),
    ("GET", "/api/v1/students/{student_id}/engagement-traces"),
    ("GET", "/api/v1/students/{student_id}/history"),
    ("GET", "/api/v1/students/{student_id}/journey"),
    ("GET", "/api/v1/students/{student_id}/learner-model"),
    ("GET", "/api/v1/students/{student_id}/learner-model/diagnostic-trajectories"),
    ("GET", "/api/v1/students/{student_id}/learner-model/history-evidence"),
    ("GET", "/api/v1/students/{student_id}/learner-model/learning-targets"),
    ("GET", "/api/v1/students/{student_id}/learner-model/metric-trajectories"),
    ("GET", "/api/v1/students/{student_id}/learner-model/snapshots"),
    ("GET", "/api/v1/students/{student_id}/learner-model/snapshots/{snapshot_id}"),
    ("GET", "/api/v1/students/{student_id}/learner-model/task-clusters"),
    ("GET", "/api/v1/students/{student_id}/practice-targets"),
    ("GET", "/api/v1/students/{student_id}/practice-targets/{practice_target_id}/context"),
    ("GET", "/api/v1/students/{student_id}/practice-targets/{practice_target_id}/evaluations"),
    ("GET", "/api/v1/students/{student_id}/profile"),
    ("GET", "/api/v1/students/{student_id}/progress"),
    ("GET", "/api/v1/students/{student_id}/revision-candidates"),
    ("GET", "/api/v1/students/{student_id}/transfer-evidence"),
    ("GET", "/api/v1/submissions/{submission_id}"),
    ("GET", "/api/v1/submissions/{submission_id}/analyses"),
    ("GET", "/api/v1/submissions/{submission_id}/analysis-units"),
    ("GET", "/api/v1/submissions/{submission_id}/calf"),
    ("GET", "/api/v1/submissions/{submission_id}/diagnostic-audit"),
    ("GET", "/api/v1/submissions/{submission_id}/error-annotations"),
    ("GET", "/api/v1/submissions/{submission_id}/pii-candidates"),
    ("GET", "/api/v1/submissions/{submission_id}/revision-analysis"),
    ("GET", "/api/v1/submissions/{submission_id}/revision-candidates"),
    ("GET", "/api/v1/submissions/{submission_id}/syntactic-units"),
    ("GET", "/api/v1/system/health"),
    ("GET", "/api/v1/system/live"),
    ("GET", "/api/v1/system/ready"),
    ("GET", "/api/v1/system/version"),
    # Wave-2 routes (F-3 pin refresh; merged composition surface)
    ("GET", "/api/v1/wave2/learner/difficulties"),
    ("GET", "/api/v1/wave2/learner/evidence"),
    ("GET", "/api/v1/wave2/learner/observations"),
    ("GET", "/api/v1/wave2/learner/observations/{observation_id}"),
    ("GET", "/api/v1/wave2/learner/proficiency-context"),
    ("GET", "/api/v1/wave2/learner/stable"),
    ("GET", "/api/v1/wave2/learner/strengths"),
    ("GET", "/api/v1/wave2/personalized/learning-items"),
    ("GET", "/api/v1/wave2/revision/tasks/{task_id}"),
    ("GET", "/api/v1/wave2/revision/tasks/{task_id}/versions"),
    (
        "GET",
        "/api/v1/wave2/revision/tasks/{task_id}/versions/"
        "{submission_id}/observation",
    ),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/openapi.json"),
    ("GET", "/redoc"),
    ("PATCH", "/api/v1/wave2/personalized/learning-items/{learning_item_id}"),
    ("POST", "/api/v1/admin/configurations"),
    ("POST", "/api/v1/admin/configurations/{configuration_id}/activate"),
    ("POST", "/api/v1/admin/configurations/{configuration_id}/rollback"),
    ("POST", "/api/v1/admin/configurations/{configuration_id}/validate"),
    ("POST", "/api/v1/admin/reanalysis/preview"),
    ("POST", "/api/v1/admin/reanalysis/run"),
    ("POST", "/api/v1/exercises/{exercise_id}/attempts"),
    ("POST", "/api/v1/practice-targets"),
    ("POST", "/api/v1/practice-targets/{practice_target_id}/complete"),
    ("POST", "/api/v1/practice-targets/{practice_target_id}/exercises"),
    ("POST", "/api/v1/research/dataset-split"),
    ("POST", "/api/v1/research/export/preview"),
    ("POST", "/api/v1/research/export/run"),
    ("POST", "/api/v1/research/reviews"),
    ("POST", "/api/v1/revisions"),
    ("POST", "/api/v1/review/events"),
    ("POST", "/api/v1/review/practice-activities"),
    ("POST", "/api/v1/students/{student_id}/learner-model/preview"),
    ("POST", "/api/v1/students/{student_id}/learner-model/rebuild"),
    ("POST", "/api/v1/submissions"),
    ("POST", "/api/v1/submissions/{submission_id}/analyses"),
    ("POST", "/api/v1/submissions/{submission_id}/calf/reanalyze"),
    ("POST", "/api/v1/submissions/{submission_id}/error-annotations/import"),
    ("POST", "/api/v1/submissions/{submission_id}/pii-review"),
    ("POST", "/api/v1/wave2/personalized/learning-items"),
    ("POST", "/api/v1/wave2/personalized/priority-plan"),
    ("POST", "/api/v1/wave2/personalized/scaffold"),
    ("POST", "/api/v1/wave2/revision/submissions/{submission_id}/reanalysis"),
    ("POST", "/api/v1/wave2/revision/tasks"),
    ("POST", "/api/v1/wave2/revision/tasks/{task_id}/submissions"),
    (
        "POST",
        "/api/v1/wave2/revision/tasks/{task_id}/submissions/"
        "{submission_id}/revisions",
    ),
    ("POST", "/api/v1/writing-intelligence/slice"),
}


def test_route_contract_pinned(tmp_path):
    app = make_test_app(tmp_path)
    assert route_surface(app) == EXPECTED_ROUTE_CONTRACT


def test_no_duplicate_path_method_pairs(tmp_path):
    app = make_test_app(tmp_path)
    pairs = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                pairs.append((method, path))
    assert len(pairs) == len(set(pairs))


def test_health_registered_exactly_once_in_both_builders(tmp_path):
    for app in (make_test_app(tmp_path), make_prod_app_with_business_routers(make_test_app_settings(tmp_path))):
        health_routes = [
            route
            for route in app.routes
            if getattr(route, "path", None) == "/api/v1/system/health"
            and "GET" in (getattr(route, "methods", None) or set())
        ]
        assert len(health_routes) == 1
        assert health_routes[0].endpoint.__module__ == "app.api.routers.system"


def test_production_and_test_route_sets_match(tmp_path):
    test_app = make_test_app(tmp_path)
    prod_app = make_prod_app_with_business_routers(make_test_app_settings(tmp_path))
    assert route_surface(test_app) == route_surface(prod_app)


def test_health_operation_id_single_and_stable(tmp_path):
    spec = make_test_app(tmp_path).openapi()
    health_operations = spec["paths"]["/api/v1/system/health"]
    assert set(health_operations) == {"get"}
    assert health_operations["get"]["operationId"] == "health_api_v1_system_health_get"


def test_health_contract_healthy_state(tmp_path):
    app = make_test_app(tmp_path)
    lifecycle.transition(ServiceState.READY)
    lifecycle.database_status = "connected"
    lifecycle.migration_version = LATEST_MIGRATION_VERSION
    lifecycle.active_configuration = "config-v0.9.0"
    with TestClient(app) as client:
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        body = response.json()
        assert body["status"] == "ok"
        assert body["database_status"] == "connected"
        assert body["database_migration_version"] == LATEST_MIGRATION_VERSION
        assert body["application_version"] == PLATFORM_APPLICATION_VERSION
        assert "deepseek_api_key" not in response.text.casefold()


def test_health_contract_unavailable_state(tmp_path):
    app = make_test_app(tmp_path)
    lifecycle.transition(ServiceState.STARTING)
    lifecycle.database_status = "unavailable"
    with TestClient(app) as client:
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["database_status"] == "unavailable"


def test_health_semantics_identical_in_production_and_test_builders(tmp_path):
    lifecycle.transition(ServiceState.READY)
    lifecycle.database_status = "connected"
    test_app = make_test_app(tmp_path)
    prod_app = make_prod_app_with_business_routers(make_test_app_settings(tmp_path))
    with TestClient(test_app) as test_client, TestClient(prod_app) as prod_client:
        test_response = test_client.get("/api/v1/system/health")
        prod_response = prod_client.get("/api/v1/system/health")
        assert test_response.status_code == 200
        assert prod_response.status_code == 200
        assert test_response.json() == prod_response.json()
        assert "X-Request-ID" in prod_response.headers


def test_live_and_ready_unchanged(tmp_path):
    app = make_test_app(tmp_path)
    lifecycle.transition(ServiceState.STARTING)
    with TestClient(app) as client:
        live = client.get("/api/v1/system/live")
        assert live.status_code == 200
        assert live.json() == {"status": "ok", "lifecycle_state": "starting"}
        ready = client.get("/api/v1/system/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "starting"
        assert ready.json()["ready"] is False
        assert "failed_stage" in ready.json()

    lifecycle.transition(ServiceState.READY)
    with TestClient(app) as client:
        ready = client.get("/api/v1/system/ready")
        assert ready.json()["ready"] is True


def test_business_route_gated_until_ready_while_health_available(tmp_path):
    app = make_prod_app_with_business_routers(make_test_app_settings(tmp_path))
    lifecycle.transition(ServiceState.STARTING)
    client = TestClient(app)  # no lifespan: startup stage does not run
    try:
        health = client.get("/api/v1/system/health")
        assert health.status_code == 200
        gated = client.get("/api/v1/submissions/999")
        assert gated.status_code == 503
        assert gated.json()["error"]["code"] == "not_ready"
    finally:
        client.close()
