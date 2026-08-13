"""R1 regression + Case H API fail-closed tests through the REAL composition.

Asserts the final R1 behavior on the real stack (real SQLite file, real
composition root, real fsrs scheduler) via TestClient with
``raise_server_exceptions=False``: D3 (nonexistent practice_activity_id ->
404, no write), D4 (duplicate PA/RE ids -> 409, original row intact), D5
(cross-student event/activity -> 403, no write), C9 (naive/non-UTC reviewed_at
-> 422, no write), plus Case H API-layer 422 negatives (invalid rating,
invalid authentic_evidence_status, unknown fields, malformed provenance)
and the unchanged happy path (200, three rating channels, provenance).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.main import create_app
from app.config import Settings
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review.models import (
    Rating,
    ReviewEvent,
    PracticeActivity,
    PracticeActivityStatus,
    SchedulerIdentity,
    SchedulerStateSnapshot,
    SchedulingResult,
)
from app.review.protocols import ReviewRepositoryConflictError
from app.review.scheduler import FSRSSchedulerAdapter
from app.review.service import ReviewError


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def stack(tmp_path):
    """Seeded real composition: S1 owns LI000001, S2 owns LI000002."""
    settings = Settings(
        database_path=tmp_path / "failclosed.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    api = create_app(settings)
    wave2 = SQLiteWave2Repository(api.state.repository._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000001",
            student_id="S1",
            category="grammar",
        )
    )
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000002",
            student_id="S2",
            category="grammar",
        )
    )
    client = TestClient(api, raise_server_exceptions=False)
    return api, wave2, client


def _rows(api, table: str) -> list[dict]:
    with api.state.repository._connection_manager.connect() as connection:
        rows = connection.execute(f"SELECT * FROM {table}").fetchall()
    return [dict(row) for row in rows]


def _event(review_event_id: str = "RE000001", **overrides) -> ReviewEvent:
    values = dict(
        review_event_id=review_event_id,
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        learner_self_rating=Rating.HARD,
        final_scheduler_rating=Rating.HARD,
        rating_rule_version="rating-rule-v1.0.0",
        scheduler_implementation="py-fsrs",
        scheduler_version="6.3.2",
        state_before=SchedulerStateSnapshot(card_id=7, due=T0),
        state_after=SchedulerStateSnapshot(
            card_id=7, state="learning", step=1, due=T0
        ),
        scheduling_result=SchedulingResult(next_due=T0),
        provenance={"source": "regression", "batch": 1},
    )
    values.update(overrides)
    return ReviewEvent(**values)


def _state_row(review_event_id: str = "RE000001") -> dict[str, object]:
    identity = FSRSSchedulerAdapter().identity()
    return {
        "learning_item_id": "LI000001",
        "student_id": "S1",
        "identity": identity.model_dump(mode="json"),
        "state": SchedulerStateSnapshot(
            card_id=7, state="review", stability=2.3065, due=T0
        ).model_dump(mode="json"),
        "rating_rule_version": "rating-rule-v1.0.0",
        "updated_at": "2026-01-01T08:00:00+00:00",
        "last_review_event_id": review_event_id,
    }


def test_happy_path_unchanged_after_r1(stack):
    """Regression: the valid path still returns 200 with three rating
    channels and provenance, and both tables receive exactly one row."""
    api, _wave2, client = stack
    response = client.post(
        "/api/v1/review/events",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
            "learner_self_rating": "hard",
            "provenance": {"source": "regression", "round": 1},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["system_provisional_rating"] == "good"
    assert body["learner_self_rating"] == "hard"
    assert body["final_scheduler_rating"] == "hard"
    assert body["scheduler_implementation"] == "py-fsrs"
    assert body["scheduler_version"] == "6.3.2"
    assert body["provenance"] == {"source": "regression", "round": 1}
    assert len(_rows(api, "review_events")) == 1
    assert len(_rows(api, "learning_item_scheduler_states")) == 1


def test_nonexistent_practice_activity_maps_404_no_write(stack):
    """D3: nonexistent practice_activity_id -> 404, zero rows written."""
    api, _wave2, client = stack
    events_before = len(_rows(api, "review_events"))
    states_before = len(_rows(api, "learning_item_scheduler_states"))
    response = client.post(
        "/api/v1/review/events",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "practice_activity_id": "PA-NOPE",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
        },
    )
    assert response.status_code == 404
    assert "No durable PracticeActivity exists" in response.text
    assert len(_rows(api, "review_events")) == events_before
    assert len(_rows(api, "learning_item_scheduler_states")) == states_before
    with pytest.raises(ReviewError) as missing:
        api.state.review_service.record_review(
            student_id="S1",
            learning_item_id="LI000001",
            reviewed_at=T0,
            system_provisional_rating=Rating.GOOD,
            practice_activity_id="PA-NOPE",
        )
    assert missing.value.kind == "practice_activity_not_found"


def test_duplicate_practice_activity_maps_409_original_intact(stack):
    """D4: duplicate activity ID -> 409 and the original row is intact."""
    api, _wave2, client = stack
    payload = {
        "activity_id": "PA-OWNED",
        "student_id": "S1",
        "learning_item_id": "LI000001",
        "activity_type": "blank_fill",
        "status": "completed",
        "occurred_at": T0.isoformat(),
        "provenance": {"source": "regression", "batch": 1},
    }
    first = client.post("/api/v1/review/practice-activities", json=payload)
    payload["provenance"] = {"source": "regression", "batch": 2}
    second = client.post("/api/v1/review/practice-activities", json=payload)
    assert first.status_code == 200
    assert second.status_code == 409
    assert "already exists" in second.text
    rows = _rows(api, "practice_activities")
    owned = [r for r in rows if r["activity_id"] == "PA-OWNED"]
    assert len(rows) == 1
    assert len(owned) == 1
    assert json.loads(owned[0]["provenance_json"]) == {
        "source": "regression",
        "batch": 1,
    }
    with pytest.raises(ReviewError) as conflict:
        api.state.review_service.record_practice_activity(
            PracticeActivity(
                activity_id="PA-OWNED",
                student_id="S1",
                learning_item_id="LI000001",
                activity_type="blank_fill",
                status=PracticeActivityStatus.COMPLETED,
                occurred_at=T0,
                provenance={"source": "regression", "batch": 2},
            )
        )
    assert conflict.value.kind == "practice_activity_already_exists"


def test_duplicate_review_event_id_conflict_original_intact(stack):
    """D4: duplicate review-event ID -> stable conflict signal; the original
    durable row is not replaced (append-only evidence)."""
    api, _wave2, _client = stack
    repository = api.state.review_repository
    first = repository.record_review_event(
        _event("RE-REP0-DUP"), _state_row("RE-REP0-DUP")
    )
    assert first.review_event_id == "RE-REP0-DUP"
    with pytest.raises(ReviewRepositoryConflictError) as conflict:
        repository.record_review_event(
            _event("RE-REP0-DUP"), _state_row("RE-REP0-DUP")
        )
    assert conflict.value.kind == "review_event_already_exists"
    rows = [
        r
        for r in _rows(api, "review_events")
        if r["review_event_id"] == "RE-REP0-DUP"
    ]
    assert len(rows) == 1
    assert json.loads(rows[0]["provenance_json"]) == {
        "source": "regression",
        "batch": 1,
    }


def test_cross_student_event_maps_403_no_write(stack):
    """D5: S2 recording a review against S1's LearningItem -> 403, no write."""
    api, _wave2, client = stack
    events_before = len(_rows(api, "review_events"))
    response = client.post(
        "/api/v1/review/events",
        json={
            "student_id": "S2",
            "learning_item_id": "LI000001",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
        },
    )
    assert response.status_code == 403
    assert "does not match the owner" in response.text
    assert len(_rows(api, "review_events")) == events_before
    with pytest.raises(ReviewError) as mismatch:
        api.state.review_service.record_review(
            student_id="S2",
            learning_item_id="LI000001",
            reviewed_at=T0,
            system_provisional_rating=Rating.GOOD,
        )
    assert mismatch.value.kind == "learning_item_owner_mismatch"


