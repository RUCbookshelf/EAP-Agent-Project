"""Wave-3 WU3 root-level contract tests (composition-aware router tests).

The WU3 endpoints live under /api/v1/wave2/personalized/ alongside the
existing WU2 routes (which are preserved unchanged). All outputs are
bounded and non-normative; unsupported normative/mastery claims are
rejected; explicit insufficient-history states are first-class; Tutor
execution requires explicit learner consent and decline is side-effect safe.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.wave2_modules import personalized_api, revision_api
from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.personalized import PersonalizedBridgeService
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from app.l2.wave2.revision_loop import RevisionLoopService
from app.l2.wave3.adapters import (
    ExistingPracticeActivitySource,
    InMemoryConsentStore,
    InMemoryReviewEvidenceStore,
    PipelineAuthenticObservationReader,
)
from app.l2.wave3.adaptive_practice import AdaptivePracticeService
from app.l2.wave3.mini_writing import MiniWritingService
from app.l2.wave3.tutor import ProactiveTutorService
from tests.wave2_l2_pipeline import V1_SHORT_REPETITIVE, build_real_pipeline


CONSENT_SCOPE = "proactive_tutor_execution"
CONSENT_VERSION = "learner-consent-v0.1.0"
NOW = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)


def _payload(**overrides) -> dict:
    values = dict(
        student_id="L-W3-01",
        task_type="argumentative",
        writing_context="ielts_task2",
        writing_prompt="Take a position on studying abroad.",
    )
    values.update(overrides)
    return values


@pytest.fixture
def client(tmp_path):
    pipeline, _, _ = build_real_pipeline(tmp_path, database_name="w3-api.db")
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
    adaptive = AdaptivePracticeService(
        repository=revision_service.repository,
        pipeline=pipeline,
        activity_source=ExistingPracticeActivitySource(),
        now=lambda: NOW,
    )
    mini_writing = MiniWritingService(
        revision_loop=revision_service, now=lambda: NOW,
    )
    consent_store = InMemoryConsentStore()
    tutor = ProactiveTutorService(
        repository=revision_service.repository,
        consent_store=consent_store,
        review_evidence=InMemoryReviewEvidenceStore(),
        observation_source=PipelineAuthenticObservationReader(
            revision_service.repository, pipeline,
        ),
        adaptive=adaptive,
        now=lambda: NOW,
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
    app.dependency_overrides[personalized_api.get_wave3_adaptive_service] = (
        lambda: adaptive
    )
    app.dependency_overrides[personalized_api.get_wave3_mini_writing_service] = (
        lambda: mini_writing
    )
    app.dependency_overrides[personalized_api.get_wave3_tutor_service] = (
        lambda: tutor
    )
    return TestClient(app), {
        "revision_service": revision_service,
        "tutor": tutor,
        "adaptive": adaptive,
    }


class TestRouterShape:
    def test_wave3_routes_present_and_wave2_routes_preserved(self, client) -> None:
        tc, _ = client
        paths = {route.path for route in personalized_api.router.routes}
        assert {
            "/api/v1/wave2/personalized/priority-plan",
            "/api/v1/wave2/personalized/scaffold",
            "/api/v1/wave2/personalized/learning-items",
            "/api/v1/wave2/personalized/learning-items/{learning_item_id}",
        } <= paths
        assert {
            "/api/v1/wave2/personalized/adaptive-practice/recommend",
            "/api/v1/wave2/personalized/adaptive-practice/select",
            "/api/v1/wave2/personalized/adaptive-practice/evaluate",
            "/api/v1/wave2/personalized/mini-writing",
            "/api/v1/wave2/personalized/tutor/recommend",
            "/api/v1/wave2/personalized/tutor/accept",
            "/api/v1/wave2/personalized/tutor/decline",
            "/api/v1/wave2/personalized/tutor/observation",
        } <= paths


class TestAdaptivePracticeApi:
    def test_recommend_then_select_flow(self, client) -> None:
        tc, _ = client
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload()).json()
        v1 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions",
            json={"essay_text": V1_SHORT_REPETITIVE},
        ).json()
        plan = tc.post("/api/v1/wave2/personalized/priority-plan", json={
            "learner_id": "L-W3-01",
            "task_id": task["task_id"],
            "submission_id": v1["submission_id"],
        })
        assert plan.status_code == 200
        recommendation = tc.post(
            "/api/v1/wave2/personalized/adaptive-practice/recommend",
            json={"learner_id": "L-W3-01"},
        )
        assert recommendation.status_code == 200
        body = recommendation.json()
        assert body["state"] == "recommended"
        assert body["default_activity_id"]
        assert body["qualified_activities"]
        selection = tc.post(
            "/api/v1/wave2/personalized/adaptive-practice/select",
            json={
                "learner_id": "L-W3-01",
                "recommendation_id": body["recommendation_id"],
                "activity_id": body["default_activity_id"],
            },
        )
        assert selection.status_code == 200
        assert selection.json()["choice_kind"] == "default"

    def test_evaluate_endpoint_is_deterministic(self, client) -> None:
        tc, _ = client
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload()).json()
        v1 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions",
            json={"essay_text": V1_SHORT_REPETITIVE},
        ).json()
        tc.post("/api/v1/wave2/personalized/priority-plan", json={
            "learner_id": "L-W3-01",
            "task_id": task["task_id"],
            "submission_id": v1["submission_id"],
        })
        recommendation = tc.post(
            "/api/v1/wave2/personalized/adaptive-practice/recommend",
            json={"learner_id": "L-W3-01"},
        ).json()
        payload = {
            "learner_id": "L-W3-01",
            "activity_id": recommendation["default_activity_id"],
            "response_text": "Parks are good for health and bring communities together.",
        }
        first = tc.post(
            "/api/v1/wave2/personalized/adaptive-practice/evaluate", json=payload,
        )
        second = tc.post(
            "/api/v1/wave2/personalized/adaptive-practice/evaluate", json=payload,
        )
        assert first.status_code == 200
        assert first.json() == second.json()


class TestMiniWritingApi:
    def test_mini_writing_through_pipeline(self, client) -> None:
        tc, _ = client
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload()).json()
        response = tc.post(
            "/api/v1/wave2/personalized/mini-writing",
            json={
                "learner_id": "L-W3-01",
                "task_id": task["task_id"],
                "text": (
                    "Cities should build more parks because green spaces "
                    "improve health and give people a place to relax."
                ),
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["submission_id"] > 0
        assert body["analysis_run_id"]
        assert body["feedback_record_id"]
        assert body["bounded"] is True

    def test_mini_writing_blank_rejected(self, client) -> None:
        tc, _ = client
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload()).json()
        response = tc.post(
            "/api/v1/wave2/personalized/mini-writing",
            json={"learner_id": "L-W3-01", "task_id": task["task_id"], "text": "  "},
        )
        assert response.status_code == 422


class TestTutorApi:
    def test_insufficient_history_state(self, client) -> None:
        tc, _ = client
        response = tc.post(
            "/api/v1/wave2/personalized/tutor/recommend",
            json={"learner_id": "L-NEVER-SEEN"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "insufficient_history"

    def test_accept_requires_consent(self, client) -> None:
        tc, services = client
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload()).json()
        v1 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions",
            json={"essay_text": V1_SHORT_REPETITIVE},
        ).json()
        tc.post("/api/v1/wave2/personalized/priority-plan", json={
            "learner_id": "L-W3-01",
            "task_id": task["task_id"],
            "submission_id": v1["submission_id"],
        })
        recommendation = tc.post(
            "/api/v1/wave2/personalized/tutor/recommend",
            json={"learner_id": "L-W3-01"},
        ).json()
        missing = tc.post(
            "/api/v1/wave2/personalized/tutor/accept",
            json={
                "learner_id": "L-W3-01",
                "recommendation_id": recommendation["recommendation_id"],
                "consent": None,
            },
        )
        assert missing.status_code == 422
        granted = tc.post(
            "/api/v1/wave2/personalized/tutor/accept",
            json={
                "learner_id": "L-W3-01",
                "recommendation_id": recommendation["recommendation_id"],
                "consent": {
                    "learner_id": "L-W3-01",
                    "granted": True,
                    "revoked": False,
                    "scope": CONSENT_SCOPE,
                    "consent_version": CONSENT_VERSION,
                    "granted_at": NOW.isoformat(),
                },
            },
        )
        assert granted.status_code == 200
        assert granted.json()["decision"] == "accept"
        assert granted.json()["executed"] is True

    def test_decline_is_side_effect_safe(self, client) -> None:
        tc, _ = client
        task = tc.post("/api/v1/wave2/revision/tasks", json=_payload()).json()
        v1 = tc.post(
            f"/api/v1/wave2/revision/tasks/{task['task_id']}/submissions",
            json={"essay_text": V1_SHORT_REPETITIVE},
        ).json()
        tc.post("/api/v1/wave2/personalized/priority-plan", json={
            "learner_id": "L-W3-01",
            "task_id": task["task_id"],
            "submission_id": v1["submission_id"],
        })
        recommendation = tc.post(
            "/api/v1/wave2/personalized/tutor/recommend",
            json={"learner_id": "L-W3-01"},
        ).json()
        response = tc.post(
            "/api/v1/wave2/personalized/tutor/decline",
            json={
                "learner_id": "L-W3-01",
                "recommendation_id": recommendation["recommendation_id"],
            },
        )
        assert response.status_code == 200
        assert response.json()["decision"] == "decline"
        assert response.json()["executed"] is False

    def test_positive_observation_endpoint(self, client) -> None:
        tc, _ = client
        response = tc.post(
            "/api/v1/wave2/personalized/tutor/observation",
            json={"learner_id": "L-W3-01", "category": "lexical_repetition"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["observation"] is None or (
            body["observation"]["evidence_kind"] == "authentic_writing"
        )
