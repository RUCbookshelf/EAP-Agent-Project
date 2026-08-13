"""WU2 focused tests: learner-owned Journey projection routes (Repair Worker R).

Covers the two additive routes exposed through the existing learner-owned
Journey router:

- ``GET /api/v1/students/{student_id}/journey/practice-history`` — the
  practice-history (activity/evidence only) projection.
- ``GET /api/v1/students/{student_id}/journey/authentic-application`` — the
  authentic-writing application (separate channel) projection.

The existing ``GET /api/v1/students/{student_id}/journey`` route stays
unchanged. Routes are tested in an isolated app that includes the router with
the ``get_journey_service`` dependency overridden by a real ``JourneyService``
built on deterministic stub ports, so the real service projection behavior is
exercised end to end through FastAPI.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_journey_service
from app.api.routers import journey as journey_router
from app.journey.service import JourneyService


LEARNER = "S-JOURNEY"

PRACTICE_TARGET = {
    "practice_target_id": "PT000001",
    "student_id": LEARNER,
    "source_submission_id": 1,
    "source_analysis_run_id": "AR000001",
    "source_diagnosis_id": "D-001",
    "source_priority_id": "PRIO-FB000001-0",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "target_scope": "within_task",
    "diagnostic_gate_status": "selected",
    "diagnostic_version": "diagnostic-v0.6.1",
    "configuration_version": "config-v0.9.0",
    "status": "completed",
    "created_at": "2026-08-01T10:03:00+00:00",
    "updated_at": "2026-08-01T10:06:00+00:00",
}

EXERCISE_ATTEMPT = {
    "attempt_id": "EA000001",
    "exercise_id": "EX000001",
    "student_id": LEARNER,
    "attempt_number": 1,
    "response_text": "A valid response.",
    "status": "submitted",
    "timing_source": "server_timestamp",
    "hint_count": 0,
    "created_at": "2026-08-01T10:04:00+00:00",
}

PRACTICE_EVALUATION = {
    "evaluation_id": "PE000001",
    "attempt_id": "EA000001",
    "practice_target_id": "PT000001",
    "evaluation_method": "rule_based",
    "completion_status": "completed",
    "target_action_status": "candidate_detected",
    "evidence": ["E-001"],
    "confidence": "medium",
    "evaluator_version": "practice-evaluator-v0.9.0",
    "created_at": "2026-08-01T10:05:00+00:00",
}

AUTH_ORIGINAL = {
    "essay_id": 1,
    "student_id": LEARNER,
    "submitted_at": "2026-08-01T10:00:00+00:00",
    "revision_of_submission_id": None,
    "revision_group_id": None,
    "draft_stage": "first draft",
    "genre": "argumentative essay",
    "revision_sequence": None,
}

AUTH_REVISION = {
    "essay_id": 2,
    "student_id": LEARNER,
    "submitted_at": "2026-08-02T10:00:00+00:00",
    "revision_of_submission_id": 1,
    "revision_group_id": "RG000001",
    "draft_stage": "revised draft",
    "genre": "argumentative essay",
    "revision_sequence": 1,
}

AUTH_RESPONSE = {
    "response_id": "WTR000001",
    "student_id": LEARNER,
    "practice_target_id": "PT000001",
    "source_submission_id": 1,
    "later_submission_id": 2,
    "revision_group_id": "RG000001",
    "target_code": "lexical_repetition_local",
    "observed_status": "target_addressed",
    "comparison_version": "revision-comparison-v0.7.1",
    "evidence_ids": ["E-001"],
    "confidence": "limited",
    "limitations": ["A revision response is a candidate observation."],
    "created_at": "2026-08-02T10:05:00+00:00",
}

AUTH_TRANSFER = {
    "transfer_evidence_id": "TE000001",
    "student_id": LEARNER,
    "practice_target_id": "PT000001",
    "source_submission_id": 1,
    "later_submission_id": 3,
    "task_comparability": "comparable",
    "target_code": "lexical_repetition_local",
    "observed_status": "recurrence_signal",
    "history_evidence_ids": ["WTR000001"],
    "confidence": "limited",
    "limitations": ["One later observation is not proof of stable transfer."],
    "created_at": "2026-08-05T10:00:00+00:00",
}


class StubStudentReader:
    """Deterministic learner lookup; returns None for unknown students."""

    def __init__(self, learner):
        self.learner = learner
        self.calls: list[str] = []

    def get_student(self, student_id: str):
        self.calls.append("get_student")
        return self.learner


class StubProjectionReader:
    """Faithful fake of the pinned nine-method Journey projection port."""

    def __init__(self, **lists):
        self.lists = lists
        self.calls: list[str] = []

    def list_essays_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_essays_by_student")
        return list(self.lists.get("essays", []))

    def list_analysis_runs_for_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_analysis_runs_for_student")
        return list(self.lists.get("analyses", []))

    def list_feedback_records_for_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_feedback_records_for_student")
        return list(self.lists.get("feedbacks", []))

    def list_practice_targets(self, student_id: str) -> list[dict]:
        self.calls.append("list_practice_targets")
        return list(self.lists.get("targets", []))

    def list_exercise_instances(self, practice_target_id=None, student_id=None) -> list[dict]:
        self.calls.append("list_exercise_instances")
        return list(self.lists.get("exercises", []))

    def list_exercise_attempts_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_exercise_attempts_by_student")
        return list(self.lists.get("attempts", []))

    def list_practice_evaluations_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_practice_evaluations_by_student")
        return list(self.lists.get("evaluations", []))

    def list_within_task_responses(self, student_id: str) -> list[dict]:
        self.calls.append("list_within_task_responses")
        return list(self.lists.get("responses", []))

    def list_transfer_evidence_candidates(self, student_id: str) -> list[dict]:
        self.calls.append("list_transfer_evidence_candidates")
        return list(self.lists.get("transfers", []))


def _practice_lists() -> dict:
    return {
        "targets": [PRACTICE_TARGET],
        "attempts": [EXERCISE_ATTEMPT],
        "evaluations": [PRACTICE_EVALUATION],
    }


def _authentic_lists() -> dict:
    return {
        "essays": [AUTH_ORIGINAL, AUTH_REVISION],
        "responses": [AUTH_RESPONSE],
        "transfers": [AUTH_TRANSFER],
    }


def _make_app(service: JourneyService) -> FastAPI:
    """Isolated app that includes only the learner-owned Journey router."""
    app = FastAPI()
    app.include_router(journey_router.router)
    app.dependency_overrides[get_journey_service] = lambda: service
    return app


def _route_pairs(app: FastAPI) -> list[tuple[str, str]]:
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


JOURNEY_PATH = "/api/v1/students/{student_id}/journey"
PRACTICE_HISTORY_PATH = "/api/v1/students/{student_id}/journey/practice-history"
AUTHENTIC_APPLICATION_PATH = (
    "/api/v1/students/{student_id}/journey/authentic-application")

PROJECTION_KEYS = {
    "section", "learner_id", "available", "status", "counts", "limitations",
}


class TestProjectionRouteRegistration:
    """The two projection routes are registered exactly once with GET,
    alongside the existing journey route, with no duplicate path/method
    pairs."""

    def test_all_three_journey_routes_registered_exactly_once(self):
        service = JourneyService(StubStudentReader(None), StubProjectionReader())
        app = _make_app(service)

        pairs = _route_pairs(app)
        for expected in (
            ("GET", JOURNEY_PATH),
            ("GET", PRACTICE_HISTORY_PATH),
            ("GET", AUTHENTIC_APPLICATION_PATH),
        ):
            assert pairs.count(expected) == 1, expected
        assert len(pairs) == len(set(pairs)), pairs


class TestProjectionRouteGuards:
    """Unknown students get the router's canonical 404 before any projection
    read occurs."""

    def test_unknown_student_404_for_both_projection_routes(self):
        students = StubStudentReader(None)
        projections = StubProjectionReader(**_practice_lists(), **_authentic_lists())
        service = JourneyService(students, projections)
        client = TestClient(_make_app(service))

        response = client.get(f"/api/v1/students/NOPE/journey/practice-history")
        assert response.status_code == 404
        assert response.json()["detail"] == "Student not found."

        response = client.get(
            f"/api/v1/students/NOPE/journey/authentic-application")
        assert response.status_code == 404
        assert response.json()["detail"] == "Student not found."

        assert students.calls == ["get_student", "get_student"]
        assert projections.calls == []

    def test_known_student_404_guard_also_applies_to_existing_route(self):
        students = StubStudentReader(None)
        service = JourneyService(students, StubProjectionReader())
        client = TestClient(_make_app(service))

        response = client.get(f"/api/v1/students/NOPE/journey")
        assert response.status_code == 404


class TestPracticeHistoryRoute:
    """Known student: 200 with the practice-history projection section."""

    def test_route_returns_projection_section_for_known_student(self):
        students = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReader(**_practice_lists())
        service = JourneyService(students, projections)
        client = TestClient(_make_app(service))

        response = client.get(f"/api/v1/students/{LEARNER}/journey/practice-history")

        assert response.status_code == 200
        body = response.json()
        assert PROJECTION_KEYS <= body.keys()
        assert body["section"] == "practice_history"
        assert body["learner_id"] == LEARNER
        assert body["available"] is True
        assert body["status"] == "available"
        assert body["counts"] == {
            "practice_targets": 1,
            "exercise_attempts": 1,
            "practice_evaluations": 1,
            "review_events": 0,
        }
        assert [r["record_id"] for r in body["records"]] == [
            "PT000001", "EA000001", "PE000001",
        ]
        assert body == service.get_practice_history(LEARNER)


class TestAuthenticApplicationRoute:
    """Known student: 200 with the authentic-writing application section."""

    def test_route_returns_projection_section_for_known_student(self):
        students = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReader(**_authentic_lists())
        service = JourneyService(students, projections)
        client = TestClient(_make_app(service))

        response = client.get(
            f"/api/v1/students/{LEARNER}/journey/authentic-application")

        assert response.status_code == 200
        body = response.json()
        assert PROJECTION_KEYS <= body.keys()
        assert body["section"] == "authentic_application"
        assert body["learner_id"] == LEARNER
        assert body["available"] is True
        assert body["status"] == "present"
        assert body["counts"] == {
            "later_submissions": 1,
            "within_task_responses": 1,
            "later_task_evidence": 1,
        }
        assert [o["observation_id"] for o in body["observations"]] == [
            "2", "WTR000001", "TE000001",
        ]
        assert body == service.get_authentic_application(LEARNER)


class TestExistingJourneyRouteUnchanged:
    """The existing journey route keeps returning its unchanged payload."""

    def test_journey_route_payload_unchanged(self):
        students = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReader(**_authentic_lists())
        service = JourneyService(students, projections)
        client = TestClient(_make_app(service))

        response = client.get(f"/api/v1/students/{LEARNER}/journey")

        assert response.status_code == 200
        assert response.json() == service.get_journey(LEARNER)

    def test_empty_journey_payload_unchanged(self):
        students = StubStudentReader({"student_id": LEARNER})
        service = JourneyService(students, StubProjectionReader())
        client = TestClient(_make_app(service))

        response = client.get(f"/api/v1/students/{LEARNER}/journey")

        assert response.status_code == 200
        assert response.json() == service.get_journey(LEARNER)
