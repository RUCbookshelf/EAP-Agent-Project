"""LEARNER mirror of the WU-D machine contract (drift protection).

The exposure classes, O2 gates, admissibility statuses, and epistemic layers
implemented by the learner foundation must exactly mirror the CORPUS-owned
WU-D machine contract when it is present in the sibling corpus worktree.
When the contract file is absent (e.g., a CI checkout without sibling
worktrees), the frozen expected values below still guard drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.learner.evidence import EvidenceAdmissionStatus, ExposureClass
from app.learner.exposure import O2Gate, qualify_diagnostic_only
from app.shared.vocabularies import EpistemicStatus


WU_D_CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "corpus" / "docs" / "corpus-intelligence" / "l2" / "data"
    / "wu_d_diagnostic_gating_contract.json"
)


@pytest.fixture(scope="module")
def wu_d_contract() -> dict:
    if not WU_D_CONTRACT.exists():
        pytest.skip("WU-D machine contract not present in this checkout")
    return json.loads(WU_D_CONTRACT.read_text(encoding="utf-8"))


class TestExposureClassMirror:
    def test_classes_match(self, wu_d_contract: dict) -> None:
        contract_classes = {item["class"] for item in wu_d_contract["exposure_classes"]}
        assert contract_classes == {cls.value for cls in ExposureClass}

    def test_learner_facing_flag_matches(self, wu_d_contract: dict) -> None:
        learner_facing = {
            item["class"] for item in wu_d_contract["exposure_classes"]
            if item["learner_facing"]
        }
        assert learner_facing == {"displayable"}

    def test_frozen_class_set(self) -> None:
        assert {cls.value for cls in ExposureClass} == {
            "research_only",
            "diagnostic_only",
            "displayable",
            "hidden",
            "unavailable",
        }


class TestGateMirror:
    def test_gates_match(self, wu_d_contract: dict) -> None:
        contract_gates = {item["gate"] for item in wu_d_contract["qualification_gates"]}
        assert contract_gates == {gate.value for gate in O2Gate}

    def test_all_gates_required_for_qualification(self, wu_d_contract: dict) -> None:
        records = [g for g in O2Gate]
        qualification = qualify_diagnostic_only([])
        assert not qualification.qualified
        assert set(qualification.missing_gates) == set(records)

    def test_frozen_gate_set(self) -> None:
        assert [g.value for g in O2Gate] == ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"]


class TestAdmissibilityMirror:
    def test_statuses_match(self, wu_d_contract: dict) -> None:
        contract_statuses = {
            item["status"] for item in wu_d_contract["admissibility_mapping"]
        }
        assert contract_statuses == {s.value for s in EvidenceAdmissionStatus}

    def test_frozen_status_set(self) -> None:
        assert {s.value for s in EvidenceAdmissionStatus} == {
            "ADMISSIBLE", "LIMITED", "UNAVAILABLE", "INVALID",
        }


class TestEpistemicLayerMirror:
    def test_layers_match(self, wu_d_contract: dict) -> None:
        contract_layers = {
            item["status"] for item in wu_d_contract["epistemic_layers"]
        }
        assert contract_layers == {s.value for s in EpistemicStatus}

    def test_frozen_layer_order(self) -> None:
        from app.learner.evidence import EPISTEMIC_LAYER_ORDER

        assert [s.value for s in EPISTEMIC_LAYER_ORDER] == [
            "observed_descriptive",
            "gated_inference",
            "recommendation",
            "outcome_claim",
        ]
