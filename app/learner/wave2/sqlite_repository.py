"""Self-contained TEST-ONLY SQLite implementation of ObservationRepository.

Goal PDW2-B-LEARNER-MODEL: the LEARNER branch must not import CORE-branch-only
persistence (``app.infrastructure.sqlite.repositories.wave2`` or migration-14
DDL; those land at integration). This module therefore owns its own tables
(``wave2_learner_*``), created inside a TEST-ONLY database passed by the
caller (for example a ``pytest`` tmp_path database). It is not wired into
the composition root and must never serve as the shared persistence layer.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.learner.evidence import ObservedEvidence
from app.learner.wave2.models import (
    ObservationRecord,
    ObservationType,
    ProficiencyContext,
    RevisionBehavior,
    SubmissionSample,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS wave2_learner_observations (
    learner_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    observation_type TEXT NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY (learner_id, observation_id)
);
CREATE TABLE IF NOT EXISTS wave2_learner_submission_samples (
    learner_id TEXT NOT NULL,
    submission_id TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY (learner_id, submission_id)
);
CREATE TABLE IF NOT EXISTS wave2_learner_revision_behavior (
    learner_id TEXT NOT NULL,
    behavior_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY (learner_id, behavior_id)
);
CREATE TABLE IF NOT EXISTS wave2_learner_evidence (
    learner_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY (learner_id, evidence_id)
);
CREATE TABLE IF NOT EXISTS wave2_learner_proficiency_context (
    learner_id TEXT NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY (learner_id)
);
"""


class SqliteObservationRepository:
    """SQLite implementation creating its own tables (TEST-ONLY databases)."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._connection = sqlite3.connect(str(self._path))
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SqliteObservationRepository":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- observations --------------------------------------------------------

    def save_observation(self, record: ObservationRecord) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_learner_observations "
            "(learner_id, observation_id, observation_type, record_json) "
            "VALUES (?, ?, ?, ?)",
            (
                record.learner_id,
                record.observation_id,
                record.observation_type.value,
                record.model_dump_json(),
            ),
        )
        self._connection.commit()

    def get_observation(
        self, learner_id: str, observation_id: str,
    ) -> ObservationRecord | None:
        row = self._connection.execute(
            "SELECT record_json FROM wave2_learner_observations "
            "WHERE learner_id = ? AND observation_id = ?",
            (learner_id, observation_id),
        ).fetchone()
        if row is None:
            return None
        return ObservationRecord.model_validate_json(row["record_json"])

    def list_observations(
        self, learner_id: str,
        observation_type: ObservationType | None = None,
    ) -> list[ObservationRecord]:
        if observation_type is None:
            rows = self._connection.execute(
                "SELECT record_json FROM wave2_learner_observations "
                "WHERE learner_id = ? ORDER BY observation_id",
                (learner_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT record_json FROM wave2_learner_observations "
                "WHERE learner_id = ? AND observation_type = ? "
                "ORDER BY observation_id",
                (learner_id, observation_type.value),
            ).fetchall()
        return [
            ObservationRecord.model_validate_json(row["record_json"])
            for row in rows
        ]

    # -- submission samples --------------------------------------------------

    def save_submission_sample(self, sample: SubmissionSample) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_learner_submission_samples "
            "(learner_id, submission_id, submitted_at, record_json) "
            "VALUES (?, ?, ?, ?)",
            (
                sample.learner_id,
                sample.submission_id,
                sample.submitted_at.isoformat(),
                sample.model_dump_json(),
            ),
        )
        self._connection.commit()

    def list_submission_samples(self, learner_id: str) -> list[SubmissionSample]:
        rows = self._connection.execute(
            "SELECT record_json FROM wave2_learner_submission_samples "
            "WHERE learner_id = ? ORDER BY submitted_at",
            (learner_id,),
        ).fetchall()
        return [
            SubmissionSample.model_validate_json(row["record_json"])
            for row in rows
        ]

    # -- evidence ------------------------------------------------------------

    def save_evidence(self, learner_id: str, evidence: ObservedEvidence) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_learner_evidence "
            "(learner_id, evidence_id, record_json) VALUES (?, ?, ?)",
            (learner_id, evidence.evidence_id, evidence.model_dump_json()),
        )
        self._connection.commit()

    def get_evidence(
        self, learner_id: str, evidence_id: str,
    ) -> ObservedEvidence | None:
        row = self._connection.execute(
            "SELECT record_json FROM wave2_learner_evidence "
            "WHERE learner_id = ? AND evidence_id = ?",
            (learner_id, evidence_id),
        ).fetchone()
        if row is None:
            return None
        return ObservedEvidence.model_validate_json(row["record_json"])

    def list_evidence(self, learner_id: str) -> list[ObservedEvidence]:
        rows = self._connection.execute(
            "SELECT record_json FROM wave2_learner_evidence "
            "WHERE learner_id = ? ORDER BY evidence_id",
            (learner_id,),
        ).fetchall()
        return [
            ObservedEvidence.model_validate_json(row["record_json"])
            for row in rows
        ]

    # -- revision behavior ---------------------------------------------------

    def save_revision_behavior(self, behavior: RevisionBehavior) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_learner_revision_behavior "
            "(learner_id, behavior_id, observation_id, occurred_at, record_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                behavior.learner_id,
                behavior.behavior_id,
                behavior.observation_id,
                behavior.occurred_at.isoformat(),
                behavior.model_dump_json(),
            ),
        )
        self._connection.commit()

    def list_revision_behavior(
        self, learner_id: str, observation_id: str | None = None,
    ) -> list[RevisionBehavior]:
        if observation_id is None:
            rows = self._connection.execute(
                "SELECT record_json FROM wave2_learner_revision_behavior "
                "WHERE learner_id = ? ORDER BY occurred_at",
                (learner_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT record_json FROM wave2_learner_revision_behavior "
                "WHERE learner_id = ? AND observation_id = ? "
                "ORDER BY occurred_at",
                (learner_id, observation_id),
            ).fetchall()
        return [
            RevisionBehavior.model_validate_json(row["record_json"])
            for row in rows
        ]

    # -- proficiency context -------------------------------------------------

    def save_proficiency_context(self, context: ProficiencyContext) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_learner_proficiency_context "
            "(learner_id, record_json) VALUES (?, ?)",
            (context.learner_id, context.model_dump_json()),
        )
        self._connection.commit()

    def get_proficiency_context(self, learner_id: str) -> ProficiencyContext | None:
        row = self._connection.execute(
            "SELECT record_json FROM wave2_learner_proficiency_context "
            "WHERE learner_id = ?",
            (learner_id,),
        ).fetchone()
        if row is None:
            return None
        return ProficiencyContext.model_validate_json(row["record_json"])


__all__ = ["SqliteObservationRepository"]
