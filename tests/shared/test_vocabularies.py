"""Drift-protection tests for the frozen shared vocabularies.

These tests verify exact set equality against the frozen value lists.
Adding a new approved value to a vocabulary requires updating this test
file in the same commit — a deliberate two-file change that makes drift
visible in code review.
"""

from __future__ import annotations

import pytest

from app.shared.vocabularies import (
    BANNED_LEARNER_LABELS,
    AvailabilityStatus,
    EpistemicStatus,
    EvidenceStatus,
    LearnerExposure,
    ResourceStatus,
)


# ── Frozen canonical sets ──────────────────────────────────────────────

_EXPECTED_EPISTEMIC: frozenset[str] = frozenset({
    "observed_descriptive",
    "gated_inference",
    "recommendation",
    "outcome_claim",
})

_EXPECTED_EVIDENCE: frozenset[str] = frozenset({
    "verified",
    "candidate",
    "insufficient",
    "suppressed",
    "not_applicable",
    "unavailable",
    "legacy",
    "unresolved",
})

_EXPECTED_AVAILABILITY: frozenset[str] = frozenset({
    "available",
    "insufficient_evidence",
    "not_applicable",
})

_EXPECTED_LEARNER_EXPOSURE: frozenset[str] = frozenset({
    "student",
    "research_only",
})

_EXPECTED_RESOURCE: frozenset[str] = frozenset({
    "corpus_not_registered",
    "no_reference_group",
    "insufficient_corpus_data",
    "feature_incompatible",
    "license_restricted",
})

_EXPECTED_BANNED: frozenset[str] = frozenset({
    "mastery",
    "proficiency",
    "ability_level",
    "learning_gain",
})


# ── Helpers ────────────────────────────────────────────────────────────

def _enum_values(enum_cls: type) -> frozenset[str]:
    return frozenset(v.value for v in enum_cls)


def _assert_no_duplicates(enum_cls: type) -> None:
    values = [v.value for v in enum_cls]
    assert len(values) == len(set(values)), (
        f"{enum_cls.__name__} contains duplicate values"
    )


def _assert_all_strings(enum_cls: type) -> None:
    for v in enum_cls:
        assert isinstance(v.value, str), (
            f"{enum_cls.__name__}.{v.name} value is not a string"
        )


# ── Tests: exact set equality ─────────────────────────────────────────

class TestEpistemicStatusExact:
    def test_exact_values(self) -> None:
        assert _enum_values(EpistemicStatus) == _EXPECTED_EPISTEMIC

    def test_no_duplicates(self) -> None:
        _assert_no_duplicates(EpistemicStatus)

    def test_all_strings(self) -> None:
        _assert_all_strings(EpistemicStatus)


class TestEvidenceStatusExact:
    def test_exact_values(self) -> None:
        assert _enum_values(EvidenceStatus) == _EXPECTED_EVIDENCE

    def test_no_duplicates(self) -> None:
        _assert_no_duplicates(EvidenceStatus)

    def test_all_strings(self) -> None:
        _assert_all_strings(EvidenceStatus)


class TestAvailabilityStatusExact:
    def test_exact_values(self) -> None:
        assert _enum_values(AvailabilityStatus) == _EXPECTED_AVAILABILITY

    def test_no_duplicates(self) -> None:
        _assert_no_duplicates(AvailabilityStatus)

    def test_all_strings(self) -> None:
        _assert_all_strings(AvailabilityStatus)


class TestLearnerExposureExact:
    def test_exact_values(self) -> None:
        assert _enum_values(LearnerExposure) == _EXPECTED_LEARNER_EXPOSURE

    def test_no_duplicates(self) -> None:
        _assert_no_duplicates(LearnerExposure)

    def test_all_strings(self) -> None:
        _assert_all_strings(LearnerExposure)


class TestResourceStatusExact:
    def test_exact_values(self) -> None:
        assert _enum_values(ResourceStatus) == _EXPECTED_RESOURCE

    def test_no_duplicates(self) -> None:
        _assert_no_duplicates(ResourceStatus)

    def test_all_strings(self) -> None:
        _assert_all_strings(ResourceStatus)


# ── Tests: banned labels ──────────────────────────────────────────────

class TestBannedLabels:
    def test_banned_set_matches(self) -> None:
        assert BANNED_LEARNER_LABELS == _EXPECTED_BANNED

    def test_banned_labels_not_in_epistemic(self) -> None:
        assert BANNED_LEARNER_LABELS.isdisjoint(_enum_values(EpistemicStatus))

    def test_banned_labels_not_in_evidence(self) -> None:
        assert BANNED_LEARNER_LABELS.isdisjoint(_enum_values(EvidenceStatus))

    def test_banned_labels_not_in_availability(self) -> None:
        assert BANNED_LEARNER_LABELS.isdisjoint(_enum_values(AvailabilityStatus))

    def test_banned_labels_not_in_learner_exposure(self) -> None:
        assert BANNED_LEARNER_LABELS.isdisjoint(_enum_values(LearnerExposure))

    def test_banned_labels_not_in_resource(self) -> None:
        assert BANNED_LEARNER_LABELS.isdisjoint(_enum_values(ResourceStatus))


# ── Drift test ────────────────────────────────────────────────────────

class TestDriftProtection:
    """If this test fails, an unapproved value was added to a vocabulary.

    To fix: update the corresponding _EXPECTED_* set in this file and
    include the approval reference in the same commit.
    """

    @pytest.mark.parametrize(
        "enum_cls,expected",
        [
            (EpistemicStatus, _EXPECTED_EPISTEMIC),
            (EvidenceStatus, _EXPECTED_EVIDENCE),
            (AvailabilityStatus, _EXPECTED_AVAILABILITY),
            (LearnerExposure, _EXPECTED_LEARNER_EXPOSURE),
            (ResourceStatus, _EXPECTED_RESOURCE),
        ],
        ids=["epistemic", "evidence", "availability", "learner_exposure", "resource"],
    )
    def test_no_unexpected_values(
        self, enum_cls: type, expected: frozenset[str]
    ) -> None:
        actual = _enum_values(enum_cls)
        added = actual - expected
        removed = expected - actual
        assert not added and not removed, (
            f"{enum_cls.__name__} drift detected: "
            f"added={added or 'none'}, removed={removed or 'none'}"
        )
