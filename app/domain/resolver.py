"""Submission ancestry / domain resolver (D-23).

One shared service deriving the domain for every learner-evidence
record through trusted submission ancestry.

Resolution order:
  1. If the record carries a trusted ancestor (revision_of_submission_id
     or any derived-artifact parent chain), inherit the ancestor domain.
  2. Otherwise apply the server attribution rule -> l2 (H1 default).

Client input never overrides trusted server ancestry.  An invalid
domain stored in a legacy record raises DomainError; the resolver
never guesses.

References: D-01, D-17, D-21, D-22, D-23, D-28, D-31, 04 section 7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.domain.domain import Domain, DEFAULT_DOMAIN


class DomainError(Exception):
    """Raised when a stored domain value is not in the closed-set vocabulary."""

    def __init__(self, domain_value: str, *, record_table: str = "", record_id: Any = None) -> None:
        self.domain_value = domain_value
        self.record_table = record_table
        self.record_id = record_id
        msg = f"invalid domain '{domain_value}'"
        if record_table:
            msg += f" in table '{record_table}'"
        if record_id is not None:
            msg += f" (id={record_id})"
        super().__init__(msg)


@dataclass(frozen=True)
class AncestryRecord:
    """Lightweight record the resolver inspects during resolution.

    Fields mirror the minimal set needed for domain derivation without
    coupling the resolver to any specific table schema.
    """

    table: str
    id: Any
    domain: str | None = None
    submission_id: int | None = None
    ancestor_domain: str | None = None


@runtime_checkable
class AncestryFetchProtocol(Protocol):
    """Fetch an AncestryRecord for a given (table, id) pair."""

    def fetch(self, table: str, record_id: Any) -> AncestryRecord | None: ...


_TABLE_FAMILY: dict[str, str] = {
    "essays": "submission",
    "analysis_runs": "derived",
    "metric_results": "derived",
    "diagnoses": "derived",
    "feedback_records": "derived",
    "revision_groups": "derived",
    "revisions": "derived",
    "practice": "derived",
    "learner_history": "derived",
    "llm_call_records": "neutral",
    "configuration": "neutral",
    "system": "neutral",
}


def get_table_family(table: str) -> str | None:
    """Return the resolution-path family for *table*, or None if unknown."""
    return _TABLE_FAMILY.get(table)


def get_registry() -> dict[str, str]:
    """Return a copy of the table-family registry."""
    return dict(_TABLE_FAMILY)


def same_domain(a: Domain | str | None, b: Domain | str | None) -> bool:
    """Equality predicate for domain comparison.

    Used for revision-candidate selection, history/journey filtering,
    and practice-provenance checks (D-31).
    """
    if a is None or b is None:
        return a is b
    return _to_domain(a) == _to_domain(b)


def _to_domain(value: Domain | str | None) -> Domain:
    """Coerce a domain value to the Domain enum."""
    if isinstance(value, Domain):
        return value
    if value is None:
        raise DomainError("None")
    return Domain(value)


class SubmissionDomainResolver:
    """Derive the domain for any learner-evidence record via trusted
    submission ancestry (D-23).

    Usage::

        resolver = SubmissionDomainResolver()
        domain = resolver.resolve(record, ancestry_fetcher)
    """

    def resolve(
        self,
        record: AncestryRecord,
        fetcher: AncestryFetchProtocol | None = None,
    ) -> Domain:
        """Resolve the domain for *record*.

        Algorithm:
        1. Domain-neutral table -> Domain.L2.
        2. Ancestor domain shortcut -> use it.
        3. submission_id present -> walk ancestry chain.
        4. Record has own domain -> use it.
        5. Missing domain -> DEFAULT_DOMAIN (l2).
        6. Invalid stored domain -> raise DomainError.
        """
        family = get_table_family(record.table)
        if family == "neutral":
            return DEFAULT_DOMAIN

        if record.ancestor_domain is not None:
            return self._coerce_domain(record.ancestor_domain, record)

        if record.submission_id is not None and fetcher is not None:
            ancestor_domain = self._walk_ancestry(record.submission_id, fetcher, origin_table=record.table)
            if ancestor_domain is not None:
                return ancestor_domain

        if record.domain is not None:
            return self._coerce_domain(record.domain, record)

        return DEFAULT_DOMAIN

    def _walk_ancestry(
        self,
        submission_id: int,
        fetcher: AncestryFetchProtocol,
        *,
        origin_table: str,
    ) -> Domain | None:
        """Walk the submission ancestry chain and return the root domain."""
        visited: set[tuple[str, Any]] = set()
        current_id: Any = submission_id

        while current_id is not None:
            key = ("essays", current_id)
            if key in visited:
                break
            visited.add(key)

            record = fetcher.fetch("essays", current_id)
            if record is None:
                return None

            if record.submission_id is not None and record.submission_id != current_id:
                current_id = record.submission_id
                continue

            if record.domain is not None:
                return self._coerce_domain(record.domain, record)
            return DEFAULT_DOMAIN

        return None

    @staticmethod
    def _coerce_domain(value: str, record: AncestryRecord) -> Domain:
        try:
            return Domain(value)
        except (ValueError, KeyError):
            raise DomainError(value, record_table=record.table, record_id=record.id)


__all__ = [
    "DomainError",
    "AncestryRecord",
    "AncestryFetchProtocol",
    "SubmissionDomainResolver",
    "same_domain",
    "get_table_family",
    "get_registry",
    "DEFAULT_DOMAIN",
]
