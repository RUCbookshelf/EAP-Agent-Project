"""Longitudinal learner model service tests (Goal PDW2-B-LEARNER-MODEL)."""

from __future__ import annotations

import pytest

from app.learner.evidence import EvidenceAdmissionStatus
from app.learner.wave2.models import (
    HistoryState,
    ObservationType,
    RevisionResponseState,
    StabilityKind,
)
from app.learner.wave2.repository import InMemoryObservationRepository
from app.learner.wave2.services import LongitudinalLearnerService
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


NOW = utc(2026, 8, 20, 12)


def build_service() -> LongitudinalLearnerService:
    service = LongitudinalLearnerService(
        InMemoryObservationRepository(), now=lambda: NOW,
    )
    return service


def seed_two_occurrence_difficulty(
    service: LongitudinalLearnerService, learner_id: str = "L-001",
) -> None:
    service.record_submission_sample(make_sample("S-001", learner_id, "T-01", utc(2026, 7, 1)))
    service.record_submission_sample(make_sample("S-002", learner_id, "T-02", utc(2026, 7, 15)))
    service.admit_evidence(learner_id, make_evidence("E-101", learner_id, utc(2026, 7, 1)))
    service.admit_evidence(learner_id, make_evidence("E-102", learner_id, utc(2026, 7, 15)))
    service.record_observation(make_observation(
        "SVA-01", learner_id, ObservationType.DIFFICULTY,
        "SVA-001", "subject-verb agreement",
        [
            make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1)),
            make_occurrence("OC-2", "E-102", "T-02", utc(2026, 7, 15)),
        ],
    ))
    service.record_revision_behavior(make_behavior(
        "B-01", learner_id, "SVA-01", "R-01",
        RevisionResponseState.CORRECTED_AFTER_FEEDBACK, utc(2026, 7, 2),
    ))
    service.record_revision_behavior(make_behavior(
        "B-02", learner_id, "SVA-01", "R-02",
        RevisionResponseState.REAPPEARED_LATER, utc(2026, 7, 16),
    ))


class TestObservationStatus:
    def test_appeared_before_and_prior_count(self) -> None:
        service = build_service()
        seed_two_occurrence_difficulty(service)
        view = service.observation_status("L-001", "SVA-01")
        assert view is not None
        assert view.appeared_before is True
        assert view.prior_occurrence_count == 1
        assert view.occurrence_count == 2

    def test_single_occurrence_is_insufficient_history(self) -> None:
        service = build_service()
        service.record_observation(make_observation(
            "ART-01", "L-001", ObservationType.DIFFICULTY,
            "ART-001", "article usage",
            [make_occurrence("OC-9", "E-301", "T-01", utc(2026, 7, 1))],
        ))
        view = service.observation_status("L-001", "ART-01")
        assert view is not None
        assert view.appeared_before is False
        assert view.history_state is HistoryState.INSUFFICIENT_HISTORY
        assert view.history_reasons

    def test_contexts_are_unique_and_chronological(self) -> None:
        service = build_service()
        seed_two_occurrence_difficulty(service)
        view = service.observation_status("L-001", "SVA-01")
        assert view is not None
        assert view.contexts == ["T-01", "T-02"]

    def test_revision_response_is_latest_behavior_state(self) -> None:
        service = build_service()
        seed_two_occurrence_difficulty(service)
        view = service.observation_status("L-001", "SVA-01")
        assert view is not None
        assert view.revision_response is RevisionResponseState.REAPPEARED_LATER

    def test_no_revision_evidence_is_default(self) -> None:
        service = build_service()
        service.record_observation(make_observation(
            "TEN-01", "L-001", ObservationType.DIFFICULTY,
            "TEN-001", "tense consistency",
            [
                make_occurrence("OC-3", "E-401", "T-01", utc(2026, 7, 1)),
                make_occurrence("OC-4", "E-402", "T-02", utc(2026, 7, 15)),
            ],
        ))
        view = service.observation_status("L-001", "TEN-01")
        assert view is not None
        assert view.revision_response is RevisionResponseState.NO_REVISION_EVIDENCE
        assert view.addressed_in_prior_revision is False

    def test_addressed_in_prior_revision_requires_behavior_before_last_occurrence(self) -> None:
        service = build_service()
        seed_two_occurrence_difficulty(service)
        view = service.observation_status("L-001", "SVA-01")
        assert view is not None
        assert view.addressed_in_prior_revision is True

        late = build_service()
        late.record_observation(make_observation(
            "SVA-02", "L-001", ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [make_occurrence("OC-5", "E-101", "T-01", utc(2026, 7, 1))],
        ))
        late.record_revision_behavior(make_behavior(
            "B-99", "L-001", "SVA-02", "R-99",
            RevisionResponseState.CORRECTED_AFTER_FEEDBACK, utc(2026, 7, 10),
        ))
        late_view = late.observation_status("L-001", "SVA-02")
        assert late_view is not None
        assert late_view.addressed_in_prior_revision is False

    def test_days_since_last_observed_uses_injected_clock(self) -> None:
        service = build_service()
        seed_two_occurrence_difficulty(service)
        view = service.observation_status("L-001", "SVA-01")
        assert view is not None
        assert view.last_observed_at == utc(2026, 7, 15)
        assert view.days_since_last_observed == (NOW - utc(2026, 7, 15)).days

    def test_unknown_observation_returns_none(self) -> None:
        service = build_service()
        assert service.observation_status("L-001", "missing") is None


