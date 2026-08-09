"""Evidence-record typing and admission contracts (LEARNER-FOUNDATION).

Covers: typed source-event/observed-evidence record contracts (ADR-03
concept), provenance fields (event id, time, actor, source,
evidence-admission status, policy/model/config version), admission
precedence (WU-D F14 / N6), and the four epistemic layers staying distinct
with downgrade-only semantics (D-09).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.learner.evidence import (
    ADMISSION_PRECEDENCE,
    EvidenceAdmissionRecord,
    EvidenceAdmissionStatus,
    ObservedEvidence,
    ProvenanceChain,
    SourceEvent,
    SourceEventType,
    admission_downgrade_allowed,
    check_provenance_completeness,
    effective_admission_status,
    epistemic_downgrade_allowed,
)
from app.shared.vocabularies import EpistemicStatus


def source_event(**overrides) -> SourceEvent:
    values = {
        "event_id": "EV000001",
        "event_type": SourceEventType.SUBMISSION_EVIDENCE,
        "occurred_at": datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
        "actor": "learner",
        "source": "E000042",
        "policy_version": "feedback-policy-v0.1.0",
        "model_version": None,
        "config_version": "config-v0.9.0",
        "payload": {"word_count": 412},
    }
    values.update(overrides)
    return SourceEvent(**values)


def provenance(**overrides) -> ProvenanceChain:
    values = {
        "source_package": "corpus-sweccl2-research-v0.1.0",
        "manifest_hash": "6B19C27F",
        "feature_set_version": "feature-set-v0.1.0",
        "reference_group_version": "RG-014-v0.1.0",
        "distribution_version": "dist-v0.1.0",
        "processing_version": "comparison-engine-v0.1.0",
        "algorithm_version": "comparison-algorithm-v0.1.0",
        "effective_n": 150,
        "availability": "available",
    }
    values.update(overrides)
    return ProvenanceChain(**values)


def admission_record(**overrides) -> EvidenceAdmissionRecord:
    values = {
        "artifact_id": "ART-0001",
        "status": EvidenceAdmissionStatus.ADMISSIBLE,
        "reasons": [],
        "provenance": provenance(),
    }
    values.update(overrides)
    return EvidenceAdmissionRecord(**values)


class TestSourceEventTyping:
    def test_typed_contract_carries_adr03_provenance_fields(self) -> None:
        event = source_event()
        assert event.event_id == "EV000001"
        assert event.policy_version == "feedback-policy-v0.1.0"
        assert event.config_version == "config-v0.9.0"
        assert event.admission_status == EvidenceAdmissionStatus.ADMISSIBLE
        assert event.actor == "learner"
        assert event.source == "E000042"
        assert event.event_type == SourceEventType.SUBMISSION_EVIDENCE

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SourceEvent(**{**source_event().model_dump(), "unexpected": True})

    def test_required_fields_enforced(self) -> None:
        with pytest.raises(ValidationError):
            SourceEvent(event_id="", event_type=SourceEventType.SUBMISSION_EVIDENCE,
                        occurred_at=datetime.now(timezone.utc), actor="", source="")


class TestObservedEvidenceTyping:
    def test_observed_evidence_is_typed_and_provenance_linked(self) -> None:
        evidence = ObservedEvidence(
            evidence_id="OE000001",
            source_event_id="EV000001",
            evidence_type="metric_value",
            observed_at=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
            provenance=provenance(),
            value={"word_count": 412},
        )
        assert evidence.epistemic_status == EpistemicStatus.OBSERVED_DESCRIPTIVE
        assert evidence.admission_status == EvidenceAdmissionStatus.ADMISSIBLE
        assert evidence.exposure_class.value == "research_only"  # O1 default

    def test_l2_or_l3_never_rides_observed_evidence(self) -> None:
        with pytest.raises(ValidationError):
            ObservedEvidence(
                evidence_id="OE000002",
                source_event_id="EV000001",
                evidence_type="metric_value",
                observed_at=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
                epistemic_status=EpistemicStatus.OUTCOME_CLAIM,
                provenance=provenance(),
            )

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ObservedEvidence(**{
                **ObservedEvidence(
                    evidence_id="OE000003",
                    source_event_id="EV000001",
                    evidence_type="metric_value",
                    observed_at=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
                    provenance=provenance(),
                ).model_dump(),
                "unexpected": True,
            })


class TestAdmissionPrecedence:
    def test_precedence_order_invalid_first(self) -> None:
        assert ADMISSION_PRECEDENCE[0] == EvidenceAdmissionStatus.INVALID
        assert ADMISSION_PRECEDENCE[1] == EvidenceAdmissionStatus.UNAVAILABLE
        assert ADMISSION_PRECEDENCE[2] == EvidenceAdmissionStatus.LIMITED

    def test_effective_status_invalid_dominates(self) -> None:
        statuses = [
            EvidenceAdmissionStatus.ADMISSIBLE,
            EvidenceAdmissionStatus.LIMITED,
            EvidenceAdmissionStatus.INVALID,
        ]
        assert effective_admission_status(statuses) == EvidenceAdmissionStatus.INVALID

    def test_effective_status_unavailable_before_limited(self) -> None:
        statuses = [EvidenceAdmissionStatus.ADMISSIBLE, EvidenceAdmissionStatus.LIMITED,
                    EvidenceAdmissionStatus.UNAVAILABLE]
        assert effective_admission_status(statuses) == EvidenceAdmissionStatus.UNAVAILABLE

    def test_effective_status_all_admissible(self) -> None:
        statuses = [EvidenceAdmissionStatus.ADMISSIBLE, EvidenceAdmissionStatus.ADMISSIBLE]
        assert effective_admission_status(statuses) == EvidenceAdmissionStatus.ADMISSIBLE

    def test_downgrade_only(self) -> None:
        assert admission_downgrade_allowed(
            EvidenceAdmissionStatus.ADMISSIBLE, EvidenceAdmissionStatus.LIMITED,
        )
        assert admission_downgrade_allowed(
            EvidenceAdmissionStatus.LIMITED, EvidenceAdmissionStatus.UNAVAILABLE,
        )
        assert not admission_downgrade_allowed(
            EvidenceAdmissionStatus.UNAVAILABLE, EvidenceAdmissionStatus.ADMISSIBLE,
        )

    def test_limited_record_requires_reasons(self) -> None:
        with pytest.raises(ValidationError):
            admission_record(status=EvidenceAdmissionStatus.LIMITED, reasons=[])


class TestProvenanceCompleteness:
    def test_corpus_aggregate_requires_full_g4_chain(self) -> None:
        complete = check_provenance_completeness(provenance(), corpus_aggregate=True)
        assert complete.complete
        assert complete.missing == []

    def test_missing_manifest_hash_fails_closed(self) -> None:
        # Model typing rejects empty strings at construction; simulate the
        # mutated/legacy record case to prove the completeness check fails
        # closed on an empty mandatory field.
        chain = provenance().model_copy(update={"manifest_hash": ""})
        result = check_provenance_completeness(chain, corpus_aggregate=True)
        assert not result.complete
        assert result.missing == ["manifest_hash"]

    def test_missing_effective_n_fails_corpus_aggregate_only(self) -> None:
        chain = provenance(effective_n=None)
        assert not check_provenance_completeness(chain, corpus_aggregate=True).complete
        assert check_provenance_completeness(chain, corpus_aggregate=False).complete

    def test_minimum_chain_is_enough_for_learner_side_records(self) -> None:
        chain = ProvenanceChain(
            source_package="learner-analysis-v0.1.0",
            manifest_hash="abc123",
            processing_version="analyzer-basic-v0.1",
            availability="available",
        )
        assert check_provenance_completeness(chain, corpus_aggregate=False).complete


class TestEpistemicLayersDistinct:
    def test_four_layers_in_order(self) -> None:
        from app.learner.evidence import EPISTEMIC_LAYER_ORDER

        assert [s.value for s in EPISTEMIC_LAYER_ORDER] == [
            "observed_descriptive",
            "gated_inference",
            "recommendation",
            "outcome_claim",
        ]

    def test_downgrade_only_display(self) -> None:
        assert epistemic_downgrade_allowed(
            EpistemicStatus.RECOMMENDATION, EpistemicStatus.OBSERVED_DESCRIPTIVE,
        )
        assert not epistemic_downgrade_allowed(
            EpistemicStatus.OBSERVED_DESCRIPTIVE, EpistemicStatus.OUTCOME_CLAIM,
        )

    def test_observed_evidence_never_equals_recommendation(self) -> None:
        evidence = ObservedEvidence(
            evidence_id="OE000004",
            source_event_id="EV000001",
            evidence_type="metric_value",
            observed_at=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
            provenance=provenance(),
        )
        assert evidence.epistemic_status != EpistemicStatus.RECOMMENDATION
        assert evidence.epistemic_status != EpistemicStatus.OUTCOME_CLAIM
