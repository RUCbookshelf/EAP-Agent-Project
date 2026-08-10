"""Wave-2 learner_api router tests (Goal PDW2-B-LEARNER-MODEL)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.wave2_modules import learner_api
from app.learner.normative import NormativeClaimsScanner
from app.learner.wave2.repository import InMemoryObservationRepository
from app.learner.wave2.services import LongitudinalLearnerService
from tests.learner.wave2_helpers import (
    make_anchor,
    make_observation,
    make_occurrence,
    make_proficiency_context,
    make_sample,
    utc,
)
from tests.learner.test_wave2_synthetic_learner import (
    LEARNER,
    NOW,
    seed_synthetic_learner,
)


SCANNER = NormativeClaimsScanner()


def build_client() -> tuple[TestClient, LongitudinalLearnerService]:
    service = LongitudinalLearnerService(
        InMemoryObservationRepository(), now=lambda: NOW,
    )
    seed_synthetic_learner(service)

    app = FastAPI()
    app.include_router(learner_api.router)
    app.dependency_overrides[learner_api.get_learner_model_service] = lambda: service
    return TestClient(app), service


class TestLearnerApi:
    def test_observations_list(self) -> None:
        client, _ = build_client()
        response = client.get("/api/v1/wave2/learner/observations", params={"learner_id": LEARNER})
        assert response.status_code == 200
        body = response.json()
        assert body["learner_id"] == LEARNER
        assert {item["observation_id"] for item in body["items"]} >= {
            "SVA-01", "CONN-01", "ART-01", "TEN-01",
        }
        sva = next(item for item in body["items"] if item["observation_id"] == "SVA-01")
        assert sva["appeared_before"] is True
        assert sva["revision_response"] == "reappeared_later"
        assert sva["claims_status"] == "observation_only"
        art = next(item for item in body["items"] if item["observation_id"] == "ART-01")
        assert art["history_state"] == "insufficient_history"

    def test_observation_detail_and_404(self) -> None:
        client, _ = build_client()
        response = client.get(
            "/api/v1/wave2/learner/observations/SVA-01",
            params={"learner_id": LEARNER},
        )
        assert response.status_code == 200
        assert response.json()["contexts"] == ["T-01", "T-02"]
        missing = client.get(
            "/api/v1/wave2/learner/observations/NOPE",
            params={"learner_id": LEARNER},
        )
        assert missing.status_code == 404

    def test_difficulties_endpoint(self) -> None:
        client, _ = build_client()
        response = client.get("/api/v1/wave2/learner/difficulties", params={"learner_id": LEARNER})
        assert response.status_code == 200
        body = response.json()
        assert {item["observation_id"] for item in body["items"]} == {"SVA-01", "TEN-01"}
        sva = next(item for item in body["items"] if item["observation_id"] == "SVA-01")
        assert sva["occurrence_history"][0]["evidence_ref"] == "E-101"
        assert sva["frequency"]["history_state"] == "sufficient"

    def test_strengths_endpoint(self) -> None:
        client, _ = build_client()
        response = client.get("/api/v1/wave2/learner/strengths", params={"learner_id": LEARNER})
        assert response.status_code == 200
        items = response.json()["items"]
        assert [item["observation_id"] for item in items] == ["CONN-01"]
        assert items[0]["history_state"] == "sufficient"

    def test_stable_endpoint(self) -> None:
        client, _ = build_client()
        response = client.get("/api/v1/wave2/learner/stable", params={"learner_id": LEARNER})
        assert response.status_code == 200
        by_id = {item["observation_id"]: item for item in response.json()["items"]}
        assert (
            by_id["SVA-01"]["stability_kind"]
            == "previously_recurring_not_recently_observed"
        )
        assert by_id["CONN-01"]["stability_kind"] == "strength_history"

    def test_proficiency_context_endpoint(self) -> None:
        client, _ = build_client()
        response = client.get(
            "/api/v1/wave2/learner/proficiency-context",
            params={"learner_id": LEARNER},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["derived_from_corpus"] is False
        assert [a["system"] for a in body["anchors"]] == ["CET-4", "IELTS"]
        assert body["history_state"] == "sufficient"

    def test_proficiency_context_insufficient_for_unknown_learner(self) -> None:
        client, _ = build_client()
        response = client.get(
            "/api/v1/wave2/learner/proficiency-context",
            params={"learner_id": "L-SYN-NO-RECORD"},
        )
        assert response.status_code == 200
        assert response.json()["history_state"] == "insufficient_history"

    def test_evidence_endpoint_with_provenance(self) -> None:
        client, _ = build_client()
        response = client.get("/api/v1/wave2/learner/evidence", params={"learner_id": LEARNER})
        assert response.status_code == 200
        body = response.json()
        assert body["excluded_count"] == 1
        evidence = {item["evidence"]["evidence_id"] for item in body["items"]}
        assert "E-101" in evidence
        assert "E-999" not in evidence
        first = body["items"][0]["evidence"]
        assert first["provenance"]["manifest_hash"] == "DEMO-MANIFEST-001"
        assert first["epistemic_status"] == "observed_descriptive"

    def test_router_is_importable_without_package_init(self) -> None:
        assert learner_api.router is not None
        paths = {route.path for route in learner_api.router.routes}
        assert {
            "/api/v1/wave2/learner/observations",
            "/api/v1/wave2/learner/observations/{observation_id}",
            "/api/v1/wave2/learner/difficulties",
            "/api/v1/wave2/learner/strengths",
            "/api/v1/wave2/learner/stable",
            "/api/v1/wave2/learner/proficiency-context",
            "/api/v1/wave2/learner/evidence",
        } <= paths

    def test_api_language_is_bounded_and_observation_only(self) -> None:
        client, _ = build_client()
        for path, params in (
            ("/api/v1/wave2/learner/observations", {"learner_id": LEARNER}),
            ("/api/v1/wave2/learner/difficulties", {"learner_id": LEARNER}),
            ("/api/v1/wave2/learner/strengths", {"learner_id": LEARNER}),
            ("/api/v1/wave2/learner/stable", {"learner_id": LEARNER}),
            ("/api/v1/wave2/learner/proficiency-context", {"learner_id": LEARNER}),
            ("/api/v1/wave2/learner/evidence", {"learner_id": LEARNER}),
        ):
            response = client.get(path, params=params)
            assert response.status_code == 200
            assert SCANNER.scan_mapping(response.json(), documentation=True) == []