def test_event_linking_other_students_activity_maps_403_no_write(stack):
    """D5: event referencing another student's activity -> 403, no write."""
    api, _wave2, client = stack
    other = client.post(
        "/api/v1/review/practice-activities",
        json={
            "activity_id": "PA-S2",
            "student_id": "S2",
            "learning_item_id": "LI000002",
            "activity_type": "blank_fill",
            "status": "completed",
            "occurred_at": T0.isoformat(),
        },
    )
    assert other.status_code == 200
    events_before = len(_rows(api, "review_events"))
    response = client.post(
        "/api/v1/review/events",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "practice_activity_id": "PA-S2",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
        },
    )
    assert response.status_code == 403
    assert "belongs to student" in response.text
    assert len(_rows(api, "review_events")) == events_before
    with pytest.raises(ReviewError) as mismatch:
        api.state.review_service.record_review(
            student_id="S1",
            learning_item_id="LI000001",
            reviewed_at=T0,
            system_provisional_rating=Rating.GOOD,
            practice_activity_id="PA-S2",
        )
    assert mismatch.value.kind == "practice_activity_owner_mismatch"


def test_mismatched_activity_owner_maps_403_no_write(stack):
    """D5: practice activity whose student does not own the LearningItem
    -> 403, no write."""
    api, _wave2, client = stack
    activities_before = len(_rows(api, "practice_activities"))
    response = client.post(
        "/api/v1/review/practice-activities",
        json={
            "activity_id": "PA-WRONG-OWNER",
            "student_id": "S2",
            "learning_item_id": "LI000001",
            "activity_type": "blank_fill",
            "status": "completed",
            "occurred_at": T0.isoformat(),
        },
    )
    assert response.status_code == 403
    assert "does not match the owner" in response.text
    assert len(_rows(api, "practice_activities")) == activities_before
    with pytest.raises(ReviewError) as mismatch:
        api.state.review_service.record_practice_activity(
            PracticeActivity(
                activity_id="PA-WRONG-OWNER",
                student_id="S2",
                learning_item_id="LI000001",
                activity_type="blank_fill",
                status=PracticeActivityStatus.COMPLETED,
                occurred_at=T0,
            )
        )
    assert mismatch.value.kind == "practice_activity_owner_mismatch"


