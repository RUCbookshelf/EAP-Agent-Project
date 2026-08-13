"""Durable SQLite acknowledgement store + qualified evidence lookup (WU2-P).

Repair workers P for
``PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`` and
``PDW3-WU2-LEARNER-MIGRATION16-PINS-OPTION-A-20260812``. This module
implements the learner ``AcknowledgementStorePort`` against the shared
SQLite database (global migration 16 table ``learner_acknowledgements``;
Migration 15 is CORE-owned ``review_scheduling_foundation``) and the
learner ``AcknowledgementEvidencePort`` over the same single database.

- The store is append-only: no update/delete surface. In ONE transaction it
  rejects an existing ``acknowledgement_id`` (kind ``conflict``) and an
  existing row for the same ``(learner_id, source_kind,
  frozenset(source_evidence_ids))`` (kind ``duplicate_acknowledgement``)
  before inserting. Violations raise ``AcknowledgementStoreConflictError``
  (defined once in ``app.learner.acknowledgement``, mirroring CORE's
  repository-conflict pattern; the service translates it to
  ``AcknowledgementError`` for defense in depth).
- The evidence lookup reads ONLY the single shared SQLite database through
  the injected connection manager. All reads are fail-closed: missing
  tables are detected via ``sqlite_master`` and treated as ``None``. Stored
  statuses are never mapped or reinterpreted: an exercise attempt only
  resolves when its stored ``status`` is an exact learner
  ``PracticeActivityStatus`` member (e.g. ``submitted`` fails closed), and
  an evaluation only resolves when ``completion_status`` is an exact
  member. Versions are only filled from stored fields; nothing is
  fabricated or defaulted.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from app.infrastructure.sqlite.connection import SQLiteConnectionManager
from app.learner.acknowledgement import (
    AcknowledgementStoreConflictError,
    AcknowledgementStorePort,
)
from app.learner.acknowledgement_contracts import (
    AcknowledgementRecord,
    AcknowledgementSourceKind,
    LearnerConsent,
)
from app.learner.evidence import ProvenanceChain
from app.learner.practice_provenance import (
    PracticeActivityStatus,
    PracticeProvenanceRecord,
)
from app.models.schemas import HistoryEvidence
from app.shared.vocabularies import EpistemicStatus, EvidenceStatus


_INSERT_COLUMNS = (
    "acknowledgement_id",
    "learner_id",
    "source_kind",
    "source_evidence_ids_json",
    "source_event_ids_json",
    "learning_item_id",
    "authentic_evidence_status",
    "practice_activity_id",
    "review_event_id",
    "evidence_status",
    "epistemic_status",
    "outcome_claim",
    "provenance_json",
    "policy_version",
    "model_version",
    "config_version",
    "record_version",
    "acknowledgement_text",
    "limitations_json",
    "consent_json",
    "observed_span_start",
    "observed_span_end",
    "recorded_at",
)

_ACKNOWLEDGEMENT_SOURCE_KIND_VALUES = frozenset(
    kind.value for kind in AcknowledgementSourceKind
)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _is_acknowledgement_row(row: sqlite3.Row) -> bool:
    """Read-side discriminator for the shared migration-16 table.

    The single ``learner_acknowledgements`` table is the architecture-
    compliant durable home for both LEARNER acknowledgement rows and the
    composed L2 WU3 tutor-consent row family (``source_kind='tutor_consent'``).
    Only rows whose ``source_kind`` is an exact ``AcknowledgementSourceKind``
    member are acknowledgement records; any other row family is skipped on
    read and never parsed as an ``AcknowledgementRecord`` (fail closed, no
    reinterpretation, no data deletion).
    """

    return row["source_kind"] in _ACKNOWLEDGEMENT_SOURCE_KIND_VALUES


def _to_row(record: AcknowledgementRecord) -> tuple:
    return (
        record.acknowledgement_id,
        record.learner_id,
        record.source_kind.value,
        _json(record.source_evidence_ids),
        _json(record.source_event_ids),
        record.learning_item_id,
        record.authentic_evidence_status,
        record.practice_activity_id,
        record.review_event_id,
        record.evidence_status.value,
        record.epistemic_status.value,
        record.outcome_claim,
        _json(record.provenance.model_dump(mode="json")),
        record.policy_version,
        record.model_version,
        record.config_version,
        record.record_version,
        record.acknowledgement_text,
        _json(record.limitations),
        _json(record.consent.model_dump(mode="json")),
        _iso(record.observed_span_start),
        _iso(record.observed_span_end),
        _iso(record.recorded_at),
    )


def _from_row(row: sqlite3.Row) -> AcknowledgementRecord:
    return AcknowledgementRecord(
        acknowledgement_id=row["acknowledgement_id"],
        learner_id=row["learner_id"],
        source_kind=AcknowledgementSourceKind(row["source_kind"]),
        source_evidence_ids=json.loads(row["source_evidence_ids_json"]),
        source_event_ids=json.loads(row["source_event_ids_json"]),
        learning_item_id=row["learning_item_id"],
        authentic_evidence_status=row["authentic_evidence_status"],
        practice_activity_id=row["practice_activity_id"],
        review_event_id=row["review_event_id"],
        evidence_status=EvidenceStatus(row["evidence_status"]),
        epistemic_status=EpistemicStatus(row["epistemic_status"]),
        outcome_claim=row["outcome_claim"],
        provenance=ProvenanceChain.model_validate(
            json.loads(row["provenance_json"])
        ),
        policy_version=row["policy_version"],
        model_version=row["model_version"],
        config_version=row["config_version"],
        record_version=row["record_version"],
        acknowledgement_text=row["acknowledgement_text"],
        limitations=json.loads(row["limitations_json"]),
        consent=LearnerConsent.model_validate(json.loads(row["consent_json"])),
        observed_span_start=_parse_dt(row["observed_span_start"]),
        observed_span_end=_parse_dt(row["observed_span_end"]),
        recorded_at=_parse_dt(row["recorded_at"]),
    )


class SQLiteAcknowledgementRepository(AcknowledgementStorePort):
    """Append-only durable acknowledgement store (migration 15 table)."""

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        self._connection_manager = connection_manager

    def append(self, record: AcknowledgementRecord) -> None:
        connection = self._connection_manager.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT 1 FROM learner_acknowledgements "
                "WHERE acknowledgement_id=?",
                (record.acknowledgement_id,),
            ).fetchone()
            if existing is not None:
                raise AcknowledgementStoreConflictError(
                    "conflict",
                    "The acknowledgement id conflicts with an existing record.",
                )
            target_set = frozenset(record.source_evidence_ids)
            rows = connection.execute(
                "SELECT source_evidence_ids_json FROM learner_acknowledgements "
                "WHERE learner_id=? AND source_kind=?",
                (record.learner_id, record.source_kind.value),
            ).fetchall()
            for row in rows:
                if frozenset(json.loads(row[0])) == target_set:
                    raise AcknowledgementStoreConflictError(
                        "duplicate_acknowledgement",
                        "This evidence set is already acknowledged for "
                        "this learner.",
                    )
            placeholders = ", ".join("?" for _ in _INSERT_COLUMNS)
            connection.execute(
                f"INSERT INTO learner_acknowledgements"
                f"({', '.join(_INSERT_COLUMNS)}) VALUES ({placeholders})",
                _to_row(record),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, acknowledgement_id: str) -> AcknowledgementRecord | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learner_acknowledgements "
                "WHERE acknowledgement_id=?",
                (acknowledgement_id,),
            ).fetchone()
        if row is None or not _is_acknowledgement_row(row):
            return None
        return _from_row(row)

    def list_for_learner(self, learner_id: str) -> list[AcknowledgementRecord]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM learner_acknowledgements "
                "WHERE learner_id=? ORDER BY recorded_at, acknowledgement_id",
                (learner_id,),
            ).fetchall()
        return [_from_row(row) for row in rows if _is_acknowledgement_row(row)]


class SQLiteAcknowledgementEvidenceLookup:
    """Learner-scoped evidence lookup over the single shared SQLite database.

    Every read is fail-closed: a table that does not exist (detected via
    ``sqlite_master``) is treated as ``None``. ``owner_of`` searches in a
    fixed order; ``get_record`` returns fully qualified typed records only
    when the stored fields satisfy the learner contracts exactly.
    """

    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        self._connection_manager = connection_manager

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None

    def owner_of(self, source_id: str) -> str | None:
        with self._connection_manager.connect() as connection:
            if self._table_exists(connection, "history_evidence_registry"):
                row = connection.execute(
                    "SELECT student_id FROM history_evidence_registry "
                    "WHERE history_evidence_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    return str(row[0])
            if self._table_exists(connection, "practice_targets"):
                row = connection.execute(
                    "SELECT student_id FROM practice_targets "
                    "WHERE practice_target_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    return str(row[0])
            if self._table_exists(connection, "exercise_attempts"):
                row = connection.execute(
                    "SELECT student_id FROM exercise_attempts "
                    "WHERE attempt_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    return str(row[0])
            if (
                self._table_exists(connection, "practice_evaluations")
                and self._table_exists(connection, "exercise_attempts")
            ):
                row = connection.execute(
                    "SELECT ea.student_id FROM practice_evaluations pe "
                    "JOIN exercise_attempts ea ON ea.attempt_id = pe.attempt_id "
                    "WHERE pe.evaluation_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    return str(row[0])
            if self._table_exists(connection, "learning_items"):
                row = connection.execute(
                    "SELECT student_id FROM learning_items "
                    "WHERE learning_item_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    return str(row[0])
            if self._table_exists(connection, "review_events"):
                row = connection.execute(
                    "SELECT student_id FROM review_events "
                    "WHERE review_event_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    return str(row[0])
            if self._table_exists(connection, "learner_observed_evidence"):
                row = connection.execute(
                    "SELECT student_id FROM learner_observed_evidence "
                    "WHERE evidence_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    return str(row[0])
        return None

    def get_record(self, learner_id: str, source_id: str) -> Any | None:
        with self._connection_manager.connect() as connection:
            if self._table_exists(connection, "history_evidence_registry"):
                row = connection.execute(
                    "SELECT student_id, evidence_json "
                    "FROM history_evidence_registry "
                    "WHERE history_evidence_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    if row["student_id"] != learner_id:
                        return None
                    try:
                        return HistoryEvidence.model_validate(
                            json.loads(row["evidence_json"])
                        )
                    except ValueError:
                        # Unparseable or model-invalid registry payloads
                        # fail closed; they are never reinterpreted.
                        return None
            if (
                self._table_exists(connection, "exercise_attempts")
                and self._table_exists(connection, "exercise_instances")
            ):
                row = connection.execute(
                    "SELECT ea.attempt_id, ea.exercise_id, ea.student_id, "
                    "ea.status, ea.created_at, ea.attempt_json, "
                    "ei.practice_target_id, ei.instance_json "
                    "FROM exercise_attempts ea "
                    "JOIN exercise_instances ei ON ei.exercise_id = ea.exercise_id "
                    "WHERE ea.attempt_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    if row["student_id"] != learner_id:
                        return None
                    record = self._attempt_provenance(row)
                    if record is not None:
                        return record
            if (
                self._table_exists(connection, "practice_evaluations")
                and self._table_exists(connection, "exercise_attempts")
                and self._table_exists(connection, "exercise_instances")
            ):
                row = connection.execute(
                    "SELECT pe.evaluation_id, pe.attempt_id, "
                    "pe.practice_target_id, pe.created_at, pe.evaluation_json, "
                    "ea.exercise_id, ea.student_id, ei.instance_json "
                    "FROM practice_evaluations pe "
                    "JOIN exercise_attempts ea ON ea.attempt_id = pe.attempt_id "
                    "JOIN exercise_instances ei ON ei.exercise_id = ea.exercise_id "
                    "WHERE pe.evaluation_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None:
                    if row["student_id"] != learner_id:
                        return None
                    record = self._evaluation_provenance(row)
                    if record is not None:
                        return record
            if self._table_exists(connection, "learning_items"):
                row = connection.execute(
                    "SELECT * FROM learning_items WHERE learning_item_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None and row["student_id"] == learner_id:
                    return dict(row)
            if self._table_exists(connection, "review_events"):
                row = connection.execute(
                    "SELECT * FROM review_events WHERE review_event_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None and row["student_id"] == learner_id:
                    return dict(row)
            if self._table_exists(connection, "learner_observed_evidence"):
                # Future integration-owned table: on this branch it is
                # absent, so this branch fails closed. When present, the row
                # is returned as-is; the future integration defines the
                # typed contract.
                row = connection.execute(
                    "SELECT * FROM learner_observed_evidence "
                    "WHERE evidence_id=?",
                    (source_id,),
                ).fetchone()
                if row is not None and row["student_id"] == learner_id:
                    return dict(row)
        return None

    @staticmethod
    def _attempt_provenance(row: sqlite3.Row) -> PracticeProvenanceRecord | None:
        """Build a provenance record ONLY when stored fields qualify.

        The stored ``status`` must be an exact learner ``PracticeActivityStatus``
        member and the joined exercise instance must carry an
        ``exercise_version``; ``submitted`` and other non-member statuses
        fail closed (no mapping or reinterpretation).
        """

        statuses = {status.value for status in PracticeActivityStatus}
        if row["status"] not in statuses:
            return None
        try:
            instance = json.loads(row["instance_json"])
            attempt = json.loads(row["attempt_json"])
        except (json.JSONDecodeError, TypeError):
            return None
        exercise_version = instance.get("exercise_version")
        if not exercise_version:
            return None
        occurred_at = _parse_dt(attempt.get("submitted_at"))
        if occurred_at is None:
            occurred_at = _parse_dt(row["created_at"])
        if occurred_at is None:
            return None
        return PracticeProvenanceRecord(
            record_id=row["attempt_id"],
            student_id=row["student_id"],
            practice_target_id=row["practice_target_id"],
            exercise_id=row["exercise_id"],
            exercise_version=exercise_version,
            attempt_id=row["attempt_id"],
            evaluation_id=None,
            evaluator_version=None,
            activity_status=PracticeActivityStatus(row["status"]),
            occurred_at=occurred_at,
        )

    @staticmethod
    def _evaluation_provenance(row: sqlite3.Row) -> PracticeProvenanceRecord | None:
        """Build a provenance record from a practice evaluation row.

        ``completion_status`` must be an exact learner
        ``PracticeActivityStatus`` member and the joined instance must carry
        an ``exercise_version``; evaluator version is filled only from the
        stored evaluation payload.
        """

        statuses = {status.value for status in PracticeActivityStatus}
        try:
            evaluation = json.loads(row["evaluation_json"])
            instance = json.loads(row["instance_json"])
        except (json.JSONDecodeError, TypeError):
            return None
        completion_status = evaluation.get("completion_status")
        if completion_status not in statuses:
            return None
        exercise_version = instance.get("exercise_version")
        if not exercise_version:
            return None
        occurred_at = _parse_dt(evaluation.get("created_at"))
        if occurred_at is None:
            occurred_at = _parse_dt(row["created_at"])
        if occurred_at is None:
            return None
        return PracticeProvenanceRecord(
            record_id=row["evaluation_id"],
            student_id=row["student_id"],
            practice_target_id=row["practice_target_id"],
            exercise_id=row["exercise_id"],
            exercise_version=exercise_version,
            attempt_id=row["attempt_id"],
            evaluation_id=row["evaluation_id"],
            evaluator_version=evaluation.get("evaluator_version"),
            activity_status=PracticeActivityStatus(completion_status),
            occurred_at=occurred_at,
        )


__all__ = [
    "SQLiteAcknowledgementEvidenceLookup",
    "SQLiteAcknowledgementRepository",
]
