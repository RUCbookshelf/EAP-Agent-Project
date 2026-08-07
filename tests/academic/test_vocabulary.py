# """Tests for app.academic.vocabulary — frozen value-set equality,
# downgrade matrix, adapter mapping, and integration-point constants.
# """

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.academic.vocabulary import (
    EPISTEMIC_LAYER_RANK,
    EPISTEMIC_STATUS_PERSISTENCE,
    SHARED_CORE_EPISTEMIC_STATUS,
    SHARED_CORE_EVIDENCE_STATUS,
    EvidenceStatus,
    EpistemicStatus,
    academic_verification_to_shared,
    epistemic_downgrade_allowed,
)

# ---------------------------------------------------------------------------
# 1. Frozen value-set equality
# ---------------------------------------------------------------------------


class TestEvidenceStatusValues:
    """EvidenceStatus must exactly mirror the frozen 8-value Shared vocabulary."""

    FROZEN_8 = {
        "verified",
        "candidate",
        "insufficient",
        "suppressed",
        "not_applicable",
        "unavailable",
        "legacy",
        "unresolved",
    }

    def test_evidence_status_exact_set(self) -> None:
        """EvidenceStatus must equal the frozen 8-value set."""
        actual = set(EvidenceStatus.__args__)  # type: ignore[attr-defined]
        assert actual == self.FROZEN_8


class TestEpistemicStatusReExport:
    """EpistemicStatus must be re-exported from entities, not redefined."""

    FROZEN_4 = {
        "observed_descriptive",
        "gated_inference",
        "recommendation",
        "outcome_claim",
    }

    def test_epistemic_status_exact_set(self) -> None:
        actual = set(EpistemicStatus.__args__)  # type: ignore[attr-defined]
        assert actual == self.FROZEN_4

    def test_no_duplicate_epistemic_definition(self) -> None:
        """vocabulary.py must not redefine EpistemicStatus locally."""
        voc_path = Path(__file__).resolve().parents[2] / "app" / "academic" / "vocabulary.py"
        source = voc_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assignments = [
            node.targets[0].id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "EpistemicStatus"
        ]
        # EpistemicStatus should only appear in `from .entities import EpistemicStatus`
        # not as a standalone assignment
        assert len(assignments) == 0, (
            "EpistemicStatus must be imported from entities, not redefined"
        )


# ---------------------------------------------------------------------------
# 2. Downgrade matrix
# ---------------------------------------------------------------------------


class TestEpistemicDowngradeAllowed:

    def test_same_layer_true(self) -> None:
        for status in EpistemicStatus.__args__:  # type: ignore[attr-defined]
            assert epistemic_downgrade_allowed(status, status) is True

    def test_downgrade_true(self) -> None:
        # recommendation -> gated_inference
        assert epistemic_downgrade_allowed("recommendation", "gated_inference") is True
        # gated_inference -> observed_descriptive
        assert epistemic_downgrade_allowed("gated_inference", "observed_descriptive") is True
        # outcome_claim -> observed_descriptive (multi-step down)
        assert epistemic_downgrade_allowed("outcome_claim", "observed_descriptive") is True

    def test_upgrade_false(self) -> None:
        # observed_descriptive -> gated_inference (upgrade)
        assert epistemic_downgrade_allowed("observed_descriptive", "gated_inference") is False
        # gated_inference -> outcome_claim (upgrade)
        assert epistemic_downgrade_allowed("gated_inference", "outcome_claim") is False
        # observed_descriptive -> outcome_claim (multi-step up)
        assert epistemic_downgrade_allowed("observed_descriptive", "outcome_claim") is False


# ---------------------------------------------------------------------------
# 3. Adapter mapping
# ---------------------------------------------------------------------------


class TestAcademicVerificationToShared:

    def test_verified(self) -> None:
        assert academic_verification_to_shared("verified") == "verified"

    def test_unverified(self) -> None:
        assert academic_verification_to_shared("unverified") == "candidate"

    def test_verification_unavailable(self) -> None:
        assert academic_verification_to_shared("verification_unavailable") == "unavailable"

    def test_unknown_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown verification_status"):
            academic_verification_to_shared("bogus")


# ---------------------------------------------------------------------------
# 4. Integration-point constants
# ---------------------------------------------------------------------------


class TestIntegrationPointConstants:

    def test_shared_core_evidence_status_non_empty(self) -> None:
        assert isinstance(SHARED_CORE_EVIDENCE_STATUS, str)
        assert len(SHARED_CORE_EVIDENCE_STATUS) > 0

    def test_shared_core_epistemic_status_non_empty(self) -> None:
        assert isinstance(SHARED_CORE_EPISTEMIC_STATUS, str)
        assert len(SHARED_CORE_EPISTEMIC_STATUS) > 0

    def test_epistemic_status_persistence_non_empty(self) -> None:
        assert isinstance(EPISTEMIC_STATUS_PERSISTENCE, str)
        assert len(EPISTEMIC_STATUS_PERSISTENCE) > 0

    def test_layer_rank_non_empty(self) -> None:
        assert len(EPISTEMIC_LAYER_RANK) == 4
