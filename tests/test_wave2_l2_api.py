"""Wave-2 Goal C -- revision_api + personalized_api router tests (TDD red phase).

Endpoints live under /api/v1/wave2/revision/ and /api/v1/wave2/personalized/.
All outputs use bounded non-normative language; unsupported normative/mastery
claims are rejected (inputs -> 422, composed outputs -> 500 structural
rejection); explicit insufficient-history states are first-class.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.personalized import PersonalizedBridgeService
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from app.l2.wave2.revision_loop import RevisionLoopService
from app.learner.normative import NormativeClaimsScanner
from app.api.routers.wave2_modules import personalized_api, revision_api
from tests.wave2_l2_pipeline import (
    V1_SHORT_REPETITIVE,
    V2_LONG_VARIED,
    build_real_pipeline,
)


SCANNER = NormativeClaimsScanner()


def _payload(**overrides) -> dict:
    values = dict(
        student_id="L-API-01",
        task_type="argumentative",
        writing_context="ielts_task2",
        writing_prompt="Take a position on studying abroad.",
    )
    values.update(overrides)
    return values


@pytest.fixture
def client(tmp_path):
    pipeline, _, _ = build_real_pipeline(tmp_path, database_name="api.db")
    revision_service = RevisionLoopService(
        repository=InMemoryRevisionLoopRepository(),
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    personalized_service = PersonalizedBridgeService(
        repository=revision_service.repository,
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    app = FastAPI()
    app.include_router(revision_api.router)
    app.include_router(personalized_api.router)
    app.dependency_overrides[revision_api.get_revision_loop_service] = (
        lambda: revision_service
    )
    app.dependency_overrides[personalized_api.get_personalized_bridge_service] = (
        lambda: personalized_service
    )
    return TestClient(app), revision_service


class TestRouterShape:
    def test_routers_importable_as_namespace_package(self) -> None:
        assert revision_api.router is not None
        assert personalized_api.router is not None

    def test_route_paths(self) -> None:
        revision_paths = {route.path for route in revision_api.router.routes}
        assert {
            "/api/v1/wave2/revision/tasks",
            "/api/v1/wave2/revision/tasks/{task_id}",
            "/api/v1/wave2/revision/tasks/{task_id}/submissions",
            "/api/v1/wave2/revision/tasks/{task_id}/submissions/{submission_id}/revisions",
            "/api/v1/wave2/revision/tasks/{task_id}/versions",
            "/api/v1/wave2/revision/tasks/{task_id}/versions/{submission_id}/observation",
            "/api/v1/wave2/revision/submissions/{submission_id}/reanalysis",
        } <= revision_paths
        personalized_paths = {route.path for route in personalized_api.router.routes}
        assert {
            "/api/v1/wave2/personalized/priority-plan",
            "/api/v1/wave2/personalized/scaffold",
            "/api/v1/wave2/personalized/learning-items",
            "/api/v1/wave2/personalized/learning-items/{learning_item_id}",
        } <= personalized_paths


class TestRevisionApi:
    def test_create_task(self, client) -> None:
        tc, _ = client
        response = tc.post("/api/v1/wave2/revision/tasks", json=_payload())
        assert response.status_code == 201
        body = response.json()
        assert body["task_id"].startswith("WT")
        assert body["task_type"] == "argumentative"
        assert body["writing_context"] == "ielts_task2"

    def test_submit_revise_versions_observation_reanalysis(self, client) -> None:
        tc, _ = client
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload(
            student_id="L-API-02",
        )).json()
        v1 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions",
            json={"essay_text": V1_SHORT_REPETITIVE},
        )
        assert v1.status_code == 201
        v1_body = v1.json()
        assert v1_body["version_number"] == 1
        assert v1_body["feedback_record_id"]

        v2 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions/"
            f"{v1_body['submission_id']}/revisions",
            json={"essay_text": V2_LONG_VARIED},
        )
        assert v2.status_code == 201
        v2_body = v2.json()
        assert v2_body["version_number"] == 2
        assert v2_body["ancestry"] == [v1_body["submission_id"], v2_body["submission_id"]]

        versions = tc.get(f"/api/v1/wave2/revision/tasks/{task['task_id']}/versions")
        assert versions.status_code == 200
        assert len(versions.json()["versions"]) == 2

        observation = tc.get(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/versions/"
            f"{v2_body['submission_id']}/observation",
        )
        assert observation.status_code == 200
        assert observation.json()["what_changed"]["inserted_tokens"] > 0
        assert observation.json()["no_intent_inference"]

        reanalysis = tc.post(
            f"/api/v1/wave2/revision/submissions/{v2_body['submission_id']}/reanalysis",
            json={},
        )
        assert reanalysis.status_code == 200
        assert reanalysis.json()["analysis_run_id"]

    def test_unknown_task_404(self, client) -> None:
        tc, _ = client
        assert tc.get("/api/v1/wave2/revision/tasks/WT999999").status_code == 404


class TestPersonalizedApi:
    def _seed(self, tc):
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload(
            student_id="L-API-03",
        )).json()
        v1 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions",
            json={"essay_text": V1_SHORT_REPETITIVE},
        ).json()
        return task, v1

    def test_priority_plan(self, client) -> None:
        tc, _ = client
        task, v1 = self._seed(tc)
        response = tc.post("/api/v1/wave2/personalized/priority-plan", json={
            "learner_id": "L-API-03",
            "task_id": task["task_id"],
            "submission_id": v1["submission_id"],
        })
        assert response.status_code == 200
        body = response.json()
        assert body["history_state"] == "insufficient_history"
        assert body["items"]
        assert all(
            item["ordering_note"] == "action-priority ordering only; not a learner-performance ranking"
            for item in body["items"]
        )

    def test_scaffold_defaults_to_level_one(self, client) -> None:
        tc, _ = client
        response = tc.post("/api/v1/wave2/personalized/scaffold", json={
            "learner_id": "L-API-03",
            "category": "essay_length",
            "evidence": "The draft contains 20 words.",
        })
        assert response.status_code == 200
        body = response.json()
        assert body["level"] == 1
        assert body["default_first"] is True
        assert body["available_levels"] == [1, 2, 3, 4, 5, 6, 7]

    def test_unsupported_mastery_claim_in_scaffold_rejected(self, client) -> None:
        tc, _ = client
        response = tc.post("/api/v1/wave2/personalized/scaffold", json={
            "learner_id": "L-API-03",
            "category": "essay_length",
            "evidence": "I mastered the grammar completely.",
        })
        assert response.status_code == 422
        assert "mastered" not in response.text.casefold()

    def test_learning_item_lifecycle(self, client) -> None:
        tc, _ = client
        task, v1 = self._seed(tc)
        plan = tc.post("/api/v1/wave2/personalized/priority-plan", json={
            "learner_id": "L-API-03",
            "task_id": task["task_id"],
            "submission_id": v1["submission_id"],
        }).json()
        created = tc.post("/api/v1/wave2/personalized/learning-items", json={
            "learner_id": "L-API-03",
            "plan_item_id": plan["items"][0]["plan_item_id"],
        })
        assert created.status_code == 201
        item = created.json()
        assert item["student_id"] == "L-API-03"
        assert item["status"] == "proposed"
        listed = tc.get(
            "/api/v1/wave2/personalized/learning-items",
            params={"student_id": "L-API-03"},
        )
        assert listed.status_code == 200
        assert [i["learning_item_id"] for i in listed.json()["items"]] == [
            item["learning_item_id"],
        ]
        patched = tc.patch(
            f"/api/v1/wave2/personalized/learning-items/{item['learning_item_id']}",
            json={"status": "active"},
        )
        assert patched.status_code == 200
        assert patched.json()["status"] == "active"


class TestNormativeGuards:
    def test_output_guard_rejects_normative_claims(self) -> None:
        from app.api.routers.wave2_modules.personalized_api import (
            reject_normative_output,
        )
        with pytest.raises(HTTPException) as excinfo:
            reject_normative_output({"statement": "The learner mastered grammar."})
        assert excinfo.value.status_code == 500

    def test_api_responses_scan_clean(self, client) -> None:
        tc, _ = client
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload(
            student_id="L-API-04",
        )).json()
        v1 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions",
            json={"essay_text": V1_SHORT_REPETITIVE},
        ).json()
        v2 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions/"
            f"{v1['submission_id']}/revisions",
            json={"essay_text": V2_LONG_VARIED},
        ).json()
        paths = (
            ("get", f"/api/v1/wave2/revision/tasks/{task['task_id']}", None),
            ("get", f"/api/v1/wave2/revision/tasks/{task['task_id']}/versions", None),
            ("get", f"/api/v1/wave2/revision/tasks/{task['task_id']}/versions/{v2['submission_id']}/observation", None),
            ("post", "/api/v1/wave2/personalized/priority-plan", {
                "learner_id": "L-API-04",
                "task_id": task["task_id"],
                "submission_id": v2["submission_id"],
            }),
        )
        for method, path, payload in paths:
            response = tc.request(method, path, json=payload)
            assert response.status_code == 200
            assert SCANNER.scan_mapping(response.json(), documentation=True) == []
