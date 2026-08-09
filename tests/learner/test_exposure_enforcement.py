"""Exposure-class enforcement, fail-closed (LEARNER-FOUNDATION WU-D)."""

from __future__ import annotations

import pytest

from app.learner.evidence import (
    EvidenceAdmissionRecord,
    EvidenceAdmissionStatus,
    ProvenanceChain,
)
from app.learner.exposure import (
    DISPLAY_POLICY_OPT_IN_EXISTS,
    ExposureClass,
    ExposureEnforcementResult,
    ExposureEnforcer,
    ExposureEnvelope,
    GateRecord,
    O2Gate,
    O2Qualification,
    layer_permitted,
    qualify_diagnostic_only,
    resolve_displayable,
)
from app.shared.vocabularies import EpistemicStatus


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


def admission(status: EvidenceAdmissionStatus = EvidenceAdmissionStatus.ADMISSIBLE,
              reasons: list[str] | None = None) -> EvidenceAdmissionRecord:
    return EvidenceAdmissionRecord(
        artifact_id="ART-0001",
        status=status,
        reasons=[] if status == EvidenceAdmissionStatus.ADMISSIBLE else (reasons or ["test reason"]),
        provenance=provenance(),
    )


def envelope(**overrides) -> ExposureEnvelope:
    values = {
        "artifact_id": "ART-0001",
        "artifact_version": "feature-comparison-v0.1.0",
        "admissibility_record": admission(),
        "feature_set_version": "feature-set-v0.1.0",
        "required_feature_set_version": "feature-set-v0.1.0",
        "provenance": provenance(),
        "n_effective": 150,
    }
    values.update(overrides)
    return ExposureEnvelope(**values)


def all_gates_passed() -> list[GateRecord]:
    return [
        GateRecord(gate=gate, passed=True, evidence=[f"evidence-{gate.value}"])
        for gate in O2Gate
    ]


class TestExposureClasses:
    def test_exactly_five_classes(self) -> None:
        assert {c.value for c in ExposureClass} == {
            "research_only",
            "diagnostic_only",
            "displayable",
            "hidden",
            "unavailable",
        }

    def test_only_displayable_is_learner_facing(self) -> None:
        from app.learner.evidence import LEARNER_FACING_CLASSES

        assert LEARNER_FACING_CLASSES == {"displayable"}


class TestO2Qualification:
    def test_no_records_fails_closed(self) -> None:
        result = qualify_diagnostic_only([])
        assert not result.qualified
        assert len(result.missing_gates) == 8

    def test_missing_single_record_fails(self) -> None:
        records = [GateRecord(gate=gate, passed=True, evidence=["e"]) for gate in O2Gate]
        records = [r for r in records if r.gate != O2Gate.G5]
        result = qualify_diagnostic_only(records)
        assert not result.qualified
        assert result.missing_gates == ["G5"]

    def test_failed_gate_record_fails_qualification(self) -> None:
        records = [r for r in all_gates_passed() if r.gate != O2Gate.G1]
        records.append(GateRecord(
            gate=O2Gate.G1, passed=False, evidence=["licensing classification missing"],
        ))
        result = qualify_diagnostic_only(records)
        assert not result.qualified
        assert result.failed_gates == ["G1"]

    def test_all_gates_pass_qualifies(self) -> None:
        result = qualify_diagnostic_only(all_gates_passed())
        assert result.qualified
        assert result.passed_gates == [g.value for g in O2Gate]

    def test_gate_criteria_covers_all_eight(self) -> None:
        from app.learner.exposure import O2_GATE_CRITERIA

        assert set(O2_GATE_CRITERIA) == set(O2Gate)


class TestO1DefaultFailClosed:
    def test_no_gate_records_resolves_research_only(self) -> None:
        result = ExposureEnforcer().enforce(envelope())
        assert result.exposure_class == ExposureClass.RESEARCH_ONLY
        assert not result.diagnostic_eligible
        assert not result.reject

    def test_incomplete_gates_stay_research_only(self) -> None:
        records = all_gates_passed()[:-1]
        result = ExposureEnforcer().enforce(envelope(), gate_records=records)
        assert result.exposure_class == ExposureClass.RESEARCH_ONLY
        assert not result.diagnostic_eligible

    def test_complete_gates_resolve_diagnostic_only(self) -> None:
        result = ExposureEnforcer().enforce(envelope(), gate_records=all_gates_passed())
        assert result.exposure_class == ExposureClass.DIAGNOSTIC_ONLY
        assert result.diagnostic_eligible

    def test_stated_higher_class_is_downgraded_never_upgraded(self) -> None:
        result = ExposureEnforcer().enforce(
            envelope(stated_exposure_class=ExposureClass.DIAGNOSTIC_ONLY),
        )
        assert result.exposure_class == ExposureClass.RESEARCH_ONLY
        assert not result.diagnostic_eligible
        assert any("downgraded" in reason for reason in result.reasons)

    def test_below_floor_aggregate_not_diagnostic_eligible(self) -> None:
        result = ExposureEnforcer().enforce(
            envelope(n_effective=29), gate_records=all_gates_passed(),
        )
        assert result.exposure_class == ExposureClass.RESEARCH_ONLY
        assert not result.diagnostic_eligible