def _events_payload(**overrides) -> dict:
    payload = {
        "student_id": "S1",
        "learning_item_id": "LI000001",
        "reviewed_at": T0.isoformat(),
        "system_provisional_rating": "good",
    }
    payload.update(overrides)
    return payload


def test_naive_reviewed_at_maps_422_no_write(stack):
    """C9: naive datetime -> 422 at the router boundary, no write."""
    api, _wave2, client = stack
    events_before = len(_rows(api, "review_events"))
    response = client.post(
        "/api/v1/review/events",
        json=_events_payload(reviewed_at="2026-01-01T08:00:00"),
    )
    assert response.status_code == 422
    assert len(_rows(api, "review_events")) == events_before


def test_non_utc_reviewed_at_maps_422_no_write(stack):
    """C9: non-UTC datetime -> 422 at the router boundary, no write."""
    api, _wave2, client = stack
    events_before = len(_rows(api, "review_events"))
    response = client.post(
        "/api/v1/review/events",
        json=_events_payload(reviewed_at="2026-01-01T08:00:00+08:00"),
    )
    assert response.status_code == 422
    assert len(_rows(api, "review_events")) == events_before


def test_invalid_rating_maps_422_no_write(stack):
    """Case H: invalid rating value -> 422 at the router boundary."""
    api, _wave2, client = stack
    events_before = len(_rows(api, "review_events"))
    response = client.post(
        "/api/v1/review/events",
        json=_events_payload(system_provisional_rating="excellent"),
    )
    assert response.status_code == 422
    assert len(_rows(api, "review_events")) == events_before
    response = client.post(
        "/api/v1/review/events",
        json=_events_payload(learner_self_rating="fine"),
    )
    assert response.status_code == 422
    assert len(_rows(api, "review_events")) == events_before