class TestFrequency:
    def test_qualified_frequency_over_recent_window(self) -> None:
        service = build_service()
        seed_two_occurrence_difficulty(service)
        service.record_submission_sample(make_sample("S-003", "L-001", "T-03", utc(2026, 8, 1)))
        view = service.observation_status("L-001", "SVA-01")
        assert view is not None
        assert view.frequency.qualified_occurrence_count == 2
        assert view.frequency.qualified_sample_count == 3
        assert view.frequency.window_size == 3
        assert view.frequency.descriptive_proportion == pytest.approx(2 / 3)
        assert view.frequency.history_state is HistoryState.SUFFICIENT

    def test_no_qualified_samples_is_insufficient(self) -> None:
        service = build_service()
        service.record_observation(make_observation(
            "SVA-01", "L-001", ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1))],
        ))
        view = service.observation_status("L-001", "SVA-01")
        assert view is not None
        assert view.frequency.history_state is HistoryState.INSUFFICIENT_HISTORY
        assert view.frequency.qualified_sample_count == 0
        assert view.frequency.descriptive_proportion is None

    def test_single_qualified_sample_is_insufficient(self) -> None:
        service = build_service()
        service.record_submission_sample(make_sample("S-001", "L-001", "T-01", utc(2026, 7, 1)))
        service.record_observation(make_observation(
            "SVA-01", "L-001", ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1))],
        ))
        view = service.observation_status("L-001", "SVA-01")
        assert view is not None
        assert view.frequency.history_state is HistoryState.INSUFFICIENT_HISTORY
        assert "2 qualified" in view.frequency.history_reasons[0]


class TestRecurringDifficulties:
    def test_recurring_difficulty_fields(self) -> None:
        service = build_service()
        seed_two_occurrence_difficulty(service)
        result = service.recurring_difficulties("L-001")
        assert result.history_state is HistoryState.SUFFICIENT
        assert [item.observation_id for item in result.items] == ["SVA-01"]
        difficulty = result.items[0]
        assert difficulty.occurrence_count == 2
        assert [o.occurrence_id for o in difficulty.occurrence_history] == ["OC-1", "OC-2"]
        assert difficulty.revision_response is RevisionResponseState.REAPPEARED_LATER
        assert difficulty.addressed_in_prior_revision is True
        assert difficulty.claims_status == "observation_only"

    def test_min_occurrences_filter(self) -> None:
        service = build_service()
        service.record_observation(make_observation(
            "ART-01", "L-001", ObservationType.DIFFICULTY,
            "ART-001", "article usage",
            [make_occurrence("OC-9", "E-301", "T-01", utc(2026, 7, 1))],
        ))
        result = service.recurring_difficulties("L-001", min_occurrences=2)
        assert result.items == []
        assert result.history_state is HistoryState.INSUFFICIENT_HISTORY

    def test_no_observations_is_insufficient_history(self) -> None:
        service = build_service()
        result = service.recurring_difficulties("L-001")
        assert result.items == []
        assert result.history_state is HistoryState.INSUFFICIENT_HISTORY


class TestStrengths:
    def test_strength_with_positive_history_is_sufficient(self) -> None:
        service = build_service()
        service.record_observation(make_observation(
            "CONN-01", "L-001", ObservationType.STRENGTH,
            "CONN-RNG", "connective range",
            [
                make_occurrence("OC-10", "E-201", "T-02", utc(2026, 7, 15)),
                make_occurrence("OC-11", "E-202", "T-03", utc(2026, 8, 1)),
            ],
        ))
        result = service.strengths("L-001")
        assert [item.observation_id for item in result.items] == ["CONN-01"]
        assert result.items[0].history_state is HistoryState.SUFFICIENT
        assert result.items[0].occurrence_count == 2

    def test_single_strength_observation_is_explicit_insufficient(self) -> None:
        service = build_service()
        service.record_observation(make_observation(
            "CONN-02", "L-001", ObservationType.STRENGTH,
            "CONN-RNG", "connective range",
            [make_occurrence("OC-12", "E-203", "T-01", utc(2026, 7, 1))],
        ))
        result = service.strengths("L-001")
        assert result.items[0].history_state is HistoryState.INSUFFICIENT_HISTORY
        assert result.items[0].history_reasons


