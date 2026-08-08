"""Tests for app.academic.provenance.ProvenanceGraph."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from app.academic.entities import (
    CitationLink,
    CitationVerificationRecord,
    Claim,
    ClaimEvidenceLink,
    EvidenceUnit,
    PaperSection,
    ResearchProject,
    ResearchQuestion,
    Source,
)
from app.academic.provenance import ProvenanceGraph


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 2, tzinfo=timezone.utc)


def _make_graph() -> ProvenanceGraph:
    """Build the representative synthetic graph from the task packet."""
    rp1 = ResearchProject(project_id="rp-1", title="Project One")
    rp2 = ResearchProject(project_id="rp-2", title="Project Two")

    rq1 = ResearchQuestion(
        question_id="rq-1", project_id="rp-1", question_text="RQ one"
    )
    rq2 = ResearchQuestion(
        question_id="rq-2", project_id="rp-1", question_text="RQ two"
    )

    src1 = Source(
        source_id="src-1",
        project_id="rp-1",
        title="Source One",
        origin="learner_entered",
        source_text="some text",
        source_text_hash=_sha256("some text"),
    )
    src2 = Source(
        source_id="src-2",
        project_id="rp-1",
        title="Source Two",
        origin="imported_file",
        source_text="other text",
        source_text_hash=_sha256("other text"),
    )
    src3 = Source(
        source_id="src-3",
        project_id="rp-1",
        title="Source Three",
        origin="learner_entered",
    )
    src_other = Source(
        source_id="src-other",
        project_id="rp-2",
        title="Source Other",
        origin="learner_entered",
    )

    ev1 = EvidenceUnit(
        evidence_id="ev-1",
        project_id="rp-1",
        source_id="src-1",
        source_version=1,
        kind="direct_quote",
        locator="p.10",
        content="evidence one content",
        rq_ids=["rq-1"],
    )
    ev2 = EvidenceUnit(
        evidence_id="ev-2",
        project_id="rp-1",
        source_id="src-1",
        source_version=1,
        kind="learner_paraphrase",
        locator="p.11",
        content="evidence two content",
    )
    ev3 = EvidenceUnit(
        evidence_id="ev-3",
        project_id="rp-1",
        source_id="src-2",
        source_version=1,
        kind="direct_quote",
        locator="p.20",
        content="evidence three content",
    )
    ev4 = EvidenceUnit(
        evidence_id="ev-4",
        project_id="rp-1",
        source_id="src-3",
        source_version=1,
        kind="direct_quote",
        locator="p.30",
        content="evidence four content",
    )

    # cl-1: supported, two evidence links (supports ev-1, supports ev-3)
    cl1 = Claim(
        claim_id="cl-1",
        project_id="rp-1",
        claim_text="Claim one text",
        support_state="supported",
        rq_ids=["rq-1"],
        section_ids=["sec-1"],
        evidence_links=[
            ClaimEvidenceLink(evidence_id="ev-1", link_type="supports"),
            ClaimEvidenceLink(evidence_id="ev-3", link_type="supports"),
        ],
    )
    # cl-2: unsupported, no links
    cl2 = Claim(
        claim_id="cl-2",
        project_id="rp-1",
        claim_text="Claim two text",
        support_state="unsupported",
    )
    # cl-3: undetermined, no links
    cl3 = Claim(
        claim_id="cl-3",
        project_id="rp-1",
        claim_text="Claim three text",
        support_state="undetermined",
    )
    # cl-4: partially_supported, ev-2 contextualizes
    cl4 = Claim(
        claim_id="cl-4",
        project_id="rp-1",
        claim_text="Claim four text",
        support_state="partially_supported",
        rq_ids=["rq-2"],
        evidence_links=[
            ClaimEvidenceLink(evidence_id="ev-2", link_type="contextualizes"),
        ],
    )
    # cl-other in rp-2 (for cross-project broken citation test)
    clother = Claim(
        claim_id="cl-other",
        project_id="rp-2",
        claim_text="Claim in other project",
        support_state="unsupported",
    )

    sec1 = PaperSection(
        section_id="sec-1",
        project_id="rp-1",
        section_title="Section One",
        order=0,
        rq_ids=["rq-1"],
    )
    sec2 = PaperSection(
        section_id="sec-2",
        project_id="rp-1",
        section_title="Section Two",
        order=1,
        parent_section_id="sec-1",
    )

    cit1 = CitationLink(
        citation_id="cit-1",
        project_id="rp-1",
        claim_id="cl-1",
        source_id="src-1",
        evidence_id="ev-1",
    )
    cit2 = CitationLink(
        citation_id="cit-2",
        project_id="rp-1",
        claim_id="cl-1",
        source_id="src-2",
    )
    cit3 = CitationLink(
        citation_id="cit-3",
        project_id="rp-1",
        claim_id="cl-4",
        source_id="src-3",
    )
    # Broken citations — claim_id uses cl-3 (undetermined, no existing citations)
    cit4 = CitationLink(
        citation_id="cit-4",
        project_id="rp-1",
        claim_id="cl-missing",
        source_id="src-missing",
    )
    cit5 = CitationLink(
        citation_id="cit-5",
        project_id="rp-1",
        claim_id="cl-3",
        source_id="src-missing",
    )
    cit6 = CitationLink(
        citation_id="cit-6",
        project_id="rp-1",
        claim_id="cl-3",
        source_id="src-2",
        evidence_id="ev-missing",
    )
    # Cross-project: claim belongs to rp-2
    cit7 = CitationLink(
        citation_id="cit-7",
        project_id="rp-1",
        claim_id="cl-other",
        source_id="src-2",
    )

    vr1 = CitationVerificationRecord(
        record_id="vr-1",
        citation_id="cit-1",
        rule_id="rule-basic",
        rule_version="1.0",
        source_revision_hash=_sha256("revision"),
        run_time=T0,
        result="verified",
    )

    return ProvenanceGraph(
        projects=[rp1, rp2],
        questions=[rq1, rq2],
        sources=[src1, src2, src3, src_other],
        evidence_units=[ev1, ev2, ev3, ev4],
        claims=[cl1, cl2, cl3, cl4, clother],
        sections=[sec1, sec2],
        citations=[cit1, cit2, cit3, cit4, cit5, cit6, cit7],
        records=[vr1],
    )


class TestDuplicateLinksDedupe:
    def test_same_evidence_via_two_links_returned_once(self) -> None:
        rp = ResearchProject(project_id="rp-dup", title="Dup")
        src = Source(
            source_id="src-dup", project_id="rp-dup", title="S", origin="learner_entered"
        )
        ev = EvidenceUnit(
            evidence_id="ev-dup",
            project_id="rp-dup",
            source_id="src-dup",
            source_version=1,
            kind="direct_quote",
            locator="p.1",
            content="c",
        )
        cl = Claim(
            claim_id="cl-dup",
            project_id="rp-dup",
            claim_text="T",
            support_state="supported",
            evidence_links=[
                ClaimEvidenceLink(evidence_id="ev-dup", link_type="supports"),
                ClaimEvidenceLink(evidence_id="ev-dup", link_type="contextualizes"),
            ],
        )
        g = ProvenanceGraph(projects=[rp], sources=[src], evidence_units=[ev], claims=[cl])
        assert [e.evidence_id for e in g.evidence_for_claim("cl-dup")] == ["ev-dup"]
        assert [(l.evidence_id, l.link_type) for l in g.links_for_claim("cl-dup")] == [
            ("ev-dup", "contextualizes"),
            ("ev-dup", "supports"),
        ]

    def test_links_for_claim_unknown_returns_empty(self) -> None:
        g = ProvenanceGraph()
        assert g.links_for_claim("cl-nope") == []

    def test_wrong_type_constructor_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="projects"):
            ProvenanceGraph(projects=["not-a-project"])

    def test_wrong_type_records_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="records"):
            ProvenanceGraph(records=[{"not": "a record"}])


class TestEvidenceForClaim:
    def test_returns_linked_evidence_sorted(self) -> None:
        g = _make_graph()
        result = g.evidence_for_claim("cl-1")
        assert [e.evidence_id for e in result] == ["ev-1", "ev-3"]

    def test_unknown_claim_returns_empty(self) -> None:
        g = _make_graph()
        assert g.evidence_for_claim("cl-nope") == []

    def test_claim_with_no_links(self) -> None:
        g = _make_graph()
        assert g.evidence_for_claim("cl-2") == []


class TestClaimsForEvidence:
    def test_single_claim_references_evidence(self) -> None:
        g = _make_graph()
        result = g.claims_for_evidence("ev-1")
        assert [c.claim_id for c in result] == ["cl-1"]

    def test_evidence_referenced_by_multiple_claims(self) -> None:
        g = _make_graph()
        result = g.claims_for_evidence("ev-2")
        assert [c.claim_id for c in result] == ["cl-4"]

    def test_unreferenced_evidence_returns_empty(self) -> None:
        g = _make_graph()
        assert g.claims_for_evidence("ev-4") == []

    def test_unknown_evidence_returns_empty(self) -> None:
        g = _make_graph()
        assert g.claims_for_evidence("ev-nope") == []


class TestClaimsForRQ:
    def test_claims_linked_to_rq(self) -> None:
        g = _make_graph()
        result = g.claims_for_rq("rq-1")
        assert [c.claim_id for c in result] == ["cl-1"]

    def test_rq_with_no_claims(self) -> None:
        g = _make_graph()
        result = g.claims_for_rq("rq-2")
        assert [c.claim_id for c in result] == ["cl-4"]

    def test_unknown_rq_returns_empty(self) -> None:
        g = _make_graph()
        assert g.claims_for_rq("rq-nope") == []


class TestSourcesForClaim:
    def test_returns_distinct_sources_sorted(self) -> None:
        g = _make_graph()
        result = g.sources_for_claim("cl-1")
        assert [s.source_id for s in result] == ["src-1", "src-2"]

    def test_claim_with_no_links(self) -> None:
        g = _make_graph()
        assert g.sources_for_claim("cl-2") == []

    def test_unknown_claim_returns_empty(self) -> None:
        g = _make_graph()
        assert g.sources_for_claim("cl-nope") == []


class TestCitationsForClaim:
    def test_returns_citations_sorted(self) -> None:
        g = _make_graph()
        result = g.citations_for_claim("cl-1")
        assert [c.citation_id for c in result] == ["cit-1", "cit-2"]

    def test_claim_with_no_citations(self) -> None:
        g = _make_graph()
        assert g.citations_for_claim("cl-2") == []

    def test_unknown_claim_returns_empty(self) -> None:
        g = _make_graph()
        assert g.citations_for_claim("cl-nope") == []


class TestUnsupportedClaims:
    def test_returns_unsupported_only(self) -> None:
        g = _make_graph()
        result = g.unsupported_claims("rp-1")
        assert [c.claim_id for c in result] == ["cl-2"]

    def test_undetermined_excluded(self) -> None:
        g = _make_graph()
        result = g.unsupported_claims("rp-1")
        claim_ids = [c.claim_id for c in result]
        assert "cl-3" not in claim_ids

    def test_different_project_returns_empty(self) -> None:
        g = _make_graph()
        assert g.unsupported_claims("rp-1-nonexistent") == []


class TestOrphanEvidence:
    def test_returns_unreferenced_evidence(self) -> None:
        g = _make_graph()
        result = g.orphan_evidence("rp-1")
        assert [e.evidence_id for e in result] == ["ev-4"]

    def test_all_evidence_referenced(self) -> None:
        rp = ResearchProject(project_id="rp-x", title="T")
        src = Source(
            source_id="src-x", project_id="rp-x", title="S", origin="learner_entered"
        )
        ev = EvidenceUnit(
            evidence_id="ev-x",
            project_id="rp-x",
            source_id="src-x",
            source_version=1,
            kind="direct_quote",
            locator="p.1",
            content="content",
        )
        cl = Claim(
            claim_id="cl-x",
            project_id="rp-x",
            claim_text="C",
            support_state="supported",
            evidence_links=[ClaimEvidenceLink(evidence_id="ev-x", link_type="supports")],
        )
        g = ProvenanceGraph(
            projects=[rp], sources=[src], evidence_units=[ev], claims=[cl]
        )
        assert g.orphan_evidence("rp-x") == []

    def test_empty_graph(self) -> None:
        g = ProvenanceGraph()
        assert g.orphan_evidence("rp-1") == []


class TestBrokenCitationLinks:
    def test_returns_broken_sorted(self) -> None:
        g = _make_graph()
        result = g.broken_citation_links("rp-1")
        assert [c.citation_id for c in result] == [
            "cit-4",
            "cit-5",
            "cit-6",
            "cit-7",
        ]

    def test_no_broken_in_clean_graph(self) -> None:
        rp = ResearchProject(project_id="rp-c", title="C")
        src = Source(
            source_id="src-c", project_id="rp-c", title="S", origin="learner_entered"
        )
        ev = EvidenceUnit(
            evidence_id="ev-c",
            project_id="rp-c",
            source_id="src-c",
            source_version=1,
            kind="direct_quote",
            locator="p.1",
            content="c",
        )
        cl = Claim(
            claim_id="cl-c",
            project_id="rp-c",
            claim_text="T",
            support_state="supported",
            evidence_links=[ClaimEvidenceLink(evidence_id="ev-c", link_type="supports")],
        )
        cit = CitationLink(
            citation_id="cit-c",
            project_id="rp-c",
            claim_id="cl-c",
            source_id="src-c",
            evidence_id="ev-c",
        )
        g = ProvenanceGraph(
            projects=[rp], sources=[src], evidence_units=[ev], claims=[cl], citations=[cit]
        )
        assert g.broken_citation_links("rp-c") == []

    def test_empty_graph(self) -> None:
        g = ProvenanceGraph()
        assert g.broken_citation_links("rp-1") == []


class TestClaimsForSection:
    def test_returns_claims_in_section(self) -> None:
        g = _make_graph()
        result = g.claims_for_section("sec-1")
        assert [c.claim_id for c in result] == ["cl-1"]

    def test_section_with_no_claims(self) -> None:
        g = _make_graph()
        assert g.claims_for_section("sec-2") == []

    def test_unknown_section_returns_empty(self) -> None:
        g = _make_graph()
        assert g.claims_for_section("sec-nope") == []


class TestSourcesForEvidence:
    def test_returns_source(self) -> None:
        g = _make_graph()
        result = g.sources_for_evidence("ev-2")
        assert len(result) == 1
        assert result[0].source_id == "src-1"

    def test_unknown_evidence_returns_empty(self) -> None:
        g = _make_graph()
        assert g.sources_for_evidence("ev-nope") == []


class TestCitationsForSource:
    def test_returns_citations(self) -> None:
        g = _make_graph()
        result = g.citations_for_source("src-1")
        assert [c.citation_id for c in result] == ["cit-1"]

    def test_unknown_source_returns_empty(self) -> None:
        g = _make_graph()
        assert g.citations_for_source("src-nope") == []


class TestRecordsForCitation:
    def test_returns_records_sorted(self) -> None:
        g = _make_graph()
        result = g.records_for_citation("cit-1")
        assert [r.record_id for r in result] == ["vr-1"]

    def test_citation_with_no_records(self) -> None:
        g = _make_graph()
        assert g.records_for_citation("cit-2") == []

    def test_unknown_citation_returns_empty(self) -> None:
        g = _make_graph()
        assert g.records_for_citation("cit-nope") == []


class TestEmptyGraph:
    @pytest.fixture()
    def empty_graph(self) -> ProvenanceGraph:
        return ProvenanceGraph()

    def test_evidence_for_claim(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.evidence_for_claim("cl-x") == []

    def test_claims_for_evidence(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.claims_for_evidence("ev-x") == []

    def test_claims_for_rq(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.claims_for_rq("rq-x") == []

    def test_sources_for_claim(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.sources_for_claim("cl-x") == []

    def test_citations_for_claim(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.citations_for_claim("cl-x") == []

    def test_unsupported_claims(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.unsupported_claims("rp-x") == []

    def test_orphan_evidence(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.orphan_evidence("rp-x") == []

    def test_broken_citation_links(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.broken_citation_links("rp-x") == []

    def test_claims_for_section(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.claims_for_section("sec-x") == []

    def test_sources_for_evidence(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.sources_for_evidence("ev-x") == []

    def test_citations_for_source(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.citations_for_source("src-x") == []

    def test_records_for_citation(self, empty_graph: ProvenanceGraph) -> None:
        assert empty_graph.records_for_citation("cit-x") == []


class TestDeterministicOrdering:
    def test_claims_sorted_by_id(self) -> None:
        rp = ResearchProject(project_id="rp-d", title="D")
        cl_b = Claim(
            claim_id="cl-b",
            project_id="rp-d",
            claim_text="B",
            support_state="unsupported",
            section_ids=["sec-d"],
        )
        cl_a = Claim(
            claim_id="cl-a",
            project_id="rp-d",
            claim_text="A",
            support_state="unsupported",
            section_ids=["sec-d"],
        )
        sec = PaperSection(
            section_id="sec-d",
            project_id="rp-d",
            section_title="D",
        )
        g = ProvenanceGraph(projects=[rp], claims=[cl_b, cl_a], sections=[sec])
        result = g.claims_for_section("sec-d")
        assert [c.claim_id for c in result] == ["cl-a", "cl-b"]

    def test_last_wins_duplicate_ids(self) -> None:
        rp = ResearchProject(project_id="rp-dup", title="Dup")
        cl1 = Claim(
            claim_id="cl-dup",
            project_id="rp-dup",
            claim_text="First",
            support_state="unsupported",
        )
        cl2 = Claim(
            claim_id="cl-dup",
            project_id="rp-dup",
            claim_text="Second",
            support_state="unsupported",
        )
        g = ProvenanceGraph(projects=[rp], claims=[cl1, cl2])
        assert g.unsupported_claims("rp-dup")[0].claim_text == "Second"

class TestGetters:
    "Tests for ProvenanceGraph lookup getters and sorted all_* iterators."

    def _g(self) -> ProvenanceGraph:
        rp1 = ResearchProject(project_id="rp-1", title="P1")
        rp2 = ResearchProject(project_id="rp-2", title="P2")
        rq1 = ResearchQuestion(question_id="rq-1", project_id="rp-1", question_text="Q1")
        rq2 = ResearchQuestion(question_id="rq-2", project_id="rp-1", question_text="Q2")
        src1 = Source(source_id="src-1", project_id="rp-1", title="S1", origin="learner_entered")
        src2 = Source(source_id="src-2", project_id="rp-1", title="S2", origin="learner_entered")
        ev1 = EvidenceUnit(evidence_id="ev-1", project_id="rp-1", source_id="src-1", source_version=1, kind="direct_quote", locator="p.1", content="c1")
        ev2 = EvidenceUnit(evidence_id="ev-2", project_id="rp-1", source_id="src-2", source_version=1, kind="direct_quote", locator="p.2", content="c2")
        cl1 = Claim(claim_id="cl-1", project_id="rp-1", claim_text="T1", support_state="supported", evidence_links=[ClaimEvidenceLink(evidence_id="ev-1", link_type="supports")])
        cl2 = Claim(claim_id="cl-2", project_id="rp-1", claim_text="T2", support_state="unsupported")
        sec1 = PaperSection(section_id="sec-1", project_id="rp-1", section_title="Sec1")
        sec2 = PaperSection(section_id="sec-2", project_id="rp-1", section_title="Sec2")
        cit1 = CitationLink(citation_id="cit-1", project_id="rp-1", claim_id="cl-1", source_id="src-1")
        cit2 = CitationLink(citation_id="cit-2", project_id="rp-1", claim_id="cl-1", source_id="src-1")
        return ProvenanceGraph(
            projects=[rp1, rp2], questions=[rq1, rq2], sources=[src1, src2],
            evidence_units=[ev1, ev2], claims=[cl1, cl2], sections=[sec1, sec2],
            citations=[cit1, cit2],
        )

    def test_project_hit(self) -> None:
        assert self._g().project("rp-1") is not None
    def test_question_hit(self) -> None:
        assert self._g().question("rq-1") is not None
    def test_source_hit(self) -> None:
        assert self._g().source("src-1") is not None
    def test_evidence_hit(self) -> None:
        assert self._g().evidence("ev-1") is not None
    def test_claim_hit(self) -> None:
        assert self._g().claim("cl-1") is not None
    def test_section_hit(self) -> None:
        assert self._g().section("sec-1") is not None
    def test_citation_hit(self) -> None:
        assert self._g().citation("cit-1") is not None

    def test_project_miss(self) -> None:
        assert self._g().project("rp-nope") is None
    def test_question_miss(self) -> None:
        assert self._g().question("rq-nope") is None
    def test_source_miss(self) -> None:
        assert self._g().source("src-nope") is None
    def test_evidence_miss(self) -> None:
        assert self._g().evidence("ev-nope") is None
    def test_claim_miss(self) -> None:
        assert self._g().claim("cl-nope") is None
    def test_section_miss(self) -> None:
        assert self._g().section("sec-nope") is None
    def test_citation_miss(self) -> None:
        assert self._g().citation("cit-nope") is None

    def test_all_projects_sorted(self) -> None:
        assert [p.project_id for p in self._g().all_projects()] == ["rp-1", "rp-2"]
    def test_all_questions_sorted(self) -> None:
        assert [q.question_id for q in self._g().all_questions()] == ["rq-1", "rq-2"]
    def test_all_sources_sorted(self) -> None:
        assert [s.source_id for s in self._g().all_sources()] == ["src-1", "src-2"]
    def test_all_evidence_sorted(self) -> None:
        assert [e.evidence_id for e in self._g().all_evidence()] == ["ev-1", "ev-2"]
    def test_all_claims_sorted(self) -> None:
        assert [cl.claim_id for cl in self._g().all_claims()] == ["cl-1", "cl-2"]
    def test_all_sections_sorted(self) -> None:
        assert [s.section_id for s in self._g().all_sections()] == ["sec-1", "sec-2"]
    def test_all_citations_sorted(self) -> None:
        assert [c.citation_id for c in self._g().all_citations()] == ["cit-1", "cit-2"]

    def test_empty_all_projects(self) -> None:
        assert ProvenanceGraph().all_projects() == []
    def test_empty_all_evidence(self) -> None:
        assert ProvenanceGraph().all_evidence() == []
    def test_empty_all_claims(self) -> None:
        assert ProvenanceGraph().all_claims() == []