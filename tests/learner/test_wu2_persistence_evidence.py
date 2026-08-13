"""WU2 repair worker P persistence + qualified evidence lookup tests.

Goal: ``PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812``.

Covers:
- Migration 16 (``learner_acknowledgement_persistence``, global ledger
  Option A; Migration 15 is CORE-owned ``review_scheduling_foundation``):
  fresh upgrade, 14->16 upgrade, idempotent re-upgrade, ledger-only rollback
  16->15->14 that
  preserves data, and re-upgrade that preserves the row.
- Durable append-only store: append/get/list, learner scoping, close/reopen
  persistence on the SAME SQLite file, duplicate-id and duplicate-evidence-
  set conflicts with no write.
- Qualified evidence lookup: history registry -> HistoryEvidence; completed
  practice evaluation -> PracticeProvenanceRecord; a positive PRACTICE_RESULT
  acknowledgement succeeds and persists; a ``submitted`` attempt fails
  closed; learning-items ownership resolves; absent observed-evidence and
  absent CORE review-events tables fail closed.
- Service link gates: unknown/mismatched learning item, unknown practice
  activity link, review link fails closed while the CORE table is absent,
  invalid runtime ``authentic_evidence_status`` -- all with no store write.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from app.database import Database, LATEST_MIGRATION_VERSION, rollback, upgrade
from app.database.migrations import MIGRATIONS
from app.infrastructure.sqlite import SQLiteConnectionManager
from app.infrastructure.sqlite.repositories.acknowledgement import (
    SQLiteAcknowledgementEvidenceLookup,
    SQLiteAcknowledgementRepository,
)
from app.learner.acknowledgement import (
    AcknowledgementError,
    AcknowledgementService,
    AcknowledgementStoreConflictError,
)
from app.learner.acknowledgement_contracts import (
    ACKNOWLEDGEMENT_CONSENT_SCOPE,
    AcknowledgementRecord,
    AcknowledgementRequest,
    AcknowledgementSourceKind,
    LearnerConsent,
)
from app.learner.evidence import ProvenanceChain
from app.learner.evidence import EvidenceAdmissionStatus, ExposureClass, ObservedEvidence
from app.learner.practice_provenance import PracticeProvenanceRecord
from app.models.schemas import HistoryEvidence
from app.shared.vocabularies import EpistemicStatus, EvidenceStatus


NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
LEARNER = "S001"
OTHER = "S002"
MIGRATION_15_NAME = "review_scheduling_foundation"
MIGRATION_16_NAME = "learner_acknowledgement_persistence"


def utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def seed_students(connection: sqlite3.Connection, *learner_ids: str) -> None:
    for learner_id in learner_ids:
        connection.execute(
            "INSERT INTO students(student_id, created_at, is_synthetic)"
            " VALUES (?, '2026-01-01T00:00:00+00:00', 0)",
            (learner_id,),
        )


def make_provenance(**overrides: Any) -> ProvenanceChain:
    values: dict[str, Any] = {
        "source_package": "learner-submissions-v1",
        "manifest_hash": "M-001",
        "processing_version": "analysis-v0.9.0",
    }
    values.update(overrides)
    return ProvenanceChain(**values)


def make_consent(**overrides: Any) -> LearnerConsent:
    values: dict[str, Any] = {
        "granted": True,
        "revoked": False,
        "scope": ACKNOWLEDGEMENT_CONSENT_SCOPE,
        "consent_version": "learner-consent-v0.1.0",
        "granted_at": utc("2026-08-10T08:00:00+00:00"),
        "learner_id": LEARNER,
    }
    values.update(overrides)
    return LearnerConsent(**values)


CLEAN_TEXT = (
    "Connective use appeared in 3 of 5 eligible submissions across the "
    "observed span; this is descriptive observed evidence only."
)


def make_record(**overrides: Any) -> AcknowledgementRecord:
    values: dict[str, Any] = {
        "acknowledgement_id": "ACK-persistence-1",
        "learner_id": LEARNER,
        "source_kind": AcknowledgementSourceKind.OBSERVED_EVIDENCE,
        "source_evidence_ids": ["E-101"],
        "source_event_ids": ["SEV-101"],
        "learning_item_id": None,
        "authentic_evidence_status": None,
        "practice_activity_id": None,
        "review_event_id": None,
        "evidence_status": EvidenceStatus.VERIFIED,
        "provenance": make_provenance(),
        "policy_version": "feedback-policy-v0.1.0",
        "model_version": None,
        "config_version": None,
        "record_version": "acknowledgement-record-v0.1.0",
        "acknowledgement_text": CLEAN_TEXT,
        "consent": make_consent(),
        "observed_span_start": utc("2026-08-01T00:00:00+00:00"),
        "observed_span_end": utc("2026-08-11T00:00:00+00:00"),
        "recorded_at": NOW,
    }
    values.update(overrides)
    return AcknowledgementRecord(**values)


def make_request(**overrides: Any) -> AcknowledgementRequest:
    values: dict[str, Any] = {
        "learner_id": LEARNER,
        "source_kind": AcknowledgementSourceKind.OBSERVED_EVIDENCE,
        "source_evidence_ids": ["E-101"],
        "evidence_status": EvidenceStatus.VERIFIED,
        "provenance": make_provenance(),
        "policy_version": "feedback-policy-v0.1.0",
        "record_version": "acknowledgement-record-v0.1.0",
        "acknowledgement_text": CLEAN_TEXT,
        "consent": make_consent(),
        "observed_span_start": utc("2026-08-01T00:00:00+00:00"),
        "observed_span_end": utc("2026-08-11T00:00:00+00:00"),
    }
    values.update(overrides)
    return AcknowledgementRequest(**values)


def build_service(
    store: SQLiteAcknowledgementRepository,
    lookup: SQLiteAcknowledgementEvidenceLookup,
) -> AcknowledgementService:
    return AcknowledgementService(
        store,
        evidence_port=lookup,
        now=lambda: NOW,
    )


def seed_history_evidence(
    connection: sqlite3.Connection, learner_id: str, evidence_id: str = "H001",
) -> None:
    evidence = HistoryEvidence(
        history_evidence_id=evidence_id,
        evidence_type="metric_change",
        description=(
            "Descriptive surface-metric comparison of two eligible submissions."
        ),
        supporting_submission_ids=["E000001", "E000002"],
        comparable_submission_count=2,
        confidence="low",
        limitation=(
            "This evidence does not establish language-ability improvement, "
            "decline, mastery, or regression."
        ),
    )
    connection.execute(
        "INSERT INTO history_evidence_registry("
        " history_evidence_id, student_id, task_cluster_id, evidence_type,"
        " evidence_json, registry_version, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            evidence_id,
            learner_id,
            "TC-1",
            "metric_change",
            evidence.model_dump_json(),
            "history-evidence-registry-v0.1.0",
            "2026-08-01T00:00:00+00:00",
        ),
    )


def seed_practice_chain(
    connection: sqlite3.Connection,
    learner_id: str,
    *,
    attempt_status: str = "submitted",
    completion_status: str | None = "completed",
    evaluator_version: str = "practice-evaluator-v0.9.0",
) -> None:
    """Seed practice_targets -> exercise_instances -> exercise_attempts ->
    practice_evaluations rows with stored JSON payloads."""
    connection.execute(
        "INSERT INTO practice_targets("
        " practice_target_id, student_id, source_submission_id,"
        " source_diagnosis_id, target_code, target_label, status, created_at,"
        " target_json) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)",
        (
            "PT000001",
            learner_id,
            1,
            "D001",
            "connectives",
            "Connective use",
            "2026-08-01T00:00:00+00:00",
            json.dumps({"target_code": "connectives"}),
        ),
    )
    connection.execute(
        "INSERT INTO exercise_instances("
        " exercise_id, practice_target_id, student_id, exercise_type,"
        " created_at, instance_json) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "EX000001",
            "PT000001",
            learner_id,
            "guided_sentence_rewrite",
            "2026-08-01T00:00:00+00:00",
            json.dumps(
                {"exercise_version": "exercise-v0.9.0", "exercise_type": "guided_sentence_rewrite"}
            ),
        ),
    )
    connection.execute(
        "INSERT INTO exercise_attempts("
        " attempt_id, exercise_id, student_id, attempt_number, status,"
        " created_at, attempt_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "EA000001",
            "EX000001",
            learner_id,
            1,
            attempt_status,
            "2026-08-02T09:00:00+00:00",
            json.dumps({"submitted_at": "2026-08-02T09:00:00+00:00"}),
        ),
    )
    if completion_status is not None:
        connection.execute(
            "INSERT INTO practice_evaluations("
            " evaluation_id, attempt_id, practice_target_id, created_at,"
            " evaluation_json) VALUES (?, ?, ?, ?, ?)",
            (
                "PE000001",
                "EA000001",
                "PT000001",
                "2026-08-02T09:05:00+00:00",
                json.dumps(
                    {
                        "completion_status": completion_status,
                        "evaluator_version": evaluator_version,
                        "created_at": "2026-08-02T09:05:00+00:00",
                    }
                ),
            ),
        )


def seed_learning_item(
    connection: sqlite3.Connection, learner_id: str, learning_item_id: str,
) -> None:
    connection.execute(
        "INSERT INTO learning_items("
        " learning_item_id, student_id, created_at, updated_at)"
        " VALUES (?, ?, ?, ?)",
        (
            learning_item_id,
            learner_id,
            "2026-08-01T00:00:00+00:00",
            "2026-08-01T00:00:00+00:00",
        ),
    )


def make_observed_evidence() -> ObservedEvidence:
    return ObservedEvidence(
        evidence_id="E-101",
        source_event_id="SEV-E-101",
        evidence_type="surface_metric",
        observed_at=utc("2026-08-01T09:00:00+00:00"),
        admission_status=EvidenceAdmissionStatus.ADMISSIBLE,
        epistemic_status=EpistemicStatus.OBSERVED_DESCRIPTIVE,
        exposure_class=ExposureClass.RESEARCH_ONLY,
        provenance=make_provenance(),
        value={"metric": "connective_count", "count": 4},
    )


# ---------------------------------------------------------------------------
# Migration 16 (global ledger Option A)
# ---------------------------------------------------------------------------


class TestMigration16:
    def test_fresh_db_upgrades_to_16_with_table_and_ledger(self, tmp_path):
        repository = Database(tmp_path / "m16.db")
        repository.initialize()
        assert LATEST_MIGRATION_VERSION == 16
        assert repository._system_repository.migration_version() == 16
        with repository.connect() as connection:
            assert "learner_acknowledgements" in _table_names(connection)
            ledger = connection.execute(
                "SELECT name FROM schema_migrations WHERE version=16"
            ).fetchone()
            assert ledger is not None
            assert ledger["name"] == MIGRATION_16_NAME
            core_ledger = connection.execute(
                "SELECT name FROM schema_migrations WHERE version=15"
            ).fetchone()
            assert core_ledger is not None
            assert core_ledger["name"] == MIGRATION_15_NAME

    def test_upgrade_from_14_to_16_is_idempotent_and_preserves_rows(self, tmp_path):
        path = tmp_path / "up16.db"
        repository = Database(path)
        repository.initialize()
        store = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        with repository.connect() as connection:
            seed_students(connection, LEARNER)
        store.append(make_record())

        with repository.connect() as connection:
            rollback(connection, 15)
            rollback(connection, 14)
            assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == 14
            # Ledger-only rollback: table, data, and indexes are preserved;
            # both the CORE-15 and the 16 ledger rows are removed.
            assert "learner_acknowledgements" in _table_names(connection)
            assert (
                connection.execute(
                    "SELECT version FROM schema_migrations WHERE version=16"
                ).fetchone()
                is None
            )
            assert (
                connection.execute(
                    "SELECT acknowledgement_id FROM learner_acknowledgements"
                ).fetchone()[0]
                == "ACK-persistence-1"
            )
            # Re-upgrade 14 -> 15 -> 16 is idempotent and preserves the row.
            upgrade(connection)
            assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == 16
            assert (
                connection.execute(
                    "SELECT version FROM schema_migrations WHERE version=16"
                ).fetchone()
                is not None
            )
            assert (
                connection.execute(
                    "SELECT acknowledgement_id FROM learner_acknowledgements"
                ).fetchone()[0]
                == "ACK-persistence-1"
            )

    def test_reupgrade_is_idempotent(self, tmp_path):
        path = tmp_path / "idem16.db"
        repository = Database(path)
        repository.initialize()
        with repository.connect() as connection:
            upgrade(connection)
            upgrade(connection)
            assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == 16
            assert "learner_acknowledgements" in _table_names(connection)
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM schema_migrations WHERE version=16"
                ).fetchone()[0]
                == 1
            )

    def test_non_adjacent_rollback_is_rejected(self, tmp_path):
        repository = Database(tmp_path / "nonadj16.db")
        repository.initialize()
        with repository.connect() as connection:
            with pytest.raises(ValueError):
                rollback(connection, 13)


# ---------------------------------------------------------------------------
# Durable append-only store
# ---------------------------------------------------------------------------


class TestDurableStore:
    def test_append_get_roundtrip_preserves_all_fields(self, tmp_path):
        path = tmp_path / "store.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
        store = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        record = make_record(
            source_event_ids=["SEV-101", "SEV-102"],
            learning_item_id="LI-1",
            authentic_evidence_status="insufficient",
            practice_activity_id="PA-1",
            review_event_id="REV-1",
            policy_version="feedback-policy-v0.1.0",
            model_version="model-v0.1.0",
            config_version="config-v0.1.0",
            limitations=["Custom limitation."],
        )
        store.append(record)
        stored = store.get("ACK-persistence-1")
        assert stored is not None
        assert stored.model_dump(mode="python") == record.model_dump(mode="python")

    def test_list_for_learner_is_scoped_and_ordered(self, tmp_path):
        path = tmp_path / "scoped.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER, OTHER)
        store = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        store.append(make_record(learner_id=LEARNER, recorded_at=utc("2026-08-01T00:00:00+00:00")))
        store.append(
            make_record(
                acknowledgement_id="ACK-persistence-2",
                learner_id=OTHER,
                recorded_at=utc("2026-08-02T00:00:00+00:00"),
            )
        )
        store.append(
            make_record(
                acknowledgement_id="ACK-persistence-3",
                learner_id=LEARNER,
                source_evidence_ids=["E-103"],
                recorded_at=utc("2026-08-03T00:00:00+00:00"),
            )
        )
        learner_records = store.list_for_learner(LEARNER)
        assert [r.acknowledgement_id for r in learner_records] == [
            "ACK-persistence-1",
            "ACK-persistence-3",
        ]
        assert [r.acknowledgement_id for r in store.list_for_learner(OTHER)] == [
            "ACK-persistence-2"
        ]

    def test_close_reopen_same_file_persistence(self, tmp_path):
        path = tmp_path / "durable.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
        first = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        first.append(make_record())
        # A brand-new repository over the SAME SQLite file must see the row.
        reopened = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        stored = reopened.get("ACK-persistence-1")
        assert stored is not None
        assert stored.learner_id == LEARNER
        assert len(reopened.list_for_learner(LEARNER)) == 1

    def test_duplicate_id_conflict_has_no_write(self, tmp_path):
        path = tmp_path / "conflict.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
        store = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        store.append(make_record())
        with pytest.raises(AcknowledgementStoreConflictError) as exc_info:
            store.append(
                make_record(
                    acknowledgement_text=(
                        "A different descriptive sentence about the same evidence."
                    )
                )
            )
        assert exc_info.value.kind == "conflict"
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_duplicate_evidence_set_conflict_has_no_write(self, tmp_path):
        path = tmp_path / "dupset.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
        store = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        store.append(
            make_record(source_evidence_ids=["E-101", "E-102"])
        )
        # Same learner + kind + evidence SET (order-insensitive), different id.
        with pytest.raises(AcknowledgementStoreConflictError) as exc_info:
            store.append(
                make_record(
                    acknowledgement_id="ACK-persistence-other",
                    source_evidence_ids=["E-102", "E-101"],
                )
            )
        assert exc_info.value.kind == "duplicate_acknowledgement"
        assert len(store.list_for_learner(LEARNER)) == 1

# ---------------------------------------------------------------------------
# Qualified evidence lookup over the shared database
# ---------------------------------------------------------------------------


class TestEvidenceLookup:
    def test_history_evidence_registry_resolves_as_history_evidence(self, tmp_path):
        path = tmp_path / "lookup.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
            seed_history_evidence(connection, LEARNER)
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        assert lookup.owner_of("H001") == LEARNER
        record = lookup.get_record(LEARNER, "H001")
        assert isinstance(record, HistoryEvidence)
        assert record.history_evidence_id == "H001"
        assert record.evidence_type == "metric_change"
        assert record.limitation

    def test_completed_evaluation_resolves_to_practice_provenance(self, tmp_path):
        path = tmp_path / "lookup_eval.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
            seed_practice_chain(connection, LEARNER)
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        assert lookup.owner_of("PE000001") == LEARNER
        record = lookup.get_record(LEARNER, "PE000001")
        assert isinstance(record, PracticeProvenanceRecord)
        assert record.evaluation_id == "PE000001"
        assert record.attempt_id == "EA000001"
        assert record.evaluator_version == "practice-evaluator-v0.9.0"
        assert record.activity_status.value == "completed"
        assert record.exercise_version == "exercise-v0.9.0"

    def test_submitted_attempt_fails_closed_without_fabrication(self, tmp_path):
        path = tmp_path / "lookup_submitted.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
            # attempt status "submitted" is not an exact PracticeActivityStatus
            # member and must fail closed; no evaluation row exists.
            seed_practice_chain(connection, LEARNER, completion_status=None)
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        assert lookup.owner_of("EA000001") == LEARNER
        assert lookup.get_record(LEARNER, "EA000001") is None

    def test_learning_item_row_resolves_ownership(self, tmp_path):
        path = tmp_path / "lookup_li.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
            seed_learning_item(connection, LEARNER, "LI000001")
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        assert lookup.owner_of("LI000001") == LEARNER
        row = lookup.get_record(LEARNER, "LI000001")
        assert row is not None
        assert row["student_id"] == LEARNER
        assert row["learning_item_id"] == "LI000001"

    def test_absent_observed_evidence_and_review_tables_fail_closed(self, tmp_path):
        path = tmp_path / "lookup_absent.db"
        # Under the global Option A ledger a fresh database now upgrades to
        # 16 and therefore DOES contain the CORE review_events table (CORE-15
        # seam). The fail-closed contract that matters is the pre-CORE-15 era:
        # a genuine v14-era database (migrations 1-14 only) has neither the
        # CORE review table nor the learner observed-evidence table, and the
        # lookup must fail closed.
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            for version in range(1, 15):
                MIGRATIONS[version][1](connection)
                connection.execute(f"PRAGMA user_version={version}")
            connection.commit()
        finally:
            connection.close()
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        with Database(path).connect() as connection:
            names = _table_names(connection)
            assert "review_events" not in names
            assert "learner_observed_evidence" not in names
            assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == 14
        assert lookup.owner_of("REV-1") is None
        assert lookup.owner_of("OE-1") is None
        assert lookup.get_record(LEARNER, "REV-1") is None
        assert lookup.get_record(LEARNER, "OE-1") is None

    def test_cross_student_lookup_fails_closed(self, tmp_path):
        path = tmp_path / "lookup_x.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER, OTHER)
            seed_history_evidence(connection, LEARNER)
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        assert lookup.get_record(OTHER, "H001") is None


# ---------------------------------------------------------------------------
# Service link gates (no store write on any failure)
# ---------------------------------------------------------------------------


class InMemoryStore:
    """Append-only store double that records writes for no-write assertions."""

    def __init__(self) -> None:
        self._records: list[AcknowledgementRecord] = []

    def append(self, record: AcknowledgementRecord) -> None:
        self._records.append(record)

    def get(self, acknowledgement_id: str) -> AcknowledgementRecord | None:
        for record in self._records:
            if record.acknowledgement_id == acknowledgement_id:
                return record
        return None

    def list_for_learner(self, learner_id: str) -> list[AcknowledgementRecord]:
        return [record for record in self._records if record.learner_id == learner_id]


class LinkEvidencePort:
    """Evidence port double with learner-scoped structural links."""

    def __init__(self) -> None:
        self._owner: dict[str, str] = {}
        self._records: dict[str, Any] = {}

    def add(self, learner_id: str, source_id: str, record: Any = None) -> None:
        self._owner[source_id] = learner_id
        if record is not None:
            self._records[source_id] = record

    def owner_of(self, source_id: str) -> str | None:
        return self._owner.get(source_id)

    def get_record(self, learner_id: str, source_id: str) -> Any | None:
        if self.owner_of(source_id) != learner_id:
            return None
        return self._records.get(source_id)


def build_link_service(
    store: InMemoryStore | None = None,
    port: LinkEvidencePort | None = None,
) -> tuple[AcknowledgementService, InMemoryStore, LinkEvidencePort]:
    store = store or InMemoryStore()
    port = port or LinkEvidencePort()
    port.add(LEARNER, "E-101", make_observed_evidence())
    return (
        AcknowledgementService(
            store,
            evidence_port=port,
            now=lambda: NOW,
        ),
        store,
        port,
    )


class TestServiceLinkGates:
    def test_unknown_learning_item_fails_closed(self) -> None:
        service, store, port = build_link_service()
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(learning_item_id="LI-MISSING"))
        assert exc_info.value.kind == "learning_item_not_found"
        assert store.list_for_learner(LEARNER) == []

    def test_mismatched_learning_item_fails_closed(self) -> None:
        service, store, port = build_link_service()
        port.add(OTHER, "LI-OTHER")
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(learning_item_id="LI-OTHER"))
        assert exc_info.value.kind == "learning_item_owner_mismatch"
        assert store.list_for_learner(LEARNER) == []

    def test_unknown_practice_activity_link_fails_closed(self) -> None:
        service, store, _ = build_link_service()
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(practice_activity_id="PA-MISSING"))
        assert exc_info.value.kind == "practice_activity_not_found"
        assert store.list_for_learner(LEARNER) == []

    def test_review_link_fails_closed_when_core_table_absent(self) -> None:
        service, store, _ = build_link_service()
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(review_event_id="REV-1"))
        assert exc_info.value.kind == "review_event_not_found"
        assert store.list_for_learner(LEARNER) == []

    def test_invalid_runtime_authentic_evidence_status_fails_closed(self) -> None:
        service, store, _ = build_link_service()
        request = make_request(authentic_evidence_status="insufficient")
        # Records are mutable after construction; the gate re-validates at
        # runtime because Pydantic type checks do not run on assignment.
        request.authentic_evidence_status = "bogus"
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(request)
        assert exc_info.value.kind == "invalid_authentic_evidence_status"
        assert store.list_for_learner(LEARNER) == []

    def test_valid_links_acknowledge_and_carry_links(self) -> None:
        service, store, port = build_link_service()
        port.add(LEARNER, "LI-OWNED")
        result = service.acknowledge(
            make_request(
                learning_item_id="LI-OWNED",
                authentic_evidence_status="present",
            )
        )
        assert result.acknowledged is True
        assert result.record.learning_item_id == "LI-OWNED"
        assert result.record.authentic_evidence_status == "present"
        assert result.record.practice_activity_id is None
        assert result.record.review_event_id is None
        assert len(store.list_for_learner(LEARNER)) == 1


# ---------------------------------------------------------------------------
# Defense in depth: durable-store conflict translated by the service
# ---------------------------------------------------------------------------


class RejectingStore:
    """Store double that rejects at append time (e.g. a durable-store race
    or restart); the service must translate the store conflict."""

    def append(self, record: AcknowledgementRecord) -> None:
        raise AcknowledgementStoreConflictError(
            "conflict", "durable store rejected the write"
        )

    def get(self, acknowledgement_id: str) -> AcknowledgementRecord | None:
        return None

    def list_for_learner(self, learner_id: str) -> list[AcknowledgementRecord]:
        return []


class TestStoreConflictTranslation:
    def test_store_conflict_is_translated_to_acknowledgement_error(self) -> None:
        store = RejectingStore()
        service, _, _ = build_link_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request())
        assert exc_info.value.kind == "conflict"
        assert exc_info.value.message == "durable store rejected the write"


# ---------------------------------------------------------------------------
# End-to-end: real store + real lookup + service
# ---------------------------------------------------------------------------


class TestEndToEndPersistence:
    def test_positive_practice_result_acknowledgement_persists(self, tmp_path):
        path = tmp_path / "e2e.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
            seed_practice_chain(connection, LEARNER)
        store = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        service = build_service(store, lookup)

        result = service.acknowledge(
            make_request(
                source_kind=AcknowledgementSourceKind.PRACTICE_RESULT,
                source_evidence_ids=["PE000001"],
                acknowledgement_text=(
                    "A completed guided rewrite for the connective-use target "
                    "was acknowledged; descriptive activity evidence only."
                ),
            )
        )
        assert result.acknowledged is True
        assert result.record.source_kind == AcknowledgementSourceKind.PRACTICE_RESULT
        persisted = store.get(result.record.acknowledgement_id)
        assert persisted is not None
        assert persisted.learner_id == LEARNER
        assert persisted.source_evidence_ids == ["PE000001"]
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_positive_history_signal_acknowledgement_persists(self, tmp_path):
        path = tmp_path / "e2e_history.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
            seed_history_evidence(connection, LEARNER)
        store = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        service = build_service(store, lookup)

        result = service.acknowledge(
            make_request(
                source_kind=AcknowledgementSourceKind.HISTORY_SIGNAL,
                source_evidence_ids=["H001"],
                acknowledgement_text=(
                    "A descriptive metric comparison between two eligible "
                    "submissions was recorded; observed evidence only."
                ),
            )
        )
        assert result.acknowledged is True
        assert store.get(result.record.acknowledgement_id) is not None

    def test_review_link_fails_closed_with_real_lookup(self, tmp_path):
        path = tmp_path / "e2e_review.db"
        Database(path).initialize()
        with Database(path).connect() as connection:
            seed_students(connection, LEARNER)
            seed_history_evidence(connection, LEARNER)
        store = SQLiteAcknowledgementRepository(SQLiteConnectionManager(path))
        lookup = SQLiteAcknowledgementEvidenceLookup(SQLiteConnectionManager(path))
        service = build_service(store, lookup)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    source_kind=AcknowledgementSourceKind.HISTORY_SIGNAL,
                    source_evidence_ids=["H001"],
                    review_event_id="REV-NOT-EXISTING",
                )
            )
        assert exc_info.value.kind == "review_event_not_found"
        assert store.list_for_learner(LEARNER) == []


# ---------------------------------------------------------------------------
# Contract typing for the additive link fields
# ---------------------------------------------------------------------------


class TestLinkFieldTyping:
    def test_request_rejects_blank_link_ids(self) -> None:
        with pytest.raises(ValidationError):
            make_request(learning_item_id="   ")
        with pytest.raises(ValidationError):
            make_request(practice_activity_id="  ")
        with pytest.raises(ValidationError):
            make_request(review_event_id="")

    def test_record_rejects_blank_link_ids(self) -> None:
        with pytest.raises(ValidationError):
            make_record(learning_item_id="   ")
        with pytest.raises(ValidationError):
            make_record(review_event_id="")

    def test_link_ids_are_stripped(self) -> None:
        request = make_request(learning_item_id="  LI-1  ")
        assert request.learning_item_id == "LI-1"

    def test_authentic_evidence_status_literal_validation(self) -> None:
        with pytest.raises(ValidationError):
            make_request(authentic_evidence_status="bogus")
        with pytest.raises(ValidationError):
            make_record(authentic_evidence_status="bogus")
