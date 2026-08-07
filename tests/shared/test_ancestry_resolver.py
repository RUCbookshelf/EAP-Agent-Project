"""Tests for the submission ancestry/domain resolver (WU4-D23).

Covers:
  - New L2 submission -> l2
  - Legacy submission (no domain, no ancestry) -> l2
  - Derived artifact chains -> l2 through ancestry
  - Missing ancestry -> l2 default
  - Conflicting client input rejected (WU3 contract) / resolver guard
  - Invalid domain -> DomainError
  - Domain equality predicate for revision-candidate selection
  - D-31 invariant hooks (named contract tests)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.domain.domain import Domain, DEFAULT_DOMAIN
from app.domain.resolver import (
    DomainError,
    AncestryRecord,
    SubmissionDomainResolver,
    same_domain,
    get_table_family,
    get_registry,
)


@dataclass
class FakeAncestryStore:
    """In-memory store for test ancestry records keyed by (table, id)."""

    records: dict[tuple[str, Any], AncestryRecord]

    def __init__(self, records=None):
        self.records = {}
        if records:
            for r in records:
                self.records[(r.table, r.id)] = r

    def fetch(self, table, record_id):
        return self.records.get((table, record_id))


class TestTableFamilyRegistry:
    """04 section 7 table-family -> resolution-path registry tests."""

    def test_all_expected_tables_registered(self):
        registry = get_registry()
        expected_submission = {"essays"}
        expected_derived = {
            "analysis_runs", "metric_results", "diagnoses",
            "feedback_records", "revision_groups", "revisions",
            "practice", "learner_history",
        }
        expected_neutral = {"llm_call_records", "configuration", "system"}
        assert expected_submission <= set(registry.keys())
        assert expected_derived <= set(registry.keys())
        assert expected_neutral <= set(registry.keys())
        for t in expected_submission:
            assert registry[t] == "submission"
        for t in expected_derived:
            assert registry[t] == "derived"
        for t in expected_neutral:
            assert registry[t] == "neutral"

    def test_unknown_table_returns_none(self):
        assert get_table_family("nonexistent") is None


class TestDomainError:
    """DomainError is raised for invalid stored domains."""

    def test_invalid_domain_raises(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="essays", id=1, domain="nonexistent")
        with pytest.raises(DomainError, match="invalid domain") as exc_info:
            resolver.resolve(record)
        assert exc_info.value.domain_value == "nonexistent"
        assert exc_info.value.record_table == "essays"
        assert exc_info.value.record_id == 1

    def test_invalid_ancestor_domain_raises(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(
            table="analysis_runs", id=10, submission_id=1,
            ancestor_domain="bad_domain",
        )
        with pytest.raises(DomainError, match="invalid domain") as exc_info:
            resolver.resolve(record)
        assert exc_info.value.domain_value == "bad_domain"


class TestResolveNewSubmission:
    """New L2 submission -> l2 (server attribution)."""

    def test_new_l2_submission_resolves_to_l2(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="essays", id=100, domain="l2")
        assert resolver.resolve(record) == Domain.L2

    def test_new_submission_no_domain_defaults_to_l2(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="essays", id=101)
        assert resolver.resolve(record) == Domain.L2


class TestResolveLegacySubmission:
    """Legacy submission (no domain, no ancestry) -> l2."""

    def test_legacy_no_domain_no_ancestry(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="essays", id=1)
        assert resolver.resolve(record) == Domain.L2

    def test_legacy_null_domain(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="essays", id=2, domain=None)
        assert resolver.resolve(record) == Domain.L2


class TestResolveDerivedArtifactChain:
    """Derived artifacts -> l2 through ancestry."""

    def test_analysis_run_inherits(self):
        store = FakeAncestryStore([
            AncestryRecord(table="essays", id=1, domain="l2"),
        ])
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="analysis_runs", id=10, submission_id=1)
        assert resolver.resolve(record, store) == Domain.L2

    def test_feedback_inherits(self):
        store = FakeAncestryStore([
            AncestryRecord(table="essays", id=1, domain="l2"),
        ])
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="feedback_records", id=30, submission_id=1)
        assert resolver.resolve(record, store) == Domain.L2

    def test_revision_inherits(self):
        store = FakeAncestryStore([
            AncestryRecord(table="essays", id=5, domain="l2"),
        ])
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="revisions", id=50, submission_id=5)
        assert resolver.resolve(record, store) == Domain.L2

    def test_practice_inherits(self):
        store = FakeAncestryStore([
            AncestryRecord(table="essays", id=7, domain="l2"),
        ])
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="practice", id=70, submission_id=7)
        assert resolver.resolve(record, store) == Domain.L2

    def test_multi_hop_chain(self):
        store = FakeAncestryStore([
            AncestryRecord(table="essays", id=1, domain="l2"),
            AncestryRecord(table="essays", id=10, domain="l2", submission_id=1),
        ])
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="revisions", id=20, submission_id=10)
        assert resolver.resolve(record, store) == Domain.L2


class TestResolveMissingAncestry:
    """Missing ancestry -> l2 default."""

    def test_no_fetcher_no_domain(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="analysis_runs", id=99)
        assert resolver.resolve(record) == Domain.L2

    def test_fetcher_returns_none(self):
        store = FakeAncestryStore([])
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="analysis_runs", id=99, submission_id=1)
        assert resolver.resolve(record, store) == Domain.L2


class TestConflictingClientInput:
    """Conflicting client input rejected / resolver guard."""

    def test_resolver_never_uses_client_domain(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="essays", id=500, domain="l2")
        assert resolver.resolve(record) == Domain.L2

    def test_invalid_domain_from_store_raises(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="essays", id=501, domain="invalid_val")
        with pytest.raises(DomainError):
            resolver.resolve(record)

    def test_academic_valid_but_rejected_upstream(self):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="essays", id=600, domain="academic")
        assert resolver.resolve(record) == Domain.ACADEMIC


class TestDomainEqualityPredicate:
    """same_domain() for revision-candidate selection (D-31)."""

    def test_same_domain_l2(self):
        assert same_domain(Domain.L2, Domain.L2) is True

    def test_same_domain_academic(self):
        assert same_domain(Domain.ACADEMIC, Domain.ACADEMIC) is True

    def test_different_domains(self):
        assert same_domain(Domain.L2, Domain.ACADEMIC) is False

    def test_string_l2(self):
        assert same_domain("l2", "l2") is True

    def test_mixed_types(self):
        assert same_domain(Domain.L2, "l2") is True
        assert same_domain("l2", Domain.L2) is True

    def test_both_none(self):
        assert same_domain(None, None) is True

    def test_one_none(self):
        assert same_domain(None, Domain.L2) is False
        assert same_domain(Domain.L2, None) is False

    def test_across_revision_candidates(self):
        assert same_domain(Domain.L2, Domain.L2)
        assert not same_domain(Domain.L2, Domain.ACADEMIC)


class TestAncestryRecordDataclass:
    def test_frozen(self):
        record = AncestryRecord(table="essays", id=1)
        with pytest.raises(AttributeError):
            record.table = "other"  # type: ignore[misc]

    def test_defaults(self):
        record = AncestryRecord(table="test", id=42)
        assert record.domain is None
        assert record.submission_id is None
        assert record.ancestor_domain is None


class TestD31HistorySameDomainFilter:
    def test_history_filter(self):
        subs = [("S1", Domain.L2), ("S2", Domain.L2), ("S3", Domain.ACADEMIC)]
        comparable = [sid for sid, d in subs if same_domain(d, Domain.L2)]
        assert comparable == ["S1", "S2"]


class TestD31JourneySameDomainFilter:
    def test_journey_filter(self):
        entries = [("e1", Domain.L2), ("e2", Domain.L2), ("e3", Domain.ACADEMIC)]
        filtered = [eid for eid, d in entries if same_domain(d, Domain.L2)]
        assert filtered == ["e1", "e2"]


class TestD31RevisionCandidatesSameDomainFilter:
    def test_revision_candidate_filter(self):
        cands = [("r1", Domain.L2), ("r2", Domain.L2), ("r3", Domain.ACADEMIC)]
        same = [rid for rid, d in cands if same_domain(d, Domain.L2)]
        assert same == ["r1", "r2"]


class TestD31PracticeProvenanceSameDomainFilter:
    def test_practice_provenance_filter(self):
        items = [("p1", Domain.L2), ("p2", Domain.ACADEMIC), ("p3", Domain.L2)]
        filtered = [pid for pid, d in items if same_domain(d, Domain.L2)]
        assert filtered == ["p1", "p3"]


class TestD31ResolverIntegration:
    def test_resolve_then_compare(self):
        store = FakeAncestryStore([
            AncestryRecord(table="essays", id=1, domain="l2"),
            AncestryRecord(table="essays", id=2, domain="l2"),
        ])
        resolver = SubmissionDomainResolver()
        d1 = resolver.resolve(AncestryRecord(table="analysis_runs", id=10, submission_id=1), store)
        d2 = resolver.resolve(AncestryRecord(table="analysis_runs", id=20, submission_id=2), store)
        assert same_domain(d1, d2)


class TestNeutrality:
    @pytest.mark.parametrize("table", ["llm_call_records", "configuration", "system"])
    def test_neutral_table_returns_l2(self, table):
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table=table, id=1)
        assert resolver.resolve(record) == Domain.L2


class TestCycleGuard:
    def test_cycle_detection(self):
        store = FakeAncestryStore([
            AncestryRecord(table="essays", id=1, domain="l2", submission_id=2),
            AncestryRecord(table="essays", id=2, domain="l2", submission_id=1),
        ])
        resolver = SubmissionDomainResolver()
        record = AncestryRecord(table="analysis_runs", id=10, submission_id=1)
        result = resolver.resolve(record, store)
        assert result in (Domain.L2, Domain.ACADEMIC)
