"""Wave-2 longitudinal model contract tests (Goal PDW2-B-LEARNER-MODEL)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.learner.normative import NormativeClaimsScanner
from app.learner.wave2.models import (
    ExternalAnchorSystem,
    HistoryState,
    ObservationType,
    ProficiencyContext,
    RevisionBehavior,
    RevisionResponseState,
    StabilityKind,
)
from app.shared.vocabularies import BANNED_LEARNER_LABELS
from tests.learner.wave2_helpers import (
    make_anchor,
    make_behavior,
    make_observation,
    make_occurrence,
    make_proficiency_context,
    utc,
)


SCANNER = NormativeClaimsScanner()


class TestEnumVocabulary:
    def test_wave2_enum_values_never_use_banned_learner_labels(self) -> None:
        values = {s.value for s in ObservationType}
        values |= {s.value for s in RevisionResponseState}
        values |= {s.value for s in HistoryState}
        values |= {s.value for s in StabilityKind}
        values |= {s.value for s in ExternalAnchorSystem}
        assert values.isdisjoint(BANNED_LEARNER_LABELS)

    def test_revision_response_states_are_observation_only(self) -> None:
        assert RevisionResponseState.CORRECTED_AFTER_FEEDBACK.value == "corrected_after_feedback"
        assert RevisionResponseState.PERSISTED_AFTER_REVISION.value == "persisted_after_revision"
        assert RevisionResponseState.REAPPEARED_LATER.value == "reappeared_later"
        assert RevisionResponseState.NO_REVISION_EVIDENCE.value == "no_revision_evidence"

    def test_external_anchor_systems_cover_required_set(self) -> None:
        assert {
            ExternalAnchorSystem.CET4.value,
            ExternalAnchorSystem.CET6.value,
            ExternalAnchorSystem.IELTS.value,
            ExternalAnchorSystem.TOEFL.value,
            ExternalAnchorSystem.OTHER.value,
        } == {"CET-4", "CET-6", "IELTS", "TOEFL", "OTHER"}


class TestObservationRecord:
    def test_minimal_record_validates(self) -> None:
        record = make_observation(
            observation_id="SVA-01",
            learner_id="L-001",
            observation_type=ObservationType.DIFFICULTY,
            code="SVA-001",
            label="subject-verb agreement",
            occurrences=[
                make_occurrence(
                    "OC-1", "E-101", "T-01", utc(2026, 7, 1),
                )
            ],
        )
        assert record.occurrences[0].qualified is True

    def test_occurrence_requires_evidence_ref_and_context(self) -> None:
        with pytest.raises(ValidationError):
            make_occurrence("OC-1", "", "T-01", utc(2026, 7, 1))
        with pytest.raises(ValidationError):
            make_occurrence("OC-1", "E-101", "", utc(2026, 7, 1))

    def test_labels_are_strict_scan_clean(self) -> None:
        record = make_observation(
            observation_id="SVA-01",
            learner_id="L-001",
            observation_type=ObservationType.DIFFICULTY,
            code="SVA-001",
            label="subject-verb agreement",
            occurrences=[],
        )
        assert SCANNER.scan_text(record.label, documentation=False) == []
        assert SCANNER.scan_text(record.code, documentation=False) == []


class TestRevisionBehavior:
    def test_behavior_record_is_observation_only(self) -> None:
        behavior = make_behavior(
            "B-01", "L-001", "SVA-01", "R-01",
            RevisionResponseState.CORRECTED_AFTER_FEEDBACK, utc(2026, 7, 2),
        )
        assert behavior.state is RevisionResponseState.CORRECTED_AFTER_FEEDBACK
        assert behavior.evidence_refs == ["E-B-01"]
        assert SCANNER.scan_text(behavior.state.value, documentation=False) == []


class TestProficiencyContext:
    def test_anchors_may_never_be_corpus_derived(self) -> None:
        context = make_proficiency_context(
            "L-001",
            [make_anchor("A-1", ExternalAnchorSystem.CET4, "CET-4 passed", utc(2026, 6, 1))],
        )
        assert context.derived_from_corpus is False

    def test_corpus_derived_flag_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProficiencyContext(
                learner_id="L-001",
                anchors=[],
                derived_from_corpus=True,
            )

    def test_default_statement_scans_clean_strict(self) -> None:
        context = make_proficiency_context("L-001")
        assert SCANNER.scan_text(context.statement, documentation=False) == []
