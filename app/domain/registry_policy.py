"""Domain-aware registry selection policy (H1: additive wrapper).

Provides ``select_for_domain`` as an additive helper that filters
existing registry entries by domain compatibility WITHOUT changing
any existing registry lookup behavior.

H1 semantics:
  - All current entries are l2-compatible.
  - academic returns empty (no academic entries exist in H1).

References: D-05, D-26.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from app.domain.domain import Domain


@runtime_checkable
class _DomainTagged(Protocol):
    """Protocol for objects that carry a ``domain`` attribute."""

    @property
    def domain(self) -> str: ...


@runtime_checkable
class _DictEntry(Protocol):
    """Protocol for dict-like entries with a ``domain`` key."""

    def __getitem__(self, key: str) -> Any: ...

    def __contains__(self, key: object) -> bool: ...


def _entry_domain(entry: Any) -> str | None:
    """Extract the domain from an entry, returning None if absent."""
    if isinstance(entry, dict):
        return entry.get("domain")
    if hasattr(entry, "domain"):
        return getattr(entry, "domain")
    return None


def select_for_domain(
    entries: Sequence[Any],
    domain: Domain,
) -> list[Any]:
    """Filter registry entries to those compatible with *domain*.

    This is an **additive wrapper**: it does not modify the underlying
    registries or their lookup methods. Existing callers are unchanged.

    H1 semantics (all current entries are l2-compatible):
      - ``Domain.L2``: returns all entries (with or without a domain tag).
      - ``Domain.ACADEMIC``: returns only entries explicitly tagged
        ``"academic"``; currently this is always empty.

    Entries without an explicit domain tag are treated as l2-compatible
    in H1 (additive default).
    """
    result: list[Any] = []
    for entry in entries:
        entry_domain = _entry_domain(entry)
        if entry_domain is None:
            # No domain tag: l2-compatible default (H1).
            if domain == Domain.L2:
                result.append(entry)
        elif entry_domain == domain.value:
            result.append(entry)
        # else: entry is for a different domain; skip.
    return result


def select_calf_for_domain(
    specifications: Sequence[Any],
    domain: Domain,
) -> list[Any]:
    """Domain-aware selection for CALF MeasurementSpecification entries.

    Convenience wrapper that delegates to ``select_for_domain``.
    """
    return select_for_domain(specifications, domain)


def select_resource_requirement(
    specifications: Sequence[Any],
    resource_requirement: str,
) -> list[Any]:
    """Filter CALF specifications by a specific resource requirement (D-25).

    Returns entries whose ``resource_requirements`` list contains
    *resource_requirement*. This is a mechanism-only helper; no content
    decisions are made here.
    """
    result: list[Any] = []
    for spec in specifications:
        reqs = getattr(spec, "resource_requirements", None)
        if reqs is None and isinstance(spec, dict):
            reqs = spec.get("resource_requirements", [])
        if reqs and resource_requirement in reqs:
            result.append(spec)
    return result
