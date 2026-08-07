"""Domain-local vocabulary boundary for Academic Writing (Domain A).

This module mirrors integration-point constants from Shared Platform & Core.
It does NOT define a competing global contract. Shared vocabularies are owned
by Shared Platform & Core; Academic only references and adapts them locally.
"""

from __future__ import annotations

from typing import Literal

from .entities import EpistemicStatus  # re-export the single canonical domain literal

# ---------------------------------------------------------------------------
# INTEGRATION-POINT markers (module-level constants, do not rename)
# ---------------------------------------------------------------------------

SHARED_CORE_EVIDENCE_STATUS = "Shared Platform & Core evidence-status vocabulary (02:4.6); domain-local mirror only - not a competing global contract"
SHARED_CORE_EPISTEMIC_STATUS = "Shared Platform & Core epistemic-status vocabulary (02:4.5); domain-local mirror only - not a competing global contract"
EPISTEMIC_STATUS_PERSISTENCE = "Researcher decision required: additive typed field vs compute-at-boundary (interim: compute-at-boundary)"

# ---------------------------------------------------------------------------
# EvidenceStatus — exact frozen 8-value Literal; mirror only
# ---------------------------------------------------------------------------

EvidenceStatus = Literal[
    "verified", "candidate", "insufficient", "suppressed",
    "not_applicable", "unavailable", "legacy", "unresolved",
]

# EpistemicStatus is re-exported from entities.py — no duplicate definition here.

# ---------------------------------------------------------------------------
# Epistemic-layer rank (higher rank = later layer)
# ---------------------------------------------------------------------------

EPISTEMIC_LAYER_RANK: dict[EpistemicStatus, int] = {
    "observed_descriptive": 0,
    "gated_inference": 1,
    "recommendation": 2,
    "outcome_claim": 3,
}


# ---------------------------------------------------------------------------
# Downgrade-only helper
# ---------------------------------------------------------------------------

def epistemic_downgrade_allowed(current: EpistemicStatus, target: EpistemicStatus) -> bool:
    """Return True iff *target* has rank <= *current* (same-layer or downgrade)."""
    return EPISTEMIC_LAYER_RANK[target] <= EPISTEMIC_LAYER_RANK[current]


# ---------------------------------------------------------------------------
# Verification adapter (Academic -> Shared evidence-status)
# ---------------------------------------------------------------------------

def academic_verification_to_shared(
    verification_status: str,
) -> EvidenceStatus:
    """Map Academic verification states to Shared evidence-status vocabulary.

    This is a provisional integration-point adapter.  Unknown values raise
    ValueError (closed vocabulary; never silent mapping).
    """
    mapping: dict[str, EvidenceStatus] = {
        "verified": "verified",
        "unverified": "candidate",
        "verification_unavailable": "unavailable",
    }
    try:
        return mapping[verification_status]
    except KeyError:
        raise ValueError(
            f"Unknown verification_status {verification_status!r}; "
            f"valid values: {sorted(mapping.keys())}"
        )


# ---------------------------------------------------------------------------
# Cross-axis conflation guard
# ---------------------------------------------------------------------------

# academic_epistemic_to_shared is intentionally NOT implemented.
# Epistemic status and evidence status are different axes; providing a
# mapping function would conflate them and silently lose information.
# Do NOT add this function.