def test_invalid_authentic_evidence_status_maps_422_no_write(stack):
    """Case H: invalid authentic_evidence_status -> 422, no write."""
    api, _wave2, client = stack
    events_before = len(_rows(api, "review_events"))
    response = client.post(
        "/api/v1/review/events",
        json=_events_payload(authentic_evidence_status="proven"),
    )
    assert response.status_code == 422
    assert len(_rows(api, "review_events")) == events_before


def test_unknown_fields_map_422_no_write(stack):
    """Case H: unknown fields rejected at the router boundary (no write)."""
    api, _wave2, client = stack
    events_before = len(_rows(api, "review_events"))
    response = client.post(
        "/api/v1/review/events",
        json=_events_payload(mastery_score=0.9),
    )
    assert response.status_code == 422
    assert len(_rows(api, "review_events")) == events_before
    activities_before = len(_rows(api, "practice_activities"))
    response = client.post(
        "/api/v1/review/practice-activities",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "activity_type": "blank_fill",
            "status": "completed",
            "occurred_at": T0.isoformat(),
            "proficiency_score": 0.9,
        },
    )
    assert response.status_code == 422
    assert len(_rows(api, "practice_activities")) == activities_before


def test_malformed_provenance_maps_422_no_write(stack):
    """Case H: provenance must be an object; list/string payloads -> 422 at
    the router boundary and no write on either endpoint."""
    api, _wave2, client = stack
    events_before = len(_rows(api, "review_events"))
    response = client.post(
        "/api/v1/review/events",
        json=_events_payload(provenance=["malformed"]),
    )
    assert response.status_code == 422
    assert len(_rows(api, "review_events")) == events_before
    response = client.post(
        "/api/v1/review/events",
        json=_events_payload(provenance="raw-string"),
    )
    assert response.status_code == 422
    assert len(_rows(api, "review_events")) == events_before
    activities_before = len(_rows(api, "practice_activities"))
    response = client.post(
        "/api/v1/review/practice-activities",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "activity_type": "blank_fill",
            "status": "completed",
            "occurred_at": T0.isoformat(),
            "provenance": ["malformed"],
        },
    )
    assert response.status_code == 422
    assert len(_rows(api, "practice_activities")) == activities_before


def test_service_level_naive_datetime_kind_is_stable(stack):
    """C9 service path: naive datetime raises the stable ReviewError kind
    before any work."""
    api, _wave2, _client = stack
    with pytest.raises(ReviewError) as naive:
        api.state.review_service.record_review(
            student_id="S1",
            learning_item_id="LI000001",
            reviewed_at=datetime(2026, 1, 1, 8, 0, 0),
            system_provisional_rating=Rating.GOOD,
        )
    assert naive.value.kind == "invalid_reviewed_at"
    assert len(_rows(api, "review_events")) == 0


def test_deps_fail_closed_503_when_review_dependencies_not_composed():
    """WU2: the canonical deps getters fail closed (503) on any app whose
    composition root has not wired the shared review dependencies."""
    from fastapi import FastAPI

    from app.api.deps import get_review_evidence_lookup, get_review_service

    probe = FastAPI()
    request = Request(
        {
            "type": "http",
            "app": probe,
            "method": "GET",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "root_path": "",
        }
    )
    with pytest.raises(HTTPException) as missing_service:
        get_review_service(request)
    assert missing_service.value.status_code == 503
    with pytest.raises(HTTPException) as missing_lookup:
        get_review_evidence_lookup(request)
    assert missing_lookup.value.status_code == 503
