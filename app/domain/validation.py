"""Domain-scope validation utility.

Provides ``validate_domain_scope`` for future export wiring.  This
module does NOT modify app.research; it is a standalone utility.
"""

from __future__ import annotations

from app.domain.domain import Domain, VALID_DOMAINS


def validate_domain_scope(value: str) -> Domain:
    """Validate and return a Domain enum member.

    Raises ``ValueError`` if the value is not in the closed-set vocabulary.
    Used by future export wiring to reject unknown domain values.
    """
    if value not in VALID_DOMAINS:
        raise ValueError(
            f"unknown domain '{value}'; valid values: {sorted(VALID_DOMAINS)}"
        )
    return Domain(value)
