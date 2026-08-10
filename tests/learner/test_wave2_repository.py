"""Repository protocol tests: in-memory and self-contained SQLite (TEST-ONLY)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.learner.wave2.models import ObservationType, RevisionResponseState
from app.learner.wave2.repository import InMemoryObservationRepository
from app.learner.wave2.sqlite_repository import SqliteObservationRepository
from tests.learner.wave2_helpers import (
    make_anchor,
    make_behavior,
    make_evidence,
    make_observation,
    make_occurrence,
    make_proficiency_context,
    make_sample,
    utc,
)


def _round_trip_scenario(repository) -> None:
    learner = "L-REPO-001"
    occurrence = make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1))
    record = make_observation(
        "SVA-01", learner, ObservationType.DIFFICULTY,
        "SVA-001", "subject-verb agreement", [occurrence],
    )
    repository.save_observation(record)
    assert repository.get_observation(learner, "SVA-01") == record
    assert [r.observation_id for r in repository.list_observations(learner)] == ["SVA-01"]
    assert [r.observation_id for r in repository.list_observations(
        learner, observation_type=ObservationType.DIFFICULTY,
    )] == ["SVA-01"]
    assert repository.list_observations(
        learner, observation_type=ObservationType.STRENGTH,
    ) == []
    assert repository.get_observation(learner, "missing") is None

    sample = make_sample("S-001", learner, "T-01", utc(2026, 7, 1))
    repository.save_submission_sample(sample)
    assert repository.list_submission_samples(learner) == [sample]

    evidence = make_evidence("E-101", learner, utc(2026, 7, 1))
    repository.save_evidence(learner, evidence)
    assert repository.get_evidence(learner, "E-101") == evidence
    assert [e.evidence_id for e in repository.list_evidence(learner)] == ["E-101"]
    assert repository.get_evidence(learner, "missing") is None

    behavior = make_behavior(
        "B-01", learner, "SVA-01", "R-01",
        RevisionResponseState.CORRECTED_AFTER_FEEDBACK, utc(2026, 7, 2),
    )
    repository.save_revision_behavior(behavior)
    assert repository.list_revision_behavior(learner) == [behavior]
    assert repository.list_revision_behavior(learner, observation_id="SVA-01") == [behavior]
    assert repository.list_revision_behavior(learner, observation_id="other") == []

    context = make_proficiency_context(
        learner, [make_anchor("A-1", "CET-4", "CET-4 passed", utc(2026, 6, 1))]
    )
    repository.save_proficiency_context(context)
    assert repository.get_proficiency_context(learner) == context
    assert repository.get_proficiency_context("other") is None


class TestInMemoryRepository:
    def test_round_trip(self) -> None:
        _round_trip_scenario(InMemoryObservationRepository())

    def test_isolated_between_learners(self) -> None:
        repository = InMemoryObservationRepository()
        record = make_observation(
            "SVA-01", "L-A", ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement", [],
        )
        repository.save_observation(record)
        assert repository.get_observation("L-B", "SVA-01") is None


class TestSqliteRepository:
    def test_creates_own_tables_in_test_only_database(self, tmp_path: Path) -> None:
        db_path = tmp_path / "wave2-learner-test.db"
        repository = SqliteObservationRepository(db_path)
        try:
            connection = sqlite3.connect(str(db_path))
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            finally:
                connection.close()
            assert {
                "wave2_learner_observations",
                "wave2_learner_submission_samples",
                "wave2_learner_revision_behavior",
                "wave2_learner_evidence",
                "wave2_learner_proficiency_context",
            } <= tables
        finally:
            repository.close()

    def test_round_trip(self, tmp_path: Path) -> None:
        repository = SqliteObservationRepository(tmp_path / "wave2-learner-test.db")
        try:
            _round_trip_scenario(repository)
        finally:
            repository.close()

    def test_reinit_is_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "wave2-learner-test.db"
        first = SqliteObservationRepository(db_path)
        first.close()
        second = SqliteObservationRepository(db_path)
        try:
            assert second.list_observations("L-REPO-001") == []
        finally:
            second.close()

    def test_sqlite_module_is_self_contained(self) -> None:
        source = Path(
            "app/learner/wave2/sqlite_repository.py"
        ).read_text(encoding="utf-8")
        assert "import app.database" not in source
        assert "from app.database" not in source
        assert "import app.infrastructure" not in source
        assert "from app.infrastructure" not in source
