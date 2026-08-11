"""F-1 shared-repository consumption and fallback coverage (Goal
PDW2-WU2-F1-LEARNER-REPOSITORY-CONSUME).

The LEARNER ``learner_api`` dependency must consume the CORE-composed shared
wave2 store (``request.app.state.wave2_repository``) when present, falling
back to the local in-memory repository only for standalone test contexts.
Because the CORE ``SQLiteWave2Repository`` is not importable on the LEARNER
branch, these tests exercise the consumption against a faithful in-memory
fake of the shared store's observation family interface
(``save_learning_observation`` / ``get_learning_observation`` /
``list_learning_observations`` with generated ``LO`` ids), plus the
fallback path and payload round-trip fidelity.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.wave2_modules import learner_api
from app.learner.wave2.models import ObservationType
from app.learner.wave2.repository import ObservationRepository
from app.learner.wave2.services import LongitudinalLearnerService
from tests.learner.wave2_helpers import (
    make_observation,
    make_occurrence,
    utc,
)


class FakeSharedObservation:
    """Duck-typed row returned by the fake shared store (CORE-shaped)."""

    def __init__(self, **values) -> None:
        self.__dict__.update(values)


class FakeSharedWave2Store:
    """In-memory fake of the CORE ``SQLiteWave2Repository`` observation family.

    Mirrors the CORE contract used by the LEARNER adapter:
    ``save_learning_observation`` assigns a generated ``LO`` id,
    ``list_learning_observations`` filters by student id and observation
    type and orders by ``last_observed_at`` then id.
    """

    def __init__(self) -> None:
        self._rows: dict[str, FakeSharedObservation] = {}
        self._seq = 0

    def save_learning_observation(self, observation) -> FakeSharedObservation:
        self._seq += 1
        observation_id = f"LO{self._seq:06d}"
        row = FakeSharedObservation(
            observation_id=observation_id,
            student_id=observation.student_id,
            observation_type=observation.observation_type,
            evidence_refs=list(observation.evidence_refs),
            task_id=observation.task_id,
            context=dict(observation.context),
            occurrence_count=observation.occurrence_count,
            first_observed_at=observation.first_observed_at,
            last_observed_at=observation.last_observed_at,
            recency=observation.recency,
            revision_response=dict(observation.revision_response),
            limitations=list(observation.limitations),
            created_at=observation.created_at,
        )
        self._rows[observation_id] = row
        return row

    def get_learning_observation(self, observation_id: str):
        return self._rows.get(observation_id)

    def list_learning_observations(
        self, student_id: str, observation_type: str | None = None,
    ) -> list[FakeSharedObservation]:
        rows = [
            row for row in self._rows.values()
            if row.student_id == student_id
            and (observation_type is None
                 or row.observation_type == observation_type)
        ]
        return sorted(
            rows,
            key=lambda row: (row.last_observed_at or "", row.observation_id),
        )


def build_client(shared_store=None) -> tuple[TestClient, FastAPI]:
    """Router-only app; the real dependency resolves the shared store when
    present, otherwise the local fallback."""

    app = FastAPI()
    app.include_router(learner_api.router)
    if shared_store is not None:
        app.state.wave2_repository = shared_store
    return TestClient(app), app


LEARNER = "L-SHARED-001"


def seed_shared_observation(
    store: FakeSharedWave2Store, record,
) -> FakeSharedObservation:
    """Seed a shared row exactly as the adapter would (payload in context)."""
    return store.save_learning_observation(learner_api._SharedLearningObservation(
        student_id=record.learner_id,
        observation_type=record.observation_type.value,
        evidence_refs=[
            occurrence.evidence_ref for occurrence in record.occurrences
        ],
        task_id=None,
        context={learner_api._LEARNER_RECORD_PAYLOAD_KEY: record.model_dump(mode="json")},
        occurrence_count=len(record.occurrences),
        first_observed_at=record.occurrences[0].observed_at.isoformat(),
        last_observed_at=record.occurrences[-1].observed_at.isoformat(),
        recency="unknown",
        revision_response={},
        limitations=list(record.limitations),
    ))


class TestSharedStoreConsumption:
    def test_dependency_consumes_shared_store_when_present(self) -> None:
        store = FakeSharedWave2Store()
        client, _ = build_client(shared_store=store)
        # A shared row written by any consumer (e.g. another department)
        # must be visible through the learner API.
        seed_shared_observation(store, make_observation(
            "SVA-01", LEARNER, ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [
                make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1)),
                make_occurrence("OC-2", "E-102", "T-02", utc(2026, 7, 15)),
            ],
        ))
        response = client.get(
            "/api/v1/wave2/learner/observations",
            params={"learner_id": LEARNER},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["history_state"] == "sufficient"
        sva = next(
            item for item in body["items"]
            if item["observation_id"] == "SVA-01"
        )
        assert sva["code"] == "SVA-001"
        assert sva["occurrence_count"] == 2
        assert sva["contexts"] == ["T-01", "T-02"]

    def test_shared_rows_without_learner_payload_are_skipped(self) -> None:
        store = FakeSharedWave2Store()
        store.save_learning_observation(learner_api._SharedLearningObservation(
            student_id="L-FOREIGN-1",
            observation_type="strength",
            evidence_refs=["E-1"],
            task_id=None,
            context={},  # no LEARNER payload (written by another consumer)
            occurrence_count=1,
            first_observed_at="2026-07-01T09:00:00+00:00",
            last_observed_at="2026-07-01T09:00:00+00:00",
            recency="unknown",
            revision_response={},
            limitations=["shared row without learner payload"],
        ))
        client, _ = build_client(shared_store=store)
        response = client.get(
            "/api/v1/wave2/learner/observations",
            params={"learner_id": "L-FOREIGN-1"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["history_state"] == "insufficient_history"

    def test_observation_type_filter_delegates_to_shared_store(self) -> None:
        store = FakeSharedWave2Store()
        seed_shared_observation(store, make_observation(
            "SVA-01", LEARNER, ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [
                make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1)),
                make_occurrence("OC-2", "E-102", "T-02", utc(2026, 7, 15)),
            ],
        ))
        client, _ = build_client(shared_store=store)
        difficulties = client.get(
            "/api/v1/wave2/learner/difficulties",
            params={"learner_id": LEARNER},
        ).json()
        strengths = client.get(
            "/api/v1/wave2/learner/strengths",
            params={"learner_id": LEARNER},
        ).json()
        assert {item["observation_id"] for item in difficulties["items"]} == {
            "SVA-01",
        }
        assert strengths["items"] == []

    def test_shared_store_reused_across_requests(self) -> None:
        store = FakeSharedWave2Store()
        client, _ = build_client(shared_store=store)
        # First request sees nothing; after a shared write, a later request
        # sees the row (no per-request in-memory disconnect).
        empty = client.get(
            "/api/v1/wave2/learner/observations",
            params={"learner_id": LEARNER},
        )
        assert empty.json()["history_state"] == "insufficient_history"
        seed_shared_observation(store, make_observation(
            "SVA-01", LEARNER, ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1))],
        ))
        later = client.get(
            "/api/v1/wave2/learner/observations",
            params={"learner_id": LEARNER},
        )
        assert later.json()["history_state"] == "sufficient"


class TestFallback:
    def test_fallback_local_repository_when_shared_store_absent(self) -> None:
        client, _ = build_client(shared_store=None)
        response = client.get(
            "/api/v1/wave2/learner/observations",
            params={"learner_id": "L-NO-SHARED"},
        )
        assert response.status_code == 200
        assert response.json()["history_state"] == "insufficient_history"

    def test_default_service_is_used_when_shared_store_absent(self) -> None:
        from fastapi import Request

        app = FastAPI()
        app.include_router(learner_api.router)
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "app": app,
        })
        service = learner_api.get_learner_model_service(request)
        assert service is learner_api._DEFAULT_LEARNER_SERVICE

    def test_existing_local_seeding_still_visible_without_shared_store(self) -> None:
        service = learner_api._DEFAULT_LEARNER_SERVICE
        service.record_observation(make_observation(
            "SVA-01", LEARNER, ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1))],
        ))
        try:
            client, _ = build_client(shared_store=None)
            response = client.get(
                "/api/v1/wave2/learner/observations",
                params={"learner_id": LEARNER},
            )
            assert response.status_code == 200
            ids = {
                item["observation_id"]
                for item in response.json()["items"]
            }
            assert "SVA-01" in ids
        finally:
            # Restore the module-level default to its empty state so other
            # test modules are not polluted.
            from app.learner.wave2.repository import InMemoryObservationRepository
            learner_api._DEFAULT_LEARNER_SERVICE = LongitudinalLearnerService(
                InMemoryObservationRepository()
            )


class TestAdapterFidelity:
    def test_round_trip_preserves_full_learner_record(self) -> None:
        store = FakeSharedWave2Store()
        adapter = learner_api.SharedObservationRepository(store)
        original = make_observation(
            "SVA-01", LEARNER, ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [
                make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1)),
                make_occurrence("OC-2", "E-102", "T-02", utc(2026, 7, 15)),
            ],
        )
        adapter.save_observation(original)
        loaded = adapter.get_observation(LEARNER, "SVA-01")
        assert loaded is not None
        assert loaded == original
        listed = adapter.list_observations(LEARNER)
        assert listed == [original]

    def test_adapter_satisfies_observation_repository_protocol(self) -> None:
        adapter = learner_api.SharedObservationRepository(FakeSharedWave2Store())
        assert isinstance(adapter, ObservationRepository)

    def test_learner_only_families_stay_local_within_adapter(self) -> None:
        store = FakeSharedWave2Store()
        adapter = learner_api.SharedObservationRepository(store)
        from tests.learner.wave2_helpers import make_proficiency_context

        adapter.save_proficiency_context(make_proficiency_context(LEARNER))
        context = adapter.get_proficiency_context(LEARNER)
        assert context is not None
        assert context.learner_id == LEARNER
        # Nothing in the shared store changed (LEARNER-only family).
        assert store.list_learning_observations(LEARNER) == []