class TestDisplayableFailClosed:
    def test_no_display_policy_opt_in_exists(self) -> None:
        assert DISPLAY_POLICY_OPT_IN_EXISTS is False

    def test_resolve_displayable_returns_none_without_opt_in(self) -> None:
        assert resolve_displayable() is None
        assert resolve_displayable(display_policy_opt_in=False) is None

    def test_stated_displayable_is_rejected(self) -> None:
        result = ExposureEnforcer().enforce(
            envelope(stated_exposure_class=ExposureClass.DISPLAYABLE),
        )
        assert result.reject
        assert result.exposure_class == ExposureClass.UNAVAILABLE
        assert any("displayable" in reason for reason in result.reasons)


class TestUnavailableTerminal:
    def test_unknown_artifact_is_unavailable(self) -> None:
        result = ExposureEnforcer(known_artifact_ids={"ART-0001"}).enforce(
            envelope(artifact_id="ART-9999"),
        )
        assert result.exposure_class == ExposureClass.UNAVAILABLE
        assert result.reject

    def test_missing_admissibility_record_is_rejected(self) -> None:
        result = ExposureEnforcer().enforce(envelope(admissibility_record=None))
        assert result.reject
        assert result.exposure_class == ExposureClass.UNAVAILABLE

    def test_invalid_admissibility_is_never_usable(self) -> None:
        result = ExposureEnforcer().enforce(
            envelope(admissibility_record=admission(EvidenceAdmissionStatus.INVALID)),
        )
        assert result.reject

    def test_unavailable_admissibility_is_terminal_no_widening(self) -> None:
        result = ExposureEnforcer().enforce(
            envelope(admissibility_record=admission(EvidenceAdmissionStatus.UNAVAILABLE)),
            gate_records=all_gates_passed(),
        )
        assert result.reject
        assert result.exposure_class == ExposureClass.UNAVAILABLE

    def test_feature_set_mismatch_is_unavailable(self) -> None:
        result = ExposureEnforcer().enforce(
            envelope(
                feature_set_version="feature-set-v0.1.0",
                required_feature_set_version="feature-set-v0.2.0",
            ),
        )
        assert result.reject
        assert result.exposure_class == ExposureClass.UNAVAILABLE


class TestLayerCompatibility:
    def test_l0_l1_only_on_research_and_diagnostic(self) -> None:
        assert layer_permitted(ExposureClass.RESEARCH_ONLY, EpistemicStatus.OBSERVED_DESCRIPTIVE)
        assert layer_permitted(ExposureClass.DIAGNOSTIC_ONLY, EpistemicStatus.GATED_INFERENCE)
        assert not layer_permitted(ExposureClass.RESEARCH_ONLY, EpistemicStatus.RECOMMENDATION)

    def test_displayable_is_l0_only(self) -> None:
        assert layer_permitted(ExposureClass.DISPLAYABLE, EpistemicStatus.OBSERVED_DESCRIPTIVE)
        assert not layer_permitted(ExposureClass.DISPLAYABLE, EpistemicStatus.GATED_INFERENCE)

    def test_unavailable_permits_no_layer(self) -> None:
        assert not layer_permitted(ExposureClass.UNAVAILABLE, EpistemicStatus.OBSERVED_DESCRIPTIVE)

    def test_illegal_layer_rejected(self) -> None:
        result = ExposureEnforcer().enforce(
            envelope(epistemic_status=EpistemicStatus.RECOMMENDATION),
        )
        assert result.reject


class TestEnvelopeProvenance:
    def test_missing_provenance_reported(self) -> None:
        from app.learner.exposure import check_envelope_provenance

        assert check_envelope_provenance(envelope(provenance=None)) == [
            "G4: provenance chain missing",
        ]
        assert check_envelope_provenance(envelope()) == []
