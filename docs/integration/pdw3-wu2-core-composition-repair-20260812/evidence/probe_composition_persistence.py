"""Read-only probe evidence for CORE WU2 composition/persistence repair.

Builds the real composition on an isolated temp database, seeds one
LearningItem, records one practice activity and one review through the
shared service, then exercises the canonical deps getters and the shared
evidence lookup. Prints exact observable facts for the handoff.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.deps import get_review_evidence_lookup, get_review_service
from app.api.main import _build_services, create_app
from app.config import Settings
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review import ReviewService, ReviewEvidenceLookupProtocol
from app.review.protocols import ReviewEvidenceLookupProtocol as LookupPort


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


def _request(app):
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


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="wu2-probe-"))
    settings = Settings(
        database_path=tmp / "probe.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    app = create_app(settings)

    facts: dict[str, object] = {}
    facts["single_database_file"] = str(app.state.repository.path)
    facts["graph_keys"] = sorted(_build_services(settings).keys())
    facts["state_review_attrs"] = {
        "review_service": app.state.review_service is not None,
        "review_repository": app.state.review_repository is not None,
        "review_learning_item_reader": (
            app.state.review_learning_item_reader is not None
        ),
        "review_evidence_lookup": app.state.review_evidence_lookup is not None,
    }
    facts["deps_getters_resolve_state"] = (
        get_review_service(_request(app)) is app.state.review_service
        and get_review_evidence_lookup(_request(app))
        is app.state.review_evidence_lookup
    )
    facts["review_service_type"] = type(app.state.review_service).__name__
    facts["review_service_is_exported_from_app_review"] = isinstance(
        app.state.review_service, ReviewService
    )
    facts["evidence_lookup_satisfies_shared_protocol"] = isinstance(
        app.state.review_evidence_lookup, LookupPort
    )
    facts["evidence_lookup_satisfies_exported_protocol"] = isinstance(
        app.state.review_evidence_lookup, ReviewEvidenceLookupProtocol
    )

    wave2 = SQLiteWave2Repository(app.state.repository._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000001",
            student_id="S1",
            category="grammar",
        )
    )

    client = TestClient(app)
    activity = client.post(
        "/api/v1/review/practice-activities",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "activity_type": "blank_fill",
            "status": "completed",
            "occurred_at": T0.isoformat(),
        },
    ).json()
    event = client.post(
        "/api/v1/review/events",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "practice_activity_id": activity["activity_id"],
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
            "learner_self_rating": "hard",
        },
    ).json()

    lookup = app.state.review_evidence_lookup
    facts["owner_of_activity"] = lookup.owner_of(activity["activity_id"])
    facts["owner_of_event"] = lookup.owner_of(event["review_event_id"])
    facts["record_for_owner"] = lookup.get_record(
        "S1", activity["activity_id"]
    ).evidence_kind
    facts["record_cross_student_is_none"] = (
        lookup.get_record("S2", activity["activity_id"]) is None
    )
    facts["unknown_id_is_none"] = lookup.owner_of("WT000001") is None

    review_paths = sorted(
        {
            (route.path, ",".join(sorted(route.methods or [])))
            for route in app.routes
            if route.path.startswith("/api/v1/review/")
        }
    )
    facts["review_routes"] = review_paths
    facts["review_routes_count"] = len(review_paths)

    print(json.dumps(facts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
