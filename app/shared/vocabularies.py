"""Canonical shared status vocabularies (frozen values only).

All enumerations below are frozen: they contain the exact string values
agreed in design decisions D-09, D-37, RT-17, and 04 §2/§4.  Do NOT
add, remove, or rename values here without a new design decision and
explicit researcher review.

Banned learner-performance labels
---------------------------------
The following labels must NEVER appear as shared status values:
  mastery, proficiency, ability_level, learning_gain

This prohibition is documented here and enforced by drift tests in
tests/shared/test_vocabularies.py.
"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# Epistemic status of a record or claim  (D-09; 04 §2)
# ---------------------------------------------------------------------------

class EpistemicStatus(str, Enum):
    """How the evidence behind a record was obtained."""

    OBSERVED_DESCRIPTIVE = "observed_descriptive"
    GATED_INFERENCE = "gated_inference"
    RECOMMENDATION = "recommendation"
    OUTCOME_CLAIM = "outcome_claim"


# ---------------------------------------------------------------------------
# Evidence status  (03 §3; 02 §4)
# ---------------------------------------------------------------------------

class EvidenceStatus(str, Enum):
    """Verification / sufficiency state of an evidence item."""

    VERIFIED = "verified"
    CANDIDATE = "candidate"
    INSUFFICIENT = "insufficient"
    SUPPRESSED = "suppressed"
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"
    LEGACY = "legacy"
    UNRESOLVED = "unresolved"


# ---------------------------------------------------------------------------
# Availability status  (D-37 / RT-17)
# ---------------------------------------------------------------------------

class AvailabilityStatus(str, Enum):
    """Whether supporting data is available for a metric."""

    AVAILABLE = "available"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_APPLICABLE = "not_applicable"


# ---------------------------------------------------------------------------
# Learner exposure  (D-37 / RT-17)
# ---------------------------------------------------------------------------

class LearnerExposure(str, Enum):
    """Who may see a given metric or label."""

    STUDENT = "student"
    RESEARCH_ONLY = "research_only"


# ---------------------------------------------------------------------------
# Resource / corpus boundary reasons  (I4; D-25)
# ---------------------------------------------------------------------------

class ResourceStatus(str, Enum):
    """Why a resource could not contribute to a metric."""

    CORPUS_NOT_REGISTERED = "corpus_not_registered"
    NO_REFERENCE_GROUP = "no_reference_group"
    INSUFFICIENT_CORPUS_DATA = "insufficient_corpus_data"
    FEATURE_INCOMPATIBLE = "feature_incompatible"
    LICENSE_RESTRICTED = "license_restricted"


# ---------------------------------------------------------------------------
# Banned learner-performance labels — never use as status values
# ---------------------------------------------------------------------------

BANNED_LEARNER_LABELS: frozenset[str] = frozenset({
    "mastery",
    "proficiency",
    "ability_level",
    "learning_gain",
})


# ---------------------------------------------------------------------------
# Convenience look-ups for test and drift-protection
# ---------------------------------------------------------------------------

__all__ = [
    "EpistemicStatus",
    "EvidenceStatus",
    "AvailabilityStatus",
    "LearnerExposure",
    "ResourceStatus",
    "BANNED_LEARNER_LABELS",
]
