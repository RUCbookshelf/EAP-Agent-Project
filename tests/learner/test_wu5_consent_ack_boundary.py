"""WU5 consent/acknowledgement read boundary regression (REPAIR).

Goal: ``PDW3-WU5-INT-CONSOLIDATED-WAVE3-INTEGRATION-GATE__REPAIR``.

The parent INT WU5 AMBER handoff proved a real cross-contract defect at the
one-application/one-SQLite composition boundary: composing the real L2 WU3
``LearnerConsentStorePort`` over the migration-16
``learner_acknowledgements`` table (the only architecture-compliant durable
home) stores durable ``tutor_consent`` rows in the same table that the
LEARNER ``SQLiteAcknowledgementRepository`` reads. The repository parsed
every row as an ``AcknowledgementRecord``, so
``AcknowledgementSourceKind('tutor_consent')`` raised ``ValueError`` and the
WU2 acknowledgement listing returned HTTP 500.

This file reproduces that boundary with the real SQLite composition (real
``Database``, real ``SQLiteAcknowledgementRepository``, real FastAPI app and
HTTP router) and requires the bounded LEARNER-owned read-side repair:
non-acknowledgement consent rows are never parsed as
``AcknowledgementRecord`` values, genuine acknowledgement rows remain
readable, durable tutor-consent data is preserved, and existing WU2 behavior
stays intact. No migration, schema change, or data deletion is involved.

The durable tutor-consent row is inserted with the exact column/value shape
used by the INT composition adapter (``SQLiteTutorConsentStore`` writing
``source_kind='tutor_consent'`` into migration 16), so this is the real
composed boundary, not a synthetic second store.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import app.api.main as main_module
from app.config import Settings
from app.database import Database
from app.infrastructure.sqlite.repositories.acknowledgement import (
    SQLiteAcknowledgementRepository,
)
from app.models.schemas import HistoryEvidence


LEARNER = "S001"


def _make_settings(db_path) -> Settings:
    return Settings(
        database_path=db_path,
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )


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


def _acknowledgement_payload(learner_id: str = LEARNER) -> dict:
    return {
        "learner_id": learner_id,
        "source_kind": "history_signal",
        "source_evidence_ids": ["H001"],
        "evidence_status": "verified",
        "epistemic_status": "observed_descriptive",
        "provenance": {
            "source_package": "learner-submissions-v1",
            "manifest_hash": "M-001",
            "processing_version": "analysis-v0.9.0",
        },
        "policy_version": "policy-v0.1.0",
        "record_version": "acknowledgement-record-v0.1.0",
        "acknowledgement_text": (
            "A descriptive metric comparison between two eligible "
            "submissions was recorded; observed evidence only."
        ),
        "consent": {
            "granted": True,
            "revoked": False,
            "scope": "learner_facing_acknowledgement",
            "consent_version": "learner-consent-v0.1.0",
            "granted_at": "2026-08-01T12:00:00Z",
            "learner_id": learner_id,
        },
    }


def _insert_tutor_consent_row(
    database: Database,
    learner_id: str = LEARNER,
    *,
    consent_id: str = "TC-S001-proactive_tutor-2026-08-01T12:00:00+00:00",
    granted_at: str = "2026-08-01T12:00:00+00:00",
) -> None:
    """Insert the durable tutor-consent row exactly as the composed L2 WU3
    ``SQLiteTutorConsentStore`` writes it into migration 16.

    The row family is ``source_kind='tutor_consent'`` with the minimal
    NOT-NULL columns; it is a non-acknowledgement row that shares the
    architecture-compliant durable home and must be preserved untouched.
    """

    consent_json = json.dumps(
        {
            "learner_id": learner_id,
            "granted": True,
            "revoked": False,
            "scope": "proactive_tutor",
            "consent_version": "learner-consent-v0.1.0",
            "granted_at": datetime.fromisoformat(granted_at),
        },
        sort_keys=True,
        default=str,
    )
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO learner_acknowledgements("
            " acknowledgement_id, learner_id, source_kind,"
            " source_evidence_ids_json, source_event_ids_json,"
            " evidence_status, epistemic_status, outcome_claim,"
            " provenance_json, record_version, acknowledgement_text,"
            " limitations_json, consent_json, recorded_at"
            ") VALUES (?, ?, 'tutor_consent', '[]', '[]',"
            " 'verified', 'observed_descriptive', 'none',"
            " '{}', 'learner-consent-v0.1.0',"
            " 'Explicit proactive-tutor consent snapshot.', '[]',"
            " ?, ?)",
            (
                consent_id,
                learner_id,
                consent_json,
                granted_at,
            ),
        )


def _composed_app(tmp_path, *, seed_learner: bool = True):
    """Build the real composition boundary over one SQLite file."""

    db_path = tmp_path / "wu5-boundary.db"
    settings = _make_settings(db_path)
    database = Database(db_path)
    database.initialize()
    if seed_learner:
        _seed_history_evidence(database)
    return main_module.create_app(settings, repository=database), database


class TestConsentAcknowledgementReadBoundary:
    """The real composed boundary: migration-16 rows of both families."""

    def test_listing_returns_200_excludes_consent_and_preserves_rows(
        self, tmp_path,
    ) -> None:
        app, database = _composed_app(tmp_path)
        store = app.state.acknowledgement_service.store
        assert isinstance(store, SQLiteAcknowledgementRepository)

        with TestClient(app) as client:
            # One genuine acknowledgement through the real service gates.
            created = client.post(
                f"/api/v1/students/{LEARNER}/acknowledgements",
                json=_acknowledgement_payload(),
            )
            assert created.status_code == 200
            acknowledgement_id = created.json()["record"]["acknowledgement_id"]

            # One durable tutor-consent row from the L2 WU3 consent store
            # family sharing migration 16.
            _insert_tutor_consent_row(database)

            # The listing must not raise ValueError / return HTTP 500 and
            # must exclude the non-acknowledgement consent row.
            response = client.get(
                f"/api/v1/students/{LEARNER}/acknowledgements"
            )
            assert response.status_code == 200
            items = response.json()["items"]
            assert len(items) == 1
            assert items[0]["acknowledgement_id"] == acknowledgement_id
            assert items[0]["source_kind"] == "history_signal"
            assert all(
                item["source_kind"] != "tutor_consent" for item in items
            )

            # Repository-level read is also discriminating and never raises.
            assert [r.acknowledgement_id for r in store.list_for_learner(
                LEARNER
            )] == [acknowledgement_id]

        # Durability: both row families remain in the same single SQLite
        # database; the consent row is preserved, not deleted.
        with database.connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM learner_acknowledgements "
                "WHERE learner_id=?",
                (LEARNER,),
            ).fetchone()[0]
            consent_rows = connection.execute(
                "SELECT COUNT(*) FROM learner_acknowledgements "
                "WHERE learner_id=? AND source_kind='tutor_consent'",
                (LEARNER,),
            ).fetchone()[0]
        assert total == 2
        assert consent_rows == 1

    def test_get_returns_none_for_tutor_consent_row(self, tmp_path) -> None:
        app, database = _composed_app(tmp_path)
        store = app.state.acknowledgement_service.store
        _insert_tutor_consent_row(database)

        # A tutor-consent row is not an AcknowledgementRecord: lookups by
        # its durable id return None instead of raising ValueError.
        assert (
            store.get("TC-S001-proactive_tutor-2026-08-01T12:00:00+00:00")
            is None
        )
        assert store.list_for_learner(LEARNER) == []
        with database.connect() as connection:
            preserved = connection.execute(
                "SELECT source_kind FROM learner_acknowledgements "
                "WHERE learner_id=?",
                (LEARNER,),
            ).fetchall()
        assert [row[0] for row in preserved] == ["tutor_consent"]

    def test_wu2_behavior_without_tutor_consent_stays_intact(
        self, tmp_path,
    ) -> None:
        app, _ = _composed_app(tmp_path)
        with TestClient(app) as client:
            created = client.post(
                f"/api/v1/students/{LEARNER}/acknowledgements",
                json=_acknowledgement_payload(),
            )
            assert created.status_code == 200

            # Control learner path from the INT smoke facts: no tutor
            # consents -> 200 with exactly the one acknowledgement.
            response = client.get(
                f"/api/v1/students/{LEARNER}/acknowledgements"
            )
            assert response.status_code == 200
            items = response.json()["items"]
            assert len(items) == 1
            assert items[0]["source_kind"] == "history_signal"


__all__ = []
