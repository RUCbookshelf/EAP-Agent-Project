"""WU2 API composition tests (RETRY-2 Worker D).

Covers the single composition-root wiring of the completed learner slices:

- ``_build_services`` returns the WU2 services and ``_apply_service_state``
  assigns them to ``app.state`` (``acknowledgement_service`` and
  ``practice_review_transfer``);
- Worker C's learner-owned acknowledgement router is included exactly once
  with no duplicate path/method pairs in the composed application;
- the Worker A practice/review bridge is wired as a typed optional injection
  boundary: no CORE review service is present on this branch, so both entry
  points fail closed with ``core_review_service_missing`` before any write;
- the Worker C acknowledgement service fails closed (503) until a production
  evidence lookup is composed, and the list endpoint returns an empty
  append-only listing;
- the existing ``JourneyService`` instance on ``app.state`` exposes Worker
  B's additive projections (``get_practice_history`` /
  ``get_authentic_application``) and fails closed for unknown students;
- one application, one process, one SQLite database, one API namespace:
  every state reader resolves through the single composition-root Database.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

import app.api.main as main_module
from app.api import deps
from app.api.routers import acknowledgement as acknowledgement_router
from app.config import Settings
from app.database import Database
from app.infrastructure.sqlite.repositories import (
    SQLiteAcknowledgementEvidenceLookup,
    SQLiteAcknowledgementRepository,
)
from app.learner.acknowledgement import AcknowledgementService
from app.learner.review_bridge import (
    PracticeActivityRecord,
    PracticeActivityStatus,
    Rating,
    ReviewBridgeError,
    ReviewRequestRecord,
)
from app.models.schemas import HistoryEvidence
from app.practice.review_transfer import PracticeReviewTransferOrchestrator


LEARNER = "S001"


def _make_settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wu2-composition.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )


def _make_app(tmp_path):
    return main_module.create_app(_make_settings(tmp_path))


def _route_pairs(app):
    pairs = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                pairs.append((method, path))
    return pairs


def _make_request(app) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "server": None,
        "client": None,
        "scheme": "http",
        "root_path": "",
    }
    request = Request(scope)
    request.scope["app"] = app
    return request


def _acknowledgement_payload(learner_id: str = LEARNER) -> dict:
    return {
        "learner_id": learner_id,
        "source_kind": "observed_evidence",
        "source_evidence_ids": ["EVID-1"],
        "evidence_status": "verified",
        "epistemic_status": "observed_descriptive",
        "provenance": {
            "source_package": "learner-submissions-v1",
            "manifest_hash": "M-001",
            "processing_version": "analysis-v0.9.0",
        },
        "policy_version": "policy-v0.1.0",
        "record_version": "acknowledgement-record-v0.1.0",
        "acknowledgement_text": "Observed practice evidence is acknowledged.",
        "consent": {
            "granted": True,
            "revoked": False,
            "scope": "learner_facing_acknowledgement",
            "consent_version": "learner-consent-v0.1.0",
            "granted_at": "2026-08-01T12:00:00Z",
            "learner_id": learner_id,
        },
    }


def _utc_now() -> datetime:
    return datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)


def _seed_history_evidence(database: Database, learner_id: str = LEARNER) -> None:
    """Insert one real, qualified history-evidence row (learner-owned)."""
    evidence = HistoryEvidence(
        history_evidence_id="H001",
        evidence_type="metric_change",
        description=(
            "Descriptive surface-metric comparison of two eligible "
            "submissions."
        ),
        supporting_submission_ids=["E000001", "E000002"],
        comparable_submission_count=2,
        confidence="low",
        limitation=(
            "This evidence does not establish language-ability improvement, "
            "decline, mastery, or regression."
        ),
    )
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO students(student_id, created_at, is_synthetic) "
            "VALUES (?, ?, ?)",
            (learner_id, "2026-08-01T09:00:00+00:00", 1),
        )
        connection.execute(
            "INSERT INTO history_evidence_registry("
            " student_id, history_evidence_id, snapshot_id, task_cluster_id,"
            " evidence_type, evidence_json, registry_version, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                learner_id,
                "H001",
                "LPS000001",
                "TC-1",
                "metric_change",
                evidence.model_dump_json(),
                "history-evidence-registry-v0.1",
                "2026-08-01T09:00:00+00:00",
            ),
        )


def _history_payload(learner_id: str = LEARNER) -> dict:
    payload = _acknowledgement_payload(learner_id)
    payload.update(
        {
            "source_kind": "history_signal",
            "source_evidence_ids": ["H001"],
            "acknowledgement_text": (
                "A descriptive metric comparison between two eligible "
                "submissions was recorded; observed evidence only."
            ),
        }
    )
    return payload


class FakeCoreReviewService:
    """Minimal recording fake implementing the typed CORE boundary."""

    rating_rule_version = "rating-rule-v1.0.0"

    def scheduler_identity(self) -> dict:
        return {
            "implementation": "py-fsrs",
            "library_version": "6.3.2",
            "parameters": {"w": [0.4], "enable_fuzz": False},
        }

    def record_practice_activity(self, activity: object) -> dict:
        return {"activity_id": "PA000001", "recorded": True}

    def record_review(self, **kwargs: object) -> dict:
        return {"review_event_id": "RE000001", "recorded": True}


# ---------------------------------------------------------------------------
# Service-graph keys and app-state assignment
# ---------------------------------------------------------------------------


class TestServiceGraphKeys:
    def test_build_services_returns_wu2_composition_keys(self, tmp_path):
        svc = main_module._build_services(_make_settings(tmp_path))
        assert "acknowledgement" in svc
        assert "practice_review_transfer" in svc

    def test_service_state_assigns_wu2_services(self, tmp_path):
        app = _make_app(tmp_path)
        assert isinstance(
            app.state.acknowledgement_service, AcknowledgementService
        )
        assert isinstance(
            app.state.practice_review_transfer, PracticeReviewTransferOrchestrator
        )

    def test_deps_expose_wu2_services_from_app_state(self, tmp_path):
        app = _make_app(tmp_path)
        request = _make_request(app)
        assert (
            deps.get_acknowledgement_service(request)
            is app.state.acknowledgement_service
        )
        assert (
            deps.get_practice_review_transfer(request)
            is app.state.practice_review_transfer
        )


# ---------------------------------------------------------------------------
# Single composition root / single authority
# ---------------------------------------------------------------------------


class TestSingleAuthority:
    def test_one_repository_database_authority(self, tmp_path):
        app = _make_app(tmp_path)
        database = app.state.repository
        assert app.state.practice_reader is app.state.practice_writer
        assert (
            app.state.practice_reader._connection_manager
            is database._connection_manager
        )
        assert (
            app.state.journey_service.projection_reader
            is app.state.practice_reader
        )
        assert (
            app.state.journey_service.student_reader
            is app.state.student_lookup
        )
        assert (
            app.state.student_lookup._connection_manager
            is database._connection_manager
        )

    def test_bridge_is_typed_optional_boundary_without_second_store(self, tmp_path):
        app = _make_app(tmp_path)
        orchestrator = app.state.practice_review_transfer
        # No CORE review service is integrated on this branch by default:
        # the injected boundary is None (typed optional) and the
        # orchestrator owns no store, repository, scheduler, or database of
        # its own.
        assert orchestrator._core is None

    def test_core_review_service_can_be_injected_through_typed_boundary(
        self, tmp_path,
    ):
        fake = FakeCoreReviewService()
        app = main_module.create_app(
            _make_settings(tmp_path), core_review_service=fake,
        )
        assert app.state.practice_review_transfer._core is fake

    def test_journey_service_exposes_additive_projections(self, tmp_path):
        app = _make_app(tmp_path)
        journey = app.state.journey_service
        assert callable(journey.get_practice_history)
        assert callable(journey.get_authentic_application)
        with pytest.raises(LookupError):
            journey.get_practice_history("S-NO-SUCH-STUDENT")
        with pytest.raises(LookupError):
            journey.get_authentic_application("S-NO-SUCH-STUDENT")


# ---------------------------------------------------------------------------
# Acknowledgement router registration (exactly once, no duplicates)
# ---------------------------------------------------------------------------


class TestAcknowledgementRouterRegistration:
    ACK_PAIRS = (
        ("POST", "/api/v1/students/{student_id}/acknowledgements"),
        ("GET", "/api/v1/students/{student_id}/acknowledgements"),
    )

    def test_router_module_in_business_routers_exactly_once(self):
        registrations = [
            module
            for module in main_module._BUSINESS_ROUTERS
            if module is acknowledgement_router
        ]
        assert registrations == [acknowledgement_router]

    def test_acknowledgement_paths_registered_exactly_once(self, tmp_path):
        app = _make_app(tmp_path)
        pairs = _route_pairs(app)
        for pair in self.ACK_PAIRS:
            assert pair in pairs
            assert pairs.count(pair) == 1, pair

    def test_no_duplicate_path_method_pairs_in_composed_app(self, tmp_path):
        app = _make_app(tmp_path)
        pairs = _route_pairs(app)
        assert len(pairs) == len(set(pairs))


# ---------------------------------------------------------------------------
# Fail-closed composition behavior
# ---------------------------------------------------------------------------


class TestFailClosedComposition:
    def test_practice_bridge_fails_closed_without_core_service(self, tmp_path):
        orchestrator = _make_app(tmp_path).state.practice_review_transfer
        activity = PracticeActivityRecord(
            student_id=LEARNER,
            learning_item_id="LI-1",
            activity_type="exercise",
            status=PracticeActivityStatus.COMPLETED,
            occurred_at=_utc_now(),
        )
        with pytest.raises(ReviewBridgeError) as exc_info:
            orchestrator.record_practice_activity(activity)
        assert exc_info.value.kind == "core_review_service_missing"

        review = ReviewRequestRecord(
            student_id=LEARNER,
            learning_item_id="LI-1",
            reviewed_at=_utc_now(),
            system_provisional_rating=Rating.GOOD,
        )
        with pytest.raises(ReviewBridgeError) as exc_info:
            orchestrator.record_review(review)
        assert exc_info.value.kind == "core_review_service_missing"

    def test_acknowledgement_post_fails_closed_for_unknown_evidence(
        self, tmp_path
    ):
        app = _make_app(tmp_path)
        store = app.state.acknowledgement_service.store
        assert isinstance(store, SQLiteAcknowledgementRepository)
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/students/{LEARNER}/acknowledgements",
                json=_acknowledgement_payload(),
            )
            assert response.status_code == 404
            body = response.json()
            detail = body.get("error", {}).get("detail", "")
            assert "evidence" in detail.casefold()
            assert store.list_for_learner(LEARNER) == []

    def test_acknowledgement_list_is_append_only_and_empty(self, tmp_path):
        app = _make_app(tmp_path)
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/students/{LEARNER}/acknowledgements"
            )
            assert response.status_code == 200
            assert response.json() == {
                "learner_id": LEARNER,
                "items": [],
            }


# ---------------------------------------------------------------------------
# Durable acknowledgement composition + Journey route registration
# ---------------------------------------------------------------------------


class TestDurableAcknowledgementComposition:
    def test_composition_uses_single_database_authority(self, tmp_path):
        app = _make_app(tmp_path)
        database = app.state.repository
        store = app.state.acknowledgement_service.store
        evidence = app.state.acknowledgement_service.evidence_port
        assert isinstance(store, SQLiteAcknowledgementRepository)
        assert isinstance(evidence, SQLiteAcknowledgementEvidenceLookup)
        assert (
            store._connection_manager is database._connection_manager
        )
        assert (
            evidence._connection_manager is database._connection_manager
        )

    def test_positive_history_acknowledgement_persists_and_survives_rebuild(
        self, tmp_path,
    ):
        db_path = tmp_path / "durable.db"
        settings = Settings(
            database_path=db_path,
            llm_provider="local",
            deepseek_api_key=None,
            deepseek_base_url="https://example.invalid",
            deepseek_model="deepseek-test",
        )
        database = Database(db_path)
        database.initialize()
        _seed_history_evidence(database)

        app = main_module.create_app(settings, repository=database)
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/students/{LEARNER}/acknowledgements",
                json=_history_payload(),
            )
            assert response.status_code == 200
            assert response.json()["record"]["source_kind"] == "history_signal"
            assert response.json()["record"]["learner_id"] == LEARNER

        # Durability: a fresh app over the SAME SQLite file still reads it.
        reopened = main_module.create_app(settings)
        with TestClient(reopened) as client:
            listing = client.get(
                f"/api/v1/students/{LEARNER}/acknowledgements"
            )
            assert listing.status_code == 200
            items = listing.json()["items"]
            assert len(items) == 1
            assert items[0]["source_kind"] == "history_signal"
            assert items[0]["acknowledgement_id"].startswith("ACK-")

    def test_journey_projection_routes_registered_exactly_once(self, tmp_path):
        app = _make_app(tmp_path)
        pairs = _route_pairs(app)
        for pair in (
            (
                "GET",
                "/api/v1/students/{student_id}/journey/practice-history",
            ),
            (
                "GET",
                "/api/v1/students/{student_id}/journey/"
                "authentic-application",
            ),
        ):
            assert pair in pairs
            assert pairs.count(pair) == 1, pair
        assert (
            "GET",
            "/api/v1/students/{student_id}/journey",
        ) in pairs


__all__ = []
