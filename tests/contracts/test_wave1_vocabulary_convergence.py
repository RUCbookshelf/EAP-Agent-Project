"""Wave-1 shared-vocabulary convergence contract (WU6, integration-owned).

Proves the Academic Writing foundation's domain-local vocabulary mirror
matches the merged Shared Platform & Core authoritative definitions
exactly, while the two domains' semantic axes stay distinct:

    Academic verification status != shared evidence status != epistemic status

Ownership (frozen architecture D-05, D-06, D-09, D-37):
    Shared Platform & Core owns shared vocabulary.
    Academic owns Academic verification semantics.
    Research Governance owns admissibility/measurement policy.

This test is architecture-owned integration glue (Goal section 22): it
imports both sides and proves the mirror; it changes no product behavior.
"""

from __future__ import annotations

import inspect

import app.academic.vocabulary as academic_vocab
import app.shared.vocabularies as shared_vocab
from app.academic.entities import (
    CitationVerificationStatus,
    EvidenceVerificationStatus,
    EpistemicStatus as AcademicEpistemicStatus,
)
from app.academic.vocabulary import (
    EPISTEMIC_LAYER_RANK,
    EvidenceStatus as AcademicEvidenceStatus,
    academic_verification_to_shared,
    epistemic_downgrade_allowed,
)


def _literal_values(literal) -> set[str]:
    return set(literal.__args__)  # type: ignore[attr-defined]


class TestEvidenceStatusExactMirror:
    """Academic EvidenceStatus must exactly equal the shared 8-value set."""

    def test_academic_mirror_equals_shared(self) -> None:
        shared = {s.value for s in shared_vocab.EvidenceStatus}
        assert _literal_values(AcademicEvidenceStatus) == shared

    def test_shared_owns_the_canonical_values(self) -> None:
        assert {s.value for s in shared_vocab.EvidenceStatus} == {
            "verified",
            "candidate",
            "insufficient",
            "suppressed",
            "not_applicable",
            "unavailable",
            "legacy",
            "unresolved",
        }


class TestEpistemicStatusExactMirror:
    """Academic EpistemicStatus must exactly equal the shared 4-layer set."""

    def test_academic_mirror_equals_shared(self) -> None:
        shared = {s.value for s in shared_vocab.EpistemicStatus}
        assert _literal_values(AcademicEpistemicStatus) == shared

    def test_shared_layering_order(self) -> None:
        members = [s.value for s in shared_vocab.EpistemicStatus]
        assert members == [
            "observed_descriptive",
            "gated_inference",
            "recommendation",
            "outcome_claim",
        ]

    def test_academic_rank_map_consistent_with_shared_layering(self) -> None:
        shared_members = [s.value for s in shared_vocab.EpistemicStatus]
        assert set(EPISTEMIC_LAYER_RANK) == set(shared_members)
        ranks = [EPISTEMIC_LAYER_RANK[v] for v in shared_members]
        assert ranks == sorted(ranks)

    def test_downgrade_only_semantics_match_shared_layering(self) -> None:
        shared_members = [s.value for s in shared_vocab.EpistemicStatus]
        for current in shared_members:
            for target in shared_members:
                expected = EPISTEMIC_LAYER_RANK[target] <= EPISTEMIC_LAYER_RANK[current]
                assert (
                    epistemic_downgrade_allowed(current, target) == expected
                ), f"downgrade helper diverges for {current} -> {target}"


class TestAcademicVerificationAxisDistinct:
    """Academic verification status is a domain-local axis, never conflated."""

    def test_verification_states_are_domain_local_set(self) -> None:
        states = {
            "verified",
            "unverified",
            "verification_unavailable",
        }
        assert _literal_values(EvidenceVerificationStatus) == states
        assert _literal_values(CitationVerificationStatus) == states

    def test_verification_states_not_equal_to_shared_evidence_status(self) -> None:
        shared = {s.value for s in shared_vocab.EvidenceStatus}
        verification = _literal_values(EvidenceVerificationStatus)
        assert verification != shared
        # Only "verified" is a shared spelling; the other two states are
        # domain-local, proving verification is a distinct axis.
        assert verification & shared == {"verified"}
        assert not verification <= shared

    def test_adapter_maps_only_verification_axis_into_shared_evidence(self) -> None:
        shared = {s.value for s in shared_vocab.EvidenceStatus}
        for state in _literal_values(EvidenceVerificationStatus):
            mapped = academic_verification_to_shared(state)
            assert mapped in shared
            assert mapped in {s.value for s in shared_vocab.EvidenceStatus}

    def test_adapter_closed_vocabulary_never_silent(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            academic_verification_to_shared("bogus")
        with pytest.raises(ValueError):
            academic_verification_to_shared("observed_descriptive")

    def test_no_cross_axis_epistemic_mapping_function_exists(self) -> None:
        """academic_epistemic_to_shared must NOT exist (cross-axis conflation guard)."""
        assert not hasattr(academic_vocab, "academic_epistemic_to_shared")
        source = inspect.getsource(academic_vocab)
        assert "def academic_epistemic_to_shared" not in source


class TestBannedLabelsNeverInAcademicVocabulary:
    """Banned learner-performance labels must not enter either vocabulary."""

    def test_banned_labels_absent_from_academic_values(self) -> None:
        banned = shared_vocab.BANNED_LEARNER_LABELS
        academic_values = _literal_values(AcademicEvidenceStatus) | _literal_values(
            AcademicEpistemicStatus
        )
        assert banned.isdisjoint(academic_values)
        assert banned.isdisjoint(_literal_values(EvidenceVerificationStatus))

    def test_shared_ban_list_is_frozen(self) -> None:
        assert shared_vocab.BANNED_LEARNER_LABELS == {
            "mastery",
            "proficiency",
            "ability_level",
            "learning_gain",
        }