class TestStableRecently:
    def _seed_recurring_difficulty_with_clean_recent_window(
        self, service: LongitudinalLearnerService,
    ) -> None:
        for submission_id, task, at in (
            ("S-001", "T-01", utc(2026, 7, 1)),
            ("S-002", "T-02", utc(2026, 7, 15)),
            ("S-003", "T-03", utc(2026, 8, 1)),
            ("S-004", "T-04", utc(2026, 8, 8)),
        ):
            service.record_submission_sample(
                make_sample(submission_id, "L-001", task, at)
            )
        service.record_observation(make_observation(
            "SVA-01", "L-001", ObservationType.DIFFICULTY,
            "SVA-001", "subject-verb agreement",
            [
                make_occurrence("OC-1", "E-101", "T-01", utc(2026, 7, 1)),
                make_occurrence("OC-2", "E-102", "T-02", utc(2026, 7, 15)),
            ],
        ))

    def test_previously_recurring_issue_not_observed_recently(self) -> None:
        service = build_service()
        self._seed_recurring_difficulty_with_clean_recent_window(service)
        result = service.stable_recently("L-001", recent_window=2)
        stable = next(
            item for item in result.items if item.observation_id == "SVA-01"
        )
        assert (
            stable.stability_kind
            is StabilityKind.PREVIOUSLY_RECURRING_NOT_RECENTLY_OBSERVED
        )
        assert stable.recent_window_occurrence_count == 0
        assert stable.recent_window_sample_count == 2
        assert stable.history_state is HistoryState.SUFFICIENT

    def test_stable_history_state_respects_min_qualified_recent(self) -> None:
        service = build_service()
        self._seed_recurring_difficulty_with_clean_recent_window(service)
        result = service.stable_recently(
            "L-001", recent_window=2, min_qualified_recent=3,
        )
        stable = next(
            item for item in result.items if item.observation_id == "SVA-01"
        )
        assert stable.recent_window_sample_count == 2
        assert stable.history_state is HistoryState.INSUFFICIENT_HISTORY
        assert stable.history_reasons

    def test_observation_in_recent_window_is_not_stable(self) -> None:
        service = build_service()
        self._seed_recurring_difficulty_with_clean_recent_window(service)
        service.record_observation(make_observation(
            "TEN-01", "L-001", ObservationType.DIFFICULTY,
            "TEN-001", "tense consistency",
            [
                make_occurrence("OC-3", "E-401", "T-01", utc(2026, 7, 1)),
                make_occurrence("OC-4", "E-402", "T-03", utc(2026, 8, 1)),
            ],
        ))
        result = service.stable_recently("L-001", recent_window=2)
        assert all(item.observation_id != "TEN-01" for item in result.items)

    def test_strength_with_repeated_positive_history_is_stable(self) -> None:
        service = build_service()
        service.record_observation(make_observation(
            "CONN-01", "L-001", ObservationType.STRENGTH,
            "CONN-RNG", "connective range",
            [
                make_occurrence("OC-10", "E-201", "T-02", utc(2026, 7, 15)),
                make_occurrence("OC-11", "E-202", "T-03", utc(2026, 8, 1)),
            ],
        ))
        result = service.stable_recently("L-001")
        assert any(
            item.observation_id == "CONN-01"
            and item.stability_kind is StabilityKind.STRENGTH_HISTORY
            for item in result.items
        )


class TestProficiencyContext:
    def test_anchors_are_external_and_never_corpus_derived(self) -> None:
        service = build_service()
        service.set_proficiency_context(make_proficiency_context(
            "L-001",
            [
                make_anchor("A-1", "CET-4", "CET-4 passed", utc(2026, 6, 1)),
                make_anchor("A-2", "IELTS", "IELTS 6.0 band", utc(2026, 7, 1)),
            ],
        ))
        view = service.proficiency_context("L-001")
        assert view.history_state is HistoryState.SUFFICIENT
        assert len(view.anchors) == 2
        assert view.derived_from_corpus is False

    def test_missing_context_is_insufficient_history(self) -> None:
        service = build_service()
        view = service.proficiency_context("L-001")
        assert view.history_state is HistoryState.INSUFFICIENT_HISTORY
        assert view.history_reasons
        assert view.anchors == []

    def test_context_without_anchors_is_insufficient_history(self) -> None:
        service = build_service()
        service.set_proficiency_context(make_proficiency_context("L-001"))
        view = service.proficiency_context("L-001")
        assert view.history_state is HistoryState.INSUFFICIENT_HISTORY


class TestCurrentEvidence:
    def test_only_admissible_evidence_with_complete_provenance(self) -> None:
        service = build_service()
        service.admit_evidence("L-001", make_evidence("E-101", "L-001", utc(2026, 7, 1)))
        service.admit_evidence("L-001", make_evidence(
            "E-999", "L-001", utc(2026, 7, 2),
            admission_status=EvidenceAdmissionStatus.LIMITED,
        ))
        result = service.current_evidence("L-001")
        assert [e.evidence.evidence_id for e in result.items] == ["E-101"]
        assert result.excluded_count == 1

    def test_empty_learner_evidence(self) -> None:
        service = build_service()
        result = service.current_evidence("L-001")
        assert result.items == []
        assert result.excluded_count == 0
