"""Server-side domain/language attribution policy.

Implements the deterministic derivation and validation rules required by
the frozen architecture (D-01, D-17, D-21, D-22, D-28, D-36):

- Every accepted submission is attributed server-side.
- Client advisory fields are optional hints; mismatch -> 422.
- No client can relabel historical records.
- Academic Writing must NOT be exposed as a functioning domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.domain import Domain, Language


# --- Attribution constants ---------------------------------------------------

ATTRIBUTION_RULE_ID: str = "domain-attribution-v0.1.0"
ATTRIBUTION_RULE_VERSION: str = "0.1.0"


# --- Workflow-surface -> domain mapping (additive for future surfaces) -------

WORKFLOW_SURFACE_DOMAIN: dict[str, Domain] = {
    "submissions": Domain.L2,
    "revisions": Domain.L2,
    "practice": Domain.L2,
    "research": Domain.L2,
}


# --- Derivation result -------------------------------------------------------

@dataclass(frozen=True)
class AttributionResult:
    """Immutable result of server-side domain/language derivation."""

    domain: Domain
    language: Language
    rule_id: str = ATTRIBUTION_RULE_ID
    rule_version: str = ATTRIBUTION_RULE_VERSION


def derive_domain(surface: str | None = None) -> Domain:
    """Derive the domain for a submission.

    All current workflow surfaces derive ``l2``.
    The ``surface`` parameter is reserved for future academic surface
    routing and is ignored in H1.
    """
    # H1: every surface derives l2. Academic surface does not exist.
    return Domain.L2


def derive_language(surface: str | None = None) -> Language:
    """Derive the language for a submission.

    ``en`` is the only verified pipeline language.
    """
    return Language.EN


def derive_attribution(surface: str | None = None) -> AttributionResult:
    """Derive the full attribution tuple for a submission."""
    return AttributionResult(
        domain=derive_domain(surface),
        language=derive_language(surface),
    )


# --- Advisory validation -----------------------------------------------------

@dataclass(frozen=True)
class AdvisoryValidation:
    """Result of validating client advisory fields against server derivation."""

    ok: bool
    reason: str = ""


def validate_advisory(
    advisory_domain: str | None,
    advisory_language: str | None,
    derived: AttributionResult,
) -> AdvisoryValidation:
    """Validate client advisory fields against server-derived attribution.

    Rules:
    - If both advisory fields are absent (None), accept silently.
    - If advisory_domain is present but not in VALID_DOMAINS -> reject.
    - If advisory_language is present but not in VALID_LANGUAGES -> reject.
    - If advisory_domain is present and differs from derived -> reject.
    - If advisory_language is present and differs from derived -> reject.
    - If advisory matches derived -> accept (no re-attribution).
    """
    from app.domain.domain import VALID_DOMAINS, VALID_LANGUAGES

    # Both absent -> accept
    if advisory_domain is None and advisory_language is None:
        return AdvisoryValidation(ok=True)

    # Validate domain value
    if advisory_domain is not None and advisory_domain not in VALID_DOMAINS:
        return AdvisoryValidation(
            ok=False,
            reason=f"invalid domain '{advisory_domain}'; valid values: {sorted(VALID_DOMAINS)}",
        )

    # Validate language value
    if advisory_language is not None and advisory_language not in VALID_LANGUAGES:
        return AdvisoryValidation(
            ok=False,
            reason=f"invalid language '{advisory_language}'; valid values: {sorted(VALID_LANGUAGES)}",
        )

    # Check domain mismatch
    if advisory_domain is not None and advisory_domain != derived.domain.value:
        return AdvisoryValidation(
            ok=False,
            reason=(
                f"domain mismatch: client advisory '{advisory_domain}' "
                f"differs from server-derived '{derived.domain.value}'"
            ),
        )

    # Check language mismatch
    if advisory_language is not None and advisory_language != derived.language.value:
        return AdvisoryValidation(
            ok=False,
            reason=(
                f"language mismatch: client advisory '{advisory_language}' "
                f"differs from server-derived '{derived.language.value}'"
            ),
        )

    return AdvisoryValidation(ok=True)
