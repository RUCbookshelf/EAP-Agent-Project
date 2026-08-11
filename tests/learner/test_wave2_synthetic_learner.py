"""Synthetic longitudinal learner demonstration (Goal PDW2-B-LEARNER-MODEL).

One synthetic learner with multiple submissions and revisions, exercised
against BOTH repository implementations (in-memory and self-contained
SQLite TEST-ONLY database). Surfaces: recurring difficulty, prior revision
response, recent history, a strength/stable observation, evidence and
provenance links, and explicit insufficient-history states.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.learner.evidence import EvidenceAdmissionStatus
from app.learner.evidence import check_provenance_completeness
from app.learner.normative import NormativeClaimsScanner
from app.learner.wave2.models import (
    ExternalAnchorSystem,
    HistoryState,
    ObservationType,
    RevisionResponseState,
    StabilityKind,
)
from app.learner.wave2.repository import InMemoryObservationRepository
from app.learner.wave2.services import LongitudinalLearnerService
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


SCANNER = NormativeClaimsScanner()
LEARNER = "L-SYN-001"
NOW = utc(2026, 8, 20, 12)


def seed_synthetic_learner(service: LongitudinalLearnerService) -> None:
    """Four submissions, two revisions, three difficulty/strength families."""

    samples = [
        ("S-001", "T-01", utc(2026, 7, 1)),
        ("S-002", "T-02", utc(2026, 7, 15)),
        ("S-003", "T-03", utc(2026, 8, 1)),
        ("S-004", "T-04", utc(2026, 8, 8)),
        ("S-005", "T-05", utc(2026, 8, 15)),
    ]
    for submission_id, task, at in samples:
        service.record_submission_sample(
            make_sample(submission_id, LEARNER, task, at)
        )

    for evidence_id, at in (
        ("E-101", utc(2026, 7, 1)),
        ("E-102", utc(2026, 7, 15)),
        ("E-201", utc(2026, 7, 15)),
        ("E-202", utc(2026, 8, 1)),
        ("E-203", utc(2026, 8, 8)),
        ("E-301", utc(2026, 7, 1)),
        ("E-401", utc(2026, 7, 1)),
        ("E-402", utc(2026, 8, 15)),
    ):
        service.admit_evidence(
            LEARNER, make_evidence(evidence_id, LEARNER, at)
        )
    service.admit_evidence(LEARNER, make_evidence(
        "E-999", LEARNER, utc(2026, 7, 2),
        admission_status=EvidenceAdmissionStatus.LIMITED,
    ))

    # Recurring difficulty: subject-verb agreement observed in S-001 and S-002,
    # absent from S-003/S-004/S-005 (the most recent qualified samples).
    service.record_observation(make_observation(
        "SVA-01", LEARNER, ObservationType.DIFFICULTY,
        "SVA-001", "subject-verb agreement",
        [
            make_occurrence("OC-SVA-1", "E-101", "T-01", utc(2026, 7, 1)),
            make_occurrence("OC-SVA-2", "E-102", "T-02", utc(2026, 7, 15)),
        ],
    ))
    service.record_revision_behavior(make_behavior(
        "B-01", LEARNER, "SVA-01", "R-01",
        RevisionResponseState.CORRECTED_AFTER_FEEDBACK, utc(2026, 7, 2),
    ))
    service.record_revision_behavior(make_behavior(
        "B-02", LEARNER, "SVA-01", "R-02",
        RevisionResponseState.REAPPEARED_LATER, utc(2026, 7, 16),
    ))

    # Strength with repeated positive history across three submissions.
    service.record_observation(make_observation(
        "CONN-01", LEARNER, ObservationType.STRENGTH,
        "CONN-RNG", "connective range",
        [
            make_occurrence("OC-CONN-1", "E-201", "T-02", utc(2026, 7, 15)),
            make_occurrence("OC-CONN-2", "E-202", "T-03", utc(2026, 8, 1)),
            make_occurrence("OC-CONN-3", "E-203", "T-04", utc(2026, 8, 8)),
        ],
    ))

    # Single-occurrence difficulty: explicit insufficient-history state.
    service.record_observation(make_observation(
        "ART-01", LEARNER, ObservationType.DIFFICULTY,
        "ART-001", "article usage",
        [make_occurrence("OC-ART-1", "E-301", "T-01", utc(2026, 7, 1))],
    ))

    # Second recurring difficulty that IS present in the recent window, so it
    # must not be reported as stable.
    service.record_observation(make_observation(
        "TEN-01", LEARNER, ObservationType.DIFFICULTY,
        "TEN-001", "tense consistency",
        [
            make_occurrence("OC-TEN-1", "E-401", "T-01", utc(2026, 7, 1)),
            make_occurrence("OC-TEN-2", "E-402", "T-05", utc(2026, 8, 15)),
        ],
    ))

    service.set_proficiency_context(make_proficiency_context(
        LEARNER,
        [
            make_anchor(
                "A-01", ExternalAnchorSystem.CET4, "CET-4 passed",
                utc(2026, 6, 1),
            ),
            make_anchor(
                "A-02", ExternalAnchorSystem.IELTS, "IELTS 6.0 band",
                utc(2026, 7, 1), source="external_certificate",
            ),
        ],
    ))


@pytest.fixture(params=["in_memory", "sqlite"])
def service(request, tmp_path: Path) -> LongitudinalLearnerService:
    if request.param == "in_memory":
        repository = InMemoryObservationRepository()
    else:
        repository = SqliteObservationRepository(
            tmp_path / "wave2-synthetic-learner.db"
        )
    created = LongitudinalLearnerService(repository, now=lambda: NOW)
    seed_synthetic_learner(created)
    yield created
    if isinstance(repository, SqliteObservationRepository):
        repository.close()


class TestSyntheticLearner:
    def test_recurring_difficulty_surfaces(self, service) -> None:
        result = service.recurring_difficulties(LEARNER)
        assert result.history_state is HistoryState.SUFFICIENT
        ids = {item.observation_id for item in result.items}
        assert "SVA-01" in ids
        assert "TEN-01" in ids
        assert "ART-01" not in ids
        sva = next(item for item in result.items if item.observation_id == "SVA-01")
        assert sva.appeared_before is True
        assert sva.occurrence_count == 2
        assert [o.occurrence_id for o in sva.occurrence_history] == [
            "OC-SVA-1", "OC-SVA-2",
        ]
        assert sva.contexts == ["T-01", "T-02"]
        assert sva.revision_response is RevisionResponseState.REAPPEARED_LATER
        assert sva.addressed_in_prior_revision is True

    def test_recent_history_frequency(self, service) -> None:
        status = service.observation_status(LEARNER, "SVA-01")
        assert status is not None
        assert status.frequency.qualified_sample_count == 3
        assert status.frequency.qualified_occurrence_count == 0
        assert status.frequency.descriptive_proportion == 0.0
        assert status.frequency.history_state is HistoryState.SUFFICIENT
        assert status.days_since_last_observed == (NOW - utc(2026, 7, 15)).days

    def test_strength_and_stable_observations(self, service) -> None:
        strengths = service.strengths(LEARNER)
        conn = next(item for item in strengths.items if item.observation_id == "CONN-01")
        assert conn.occurrence_count == 3
        assert conn.history_state is HistoryState.SUFFICIENT

        stable = service.stable_recently(LEARNER)
        by_id = {item.observation_id: item for item in stable.items}
        assert (
            by_id["SVA-01"].stability_kind
            is StabilityKind.PREVIOUSLY_RECURRING_NOT_RECENTLY_OBSERVED
        )
        assert by_id["SVA-01"].recent_window_sample_count == 3
        assert by_id["SVA-01"].recent_window_occurrence_count == 0
        assert by_id["SVA-01"].history_state is HistoryState.SUFFICIENT
        assert by_id["CONN-01"].stability_kind is StabilityKind.STRENGTH_HISTORY
        assert "TEN-01" not in by_id

    def test_explicit_insufficient_history_states(self, service) -> None:
        art = service.observation_status(LEARNER, "ART-01")
        assert art is not None
        assert art.history_state is HistoryState.INSUFFICIENT_HISTORY
        assert art.history_reasons
        assert art.appeared_before is False

        context = service.proficiency_context("L-SYN-NO-RECORD")
        assert context.history_state is HistoryState.INSUFFICIENT_HISTORY
        assert context.history_reasons

    def test_proficiency_context_external_anchors_only(self, service) -> None:
        context = service.proficiency_context(LEARNER)
        assert context.history_state is HistoryState.SUFFICIENT
        assert context.derived_from_corpus is False
        assert [a.system for a in context.anchors] == [
            ExternalAnchorSystem.CET4, ExternalAnchorSystem.IELTS,
        ]
        assert context.anchors[0].source == "learner_declared"
        assert context.anchors[1].source == "external_certificate"

    def test_evidence_and_provenance_links_resolve(self, service) -> None:
        result = service.current_evidence(LEARNER)
        evidence_by_id = {item.evidence.evidence_id: item.evidence for item in result.items}
        assert result.excluded_count == 1
        assert "E-999" not in evidence_by_id
        difficulties = service.recurring_difficulties(LEARNER)
        for item in difficulties.items:
            for occurrence in item.occurrence_history:
                assert occurrence.evidence_ref in evidence_by_id
                assert (
                    check_provenance_completeness(
                        evidence_by_id[occurrence.evidence_ref].provenance
                    ).complete
                    is True
                )

    def test_bounded_non_normative_language(self, service) -> None:
        payloads = [
            service.recurring_difficulties(LEARNER).model_dump(mode="python"),
            service.strengths(LEARNER).model_dump(mode="python"),
            service.stable_recently(LEARNER).model_dump(mode="python"),
            service.proficiency_context(LEARNER).model_dump(mode="python"),
        ]
        for payload in payloads:
            assert SCANNER.scan_mapping(payload, documentation=True) == []
        labels = [
            service.observation_status(LEARNER, "SVA-01").label,
            service.observation_status(LEARNER, "CONN-01").label,
        ]
        for label in labels:
            assert SCANNER.scan_text(label, documentation=False) == []
