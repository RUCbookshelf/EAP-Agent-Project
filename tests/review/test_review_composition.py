"""Real composition smoke tests: the shared Review/Scheduling Foundation is
wired through the ONE composition root and served in the ONE API namespace
on isolated test databases."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request

from app.api.deps import get_review_evidence_lookup, get_review_service
from app.api.main import create_app
from app.config import Settings
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.models.schemas import utc_now
from app.review.protocols import ReviewEvidenceLookupProtocol


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def app(tmp_path):
    settings = Settings(
        database_path=tmp_path / "compose.db",
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
    return api


def test_composition_root_exposes_review_service(app):
    assert app.state.review_service is not None
    assert app.state.review_repository is not None
    assert app.state.review_learning_item_reader is not None
    identity = app.state.review_service.scheduler_identity()
    assert identity.implementation == "py-fsrs"


def test_router_round_trip_through_single_api(app):
    client = TestClient(app)
    response = client.post(
        "/api/v1/review/practice-activities",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "activity_type": "blank_fill",
            "status": "completed",
            "occurred_at": T0.isoformat(),
        },
    )
    assert response.status_code == 200
    activity = response.json()
    assert activity["activity_id"].startswith("PA")
    assert activity["evidence_kind"] == "practice"

    response = client.post(
        "/api/v1/review/events",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "practice_activity_id": activity["activity_id"],
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
            "learner_self_rating": "hard",
        },
    )
    assert response.status_code == 200
    event = response.json()
    assert event["review_event_id"].startswith("RE")
    assert event["system_provisional_rating"] == "good"
    assert event["learner_self_rating"] == "hard"
    assert event["final_scheduler_rating"] == "hard"
    assert event["scheduler_implementation"] == "py-fsrs"
    assert event["scheduler_version"] == "6.3.2"

    response = client.get("/api/v1/review/events/LI000001")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/api/v1/review/schedule/LI000001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduler_implementation"] == "py-fsrs"
    assert payload["state"]["due"] is not None


def test_router_rejects_missing_learning_item(app):
    client = TestClient(app)
    response = client.post(
        "/api/v1/review/events",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000999",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
        },
    )
    assert response.status_code == 404
    response = client.get("/api/v1/review/schedule/LI000999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# WU2 repair: downstream composition surface (LEARNER bridge/INT injection)
# ---------------------------------------------------------------------------


class _MirrorPracticeActivityStatus(StrEnum):
    """Structurally equivalent status enum (LEARNER bridge mirror)."""

    COMPLETED = "completed"


class _MirrorPracticeActivity(BaseModel):
    """Structurally equivalent to the LEARNER bridge ``PracticeActivityRecord``.

    Field names/types mirror the CORE ``PracticeActivity`` so the raw shared
    service/repository can consume the record through attribute access
    (``model_copy`` + ``status.value`` included), proving downstream
    injection without copying LEARNER semantics into CORE.
    """

    model_config = ConfigDict(extra="forbid")

    activity_id: str = "PA-PENDING"
    student_id: str = Field(min_length=1, max_length=100)
    learning_item_id: str = Field(min_length=1)
    activity_type: str = Field(min_length=1, max_length=100)
    source: str = "practice"
    status: _MirrorPracticeActivityStatus
    occurred_at: datetime
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    evaluator: str | None = None
    evaluation_id: str | None = None
    evaluator_version: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    evidence_kind: Literal["practice"] = "practice"
    authentic_evidence_status: Literal["insufficient", "present"] = (
        "insufficient"
    )
    limitations: list[str] = Field(default_factory=list)


@runtime_checkable
class _CoreReviewServicePort(Protocol):
    """Structural mirror of LEARNER's ``CoreReviewServicePort`` (WU2-D)."""

    rating_rule_version: str

    def scheduler_identity(self) -> Any: ...

    def record_practice_activity(self, activity: Any) -> Any: ...

    def record_review(
        self,
        *,
        student_id: str,
        learning_item_id: str,
        reviewed_at: datetime,
        system_provisional_rating: Any,
        learner_self_rating: Any | None = None,
        practice_activity_id: str | None = None,
        authentic_evidence_status: Literal["insufficient", "present"] = (
            "insufficient"
        ),
        provenance: dict[str, Any] | None = None,
    ) -> Any: ...


def _request_for(app) -> Request:
    return Request(
        {
            "type": "http",
            "app": app,
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


def test_deps_getters_resolve_composed_review_dependencies(app):
    """The canonical deps getters resolve the SAME composed instances."""
    request = _request_for(app)
    assert get_review_service(request) is app.state.review_service
    lookup = get_review_evidence_lookup(request)
    assert lookup is app.state.review_evidence_lookup
    assert isinstance(lookup, ReviewEvidenceLookupProtocol)


def test_review_service_satisfies_learner_core_review_service_port(app):
    """CORE ReviewService structurally satisfies the LEARNER bridge port."""
    assert isinstance(app.state.review_service, _CoreReviewServicePort)
    assert app.state.review_service.rating_rule_version == "rating-rule-v1.0.0"
    identity = app.state.review_service.scheduler_identity()
    assert identity.implementation == "py-fsrs"


def test_learner_shaped_practice_record_is_consumed_by_shared_service(app):
    """A structurally-equivalent (LEARNER-shaped) record persists through
    the shared CORE service/repository with no second store."""
    wave2 = SQLiteWave2Repository(app.state.repository._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000002",
            student_id="S1",
            category="grammar",
        )
    )
    record = _MirrorPracticeActivity(
        student_id="S1",
        learning_item_id="LI000002",
        activity_type="blank_fill",
        status=_MirrorPracticeActivityStatus.COMPLETED,
        occurred_at=T0,
        provenance={"bridge": "test-mirror", "bridge_version": "v0.0.0"},
    )
    saved = app.state.review_service.record_practice_activity(record)
    assert saved.activity_id.startswith("PA")
    assert saved.evidence_kind == "practice"
    assert app.state.review_evidence_lookup.owner_of(saved.activity_id) == "S1"


def test_composed_evidence_lookup_is_learner_scoped(app):
    """Shared evidence lookup resolves ownership and returns records only
    to the owner; unknown/non-review ids fail closed with None."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/review/practice-activities",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "activity_type": "blank_fill",
            "status": "completed",
            "occurred_at": T0.isoformat(),
        },
    )
    activity_id = response.json()["activity_id"]
    lookup = app.state.review_evidence_lookup
    assert lookup.owner_of(activity_id) == "S1"
    record = lookup.get_record("S1", activity_id)
    assert record is not None
    assert record.activity_id == activity_id
    assert record.evidence_kind == "practice"
    assert lookup.get_record("S2", activity_id) is None
    assert lookup.owner_of("PA-NOPE") is None
    assert lookup.owner_of("WT000001") is None
