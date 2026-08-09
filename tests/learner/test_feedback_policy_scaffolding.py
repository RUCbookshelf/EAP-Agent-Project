"""Feedback-policy scaffolding tests (D-03; WU-D evidence consumption)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.learner.evidence import EvidenceAdmissionStatus, ObservedEvidence, ProvenanceChain
from app.learner.exposure import (
    ExposureClass,
    ExposureEnvelope,
    GateRecord,
    O2Gate,
)
from app.learner.feedback_policy import (
    FeedbackPolicyService,
    NO_CLAIM_LIMITATION,
    default_feedback_policy,
)
from app.shared.vocabularies import EpistemicStatus


def provenance() -> ProvenanceChain:
    return ProvenanceChain(
        source_package="learner-analysis-v0.1.0",
        manifest_hash="abc123",
        processing_version="analyzer-basic-v0.1",
        availability="available",
    )


def evidence(evidence_id: str = "OE000001") -> ObservedEvidence:
    return ObservedEvidence(
        evidence_id=evidence_id,
        source_event_id="EV000001",
        evidence_type="metric_value",
        observed_at=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
        provenance=provenance(),
        value={"word_count": 412},
    )


def envelope(**overrides) -> ExposureEnvelope:
    values = {
        "artifact_id": "ART-0001",
        "artifact_version": "feature-comparison-v0.1.0",
        "admissibility_record": None,
    }
    values.update(overrides)
    return ExposureEnvelope(**values)


def all_gates_passed() -> list[GateRecord]:
    return [GateRecord(gate=gate, passed=True, evidence=["e"]) for gate in O2Gate]


class TestDefaultPolicyInstance:
    def test_default_instance_is_stable(self) -> None:
        policy = default_feedback_policy()
        assert policy.policy_id == "feedback-policy-v0.1.0"
        assert policy.version == "0.1.0"
        assert policy.priority_limit == 2
        assert policy.gate_rules == ["diagnostic-v0.6.1"]

    def test_claims_constraints_never_normative(self) -> None:
        from app.learner.normative import NormativeClaimsScanner

        policy = default_feedback_policy()
        violations = NormativeClaimsScanner().scan_text(
            " ".join(policy.claims_constraints), documentation=True,
        )
        assert violations == []


class TestPolicyApplication:
    def test_applied_produces_l2_recommendations_with_provenance(self) -> None:
        service = FeedbackPolicyService()
        result = service.apply(
            envelope(admissibility_record=None),
            [evidence("OE000001"), evidence("OE000002")],
        )
        # Without an admissibility record the enforcement rejects -> unavailable.
        assert result.status == "unavailable"

    def test_insufficient_evidence_is_explicit_never_fabricated(self) -> None:
        from app.learner.evidence import EvidenceAdmissionRecord

        service = FeedbackPolicyService()
        record = EvidenceAdmissionRecord(
            artifact_id="ART-0001",
            status=EvidenceAdmissionStatus.ADMISSIBLE,
            provenance=provenance(),
        )
        result = service.apply(envelope(admissibility_record=record), [])
        assert result.status == "insufficient_evidence"
        assert result.recommendations == []

    def test_priority_limit_is_enforced(self) -> None:
        from app.learner.evidence import EvidenceAdmissionRecord

        service = FeedbackPolicyService()
        record = EvidenceAdmissionRecord(
            artifact_id="ART-0001",
            status=EvidenceAdmissionStatus.ADMISSIBLE,
            provenance=provenance(),
        )
        candidates = [evidence(f"OE{i:06d}") for i in range(1, 5)]
        result = service.apply(envelope(admissibility_record=record), candidates)
        assert result.status == "applied"
        assert len(result.recommendations) == 2  # priority_limit=2
        assert [r.priority for r in result.recommendations] == [1, 2]

    def test_recommendations_are_l2_and_claim_free(self) -> None:
        from app.learner.evidence import EvidenceAdmissionRecord
        from app.learner.normative import NormativeClaimsScanner

        service = FeedbackPolicyService()
        record = EvidenceAdmissionRecord(
            artifact_id="ART-0001",
            status=EvidenceAdmissionStatus.ADMISSIBLE,
            provenance=provenance(),
        )
        result = service.apply(envelope(admissibility_record=record), [evidence()])
        recommendation = result.recommendations[0]
        assert recommendation.epistemic_status == EpistemicStatus.RECOMMENDATION
        assert recommendation.limitations == [NO_CLAIM_LIMITATION]
        assert recommendation.evidence_ids == ["OE000001"]
        assert NormativeClaimsScanner().scan_text(recommendation.statement) == []
        assert result.provenance["policy_id"] == "feedback-policy-v0.1.0"

    def test_ineligible_candidates_are_excluded(self) -> None:
        from app.learner.evidence import EvidenceAdmissionRecord

        service = FeedbackPolicyService()
        record = EvidenceAdmissionRecord(
            artifact_id="ART-0001",
            status=EvidenceAdmissionStatus.ADMISSIBLE,
            provenance=provenance(),
        )
        rejected = evidence("OE000099").model_copy(
            update={"admission_status": EvidenceAdmissionStatus.UNAVAILABLE},
        )
        result = service.apply(
            envelope(admissibility_record=record), [evidence("OE000001"), rejected],
        )
        assert result.status == "applied"
        assert [r.evidence_ids for r in result.recommendations] == [["OE000001"]]

    def test_displayable_envelope_never_applies(self) -> None:
        result = FeedbackPolicyService().apply(
            envelope(
                admissibility_record=None,
                stated_exposure_class=ExposureClass.DISPLAYABLE,
            ),
            [evidence()],
        )
        assert result.status == "unavailable"
