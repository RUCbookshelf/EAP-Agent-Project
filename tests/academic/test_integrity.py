"""Tests for app.academic.integrity.IntegrityService and rules."""

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
from app.academic.integrity import (
    INTEGRITY_RULES,
    INTEGRITY_RULES_VERSION,
    IntegrityService,
    IntegrityViolation,
)
from app.academic.provenance import ProvenanceGraph


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 2, tzinfo=timezone.utc)


def _rp(pid: str = "rp-1", title: str = "P1") -> ResearchProject:
    return ResearchProject(project_id=pid, title=title)


def _rq(qid: str = "rq-1", pid: str = "rp-1") -> ResearchQuestion:
    return ResearchQuestion(question_id=qid, project_id=pid, question_text=f"Q for {qid}")


def _src(sid: str = "src-1", pid: str = "rp-1", avail: str = "active") -> Source:
    return Source(source_id=sid, project_id=pid, title=f"Source {sid}", origin="learner_entered", availability=avail)


def _ev(eid: str = "ev-1", pid: str = "rp-1", sid: str = "src-1", rq_ids=None) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=eid, project_id=pid, source_id=sid, source_version=1,
        kind="direct_quote", locator="p.1", content="c",
        rq_ids=rq_ids or [],
    )


def _cl_supported_with_evidence(cid: str = "cl-1", pid: str = "rp-1", ev_id: str = "ev-1") -> Claim:
    """Construct a supported claim with evidence link using model_construct to bypass validators."""
    link = ClaimEvidenceLink.model_construct(evidence_id=ev_id, link_type="supports")
    return Claim.model_construct(
        claim_id=cid, project_id=pid, claim_text="T",
        support_state="supported", rq_ids=[], section_ids=[],
        evidence_links=[link],
    )


def _cl_supported_empty(cid: str = "cl-1", pid: str = "rp-1") -> Claim:
    """Supported claim with zero evidence links (invalid per validators, but defense-in-depth)."""
    return Claim.model_construct(
        claim_id=cid, project_id=pid, claim_text="T",
        support_state="supported", rq_ids=[], section_ids=[],
        evidence_links=[],
    )


def _cl_partial_empty(cid: str = "cl-1", pid: str = "rp-1") -> Claim:
    return Claim.model_construct(
        claim_id=cid, project_id=pid, claim_text="T",
        support_state="partially_supported", rq_ids=[], section_ids=[],
        evidence_links=[],
    )


def _cit(cid: str = "cit-1", pid: str = "rp-1", claim_id: str = "cl-1",
         sid: str = "src-1", ev_id: str | None = None,
         ver_status: str = "unverified") -> CitationLink:
    return CitationLink(
        citation_id=cid, project_id=pid, claim_id=claim_id,
        source_id=sid, evidence_id=ev_id, verification_status=ver_status,
    )


def _cit_verified(cid: str = "cit-1", pid: str = "rp-1", claim_id: str = "cl-1",
                   sid: str = "src-1") -> CitationLink:
    return CitationLink(
        citation_id=cid, project_id=pid, claim_id=claim_id,
        source_id=sid, verification_status="verified",
    )


def _vr(cid: str = "cit-1", result: str = "verified") -> CitationVerificationRecord:
    return CitationVerificationRecord(
        record_id="vr-1", citation_id=cid, rule_id="rule-basic",
        rule_version="1.0", source_revision_hash=_sha256("rev"),
        run_time=T0, result=result,
    )


def _sec(sid: str = "sec-1", pid: str = "rp-1", parent: str | None = None) -> PaperSection:
    return PaperSection(section_id=sid, project_id=pid, section_title=f"Section {sid}", parent_section_id=parent)


class TestReviewFindings:
    """WU4 review fixes: missing claim-evidence target and summarized R06 details."""

    def test_claim_link_to_missing_evidence_flagged(self) -> None:
        rp = ResearchProject(project_id="rp-rf", title="RF")
        cl = Claim.model_construct(
            claim_id="cl-rf",
            project_id="rp-rf",
            claim_text="T",
            support_state="supported",
            evidence_links=[ClaimEvidenceLink(evidence_id="ev-missing", link_type="supports")],
        )
        g = ProvenanceGraph(projects=[rp], claims=[cl])
        violations = IntegrityService().validate_project("rp-rf", g)
        rule_ids = [v.rule_id for v in violations]
        assert "ACAD-RULE-06" in rule_ids
        r6 = [v for v in violations if v.rule_id == "ACAD-RULE-06"]
        assert len(r6) == 1
        assert "not found" in r6[0].detail

    def test_r06_detail_summarizes_all_references(self) -> None:
        rp1 = ResearchProject(project_id="rp-s", title="S")
        rp2 = ResearchProject(project_id="rp-other", title="Other")
        rq_other = ResearchQuestion(
            question_id="rq-other", project_id="rp-other", question_text="Q"
        )
        sec_other = PaperSection(
            section_id="sec-other", project_id="rp-other", section_title="S"
        )
        cl = Claim.model_construct(
            claim_id="cl-s",
            project_id="rp-s",
            claim_text="T",
            support_state="unsupported",
            rq_ids=["rq-other"],
            section_ids=["sec-other"],
        )
        g = ProvenanceGraph(
            projects=[rp1, rp2], questions=[rq_other], sections=[sec_other], claims=[cl]
        )
        violations = IntegrityService().validate_project("rp-s", g)
        r6 = [v for v in violations if v.rule_id == "ACAD-RULE-06"]
        assert len(r6) == 1
        assert r6[0].entity_id == "cl-s"
        assert "rq_id" in r6[0].detail and "section_id" in r6[0].detail


class TestRulesRegistry:
    def test_rules_version(self) -> None:
        assert IntegrityService.rules_version() == "academic-integrity-rules-v0.1.0"

    def test_rules_returns_copy(self) -> None:
        r = IntegrityService.rules()
        assert isinstance(r, dict)
        assert len(r) == 7
        # Modifying copy should not affect original
        r["FAKE"] = "fake"
        assert "FAKE" not in INTEGRITY_RULES

    def test_all_rule_ids_present(self) -> None:
        expected = [f"ACAD-RULE-0{i}" for i in range(1, 8)]
        assert list(INTEGRITY_RULES.keys()) == expected


class TestIntegrityViolation:
    def test_frozen(self) -> None:
        v = IntegrityViolation(
            rule_id="ACAD-RULE-01", entity_type="claim", entity_id="cl-1",
            project_id="rp-1", detail="test",
        )
        with pytest.raises(Exception):
            v.rule_id = "changed"  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(Exception):
            IntegrityViolation(
                rule_id="ACAD-RULE-01", entity_type="claim", entity_id="cl-1",
                project_id="rp-1", detail="test", extra_field="bad",
            )


class TestCleanProject:
    """A valid project should produce zero violations."""

    def test_clean_project(self) -> None:
        rp1 = _rp()
        rq1 = _rq()
        src1 = _src()
        ev1 = _ev()
        cl1 = _cl_supported_with_evidence()
        sec1 = _sec()
        cit1 = _cit(ev_id="ev-1")
        vr1 = _vr()

        g = ProvenanceGraph(
            projects=[rp1], questions=[rq1], sources=[src1],
            evidence_units=[ev1], claims=[cl1], sections=[sec1],
            citations=[cit1], records=[vr1],
        )
        svc = IntegrityService()
        violations = svc.validate_project("rp-1", g)
        assert violations == []


class TestR01:
    """ACAD-RULE-01: supported/partially_supported claim with zero evidence links."""

    def test_supported_no_links(self) -> None:
        cl1 = _cl_supported_empty()
        g = ProvenanceGraph(projects=[_rp()], claims=[cl1])
        violations = IntegrityService().validate_project("rp-1", g)
        assert len(violations) == 1
        assert violations[0].rule_id == "ACAD-RULE-01"
        assert violations[0].entity_type == "claim"
        assert violations[0].entity_id == "cl-1"

    def test_partially_supported_no_links(self) -> None:
        cl1 = _cl_partial_empty()
        g = ProvenanceGraph(projects=[_rp()], claims=[cl1])
        violations = IntegrityService().validate_project("rp-1", g)
        assert len(violations) == 1
        assert violations[0].rule_id == "ACAD-RULE-01"

    def test_unsupported_no_violation(self) -> None:
        cl1 = Claim(
            claim_id="cl-1", project_id="rp-1", claim_text="T",
            support_state="unsupported",
        )
        g = ProvenanceGraph(projects=[_rp()], claims=[cl1])
        violations = IntegrityService().validate_project("rp-1", g)
        assert violations == []


class TestR02:
    """ACAD-RULE-02: EvidenceUnit references missing or cross-project Source."""

    def test_missing_source(self) -> None:
        ev1 = _ev(sid="src-missing")
        g = ProvenanceGraph(projects=[_rp()], evidence_units=[ev1])
        violations = IntegrityService().validate_project("rp-1", g)
        assert len(violations) == 1
        assert violations[0].rule_id == "ACAD-RULE-02"
        assert violations[0].entity_id == "ev-1"

    def test_cross_project_source(self) -> None:
        rp1 = _rp()
        rp2 = _rp("rp-2", "P2")
        src2 = _src("src-2", "rp-2")
        ev1 = _ev(sid="src-2")
        g = ProvenanceGraph(projects=[rp1, rp2], sources=[src2], evidence_units=[ev1])
        violations = IntegrityService().validate_project("rp-1", g)
        assert len(violations) == 1
        assert violations[0].rule_id == "ACAD-RULE-02"


class TestR03:
    """ACAD-RULE-03: CitationLink references missing or cross-project Source."""

    def test_missing_source(self) -> None:
        cit1 = _cit(sid="src-missing")
        cl1 = _cl_supported_with_evidence()
        g = ProvenanceGraph(projects=[_rp()], claims=[cl1], citations=[cit1])
        violations = IntegrityService().validate_project("rp-1", g)
        r03 = [v for v in violations if v.rule_id == "ACAD-RULE-03"]
        assert len(r03) == 1
        assert r03[0].entity_id == "cit-1"


class TestR04:
    """ACAD-RULE-04: CitationLink references unrelated EvidenceUnit."""

    def test_evidence_source_mismatch(self) -> None:
        rp1 = _rp()
        src1 = _src("src-1")
        src2 = _src("src-2")
        ev1 = _ev(eid="ev-1", sid="src-1")
        cl1 = _cl_supported_with_evidence(ev_id="ev-1")
        # citation links to src-2 but evidence is from src-1
        cit1 = _cit(cid="cit-1", sid="src-2", ev_id="ev-1")
        g = ProvenanceGraph(
            projects=[rp1], sources=[src1, src2], evidence_units=[ev1],
            claims=[cl1], citations=[cit1],
        )
        violations = IntegrityService().validate_project("rp-1", g)
        r04 = [v for v in violations if v.rule_id == "ACAD-RULE-04"]
        assert len(r04) == 1
        assert "source_id" in r04[0].detail

    def test_evidence_missing(self) -> None:
        rp1 = _rp()
        src1 = _src("src-1")
        cl1 = _cl_supported_with_evidence()
        cit1 = _cit(cid="cit-1", sid="src-1", ev_id="ev-missing")
        g = ProvenanceGraph(
            projects=[rp1], sources=[src1], claims=[cl1], citations=[cit1],
        )
        violations = IntegrityService().validate_project("rp-1", g)
        r04 = [v for v in violations if v.rule_id == "ACAD-RULE-04"]
        assert len(r04) == 1
        assert "not found" in r04[0].detail


class TestR05:
    """ACAD-RULE-05: Removed Source still referenced by EvidenceUnit or CitationLink."""

    def test_removed_source_referenced_by_evidence(self) -> None:
        rp1 = _rp()
        src_r = _src("src-r", avail="removed")
        ev1 = _ev(sid="src-r")
        g = ProvenanceGraph(projects=[rp1], sources=[src_r], evidence_units=[ev1])
        violations = IntegrityService().validate_project("rp-1", g)
        r05 = [v for v in violations if v.rule_id == "ACAD-RULE-05"]
        assert len(r05) == 1
        assert r05[0].entity_type == "source"
        assert r05[0].entity_id == "src-r"

    def test_removed_source_not_referenced(self) -> None:
        rp1 = _rp()
        src_r = _src("src-r", avail="removed")
        g = ProvenanceGraph(projects=[rp1], sources=[src_r])
        violations = IntegrityService().validate_project("rp-1", g)
        r05 = [v for v in violations if v.rule_id == "ACAD-RULE-05"]
        assert r05 == []


class TestR06:
    """ACAD-RULE-06: Cross-project reference detected."""

    def test_evidence_rq_cross_project(self) -> None:
        rp1 = _rp()
        rp2 = _rp("rp-2", "P2")
        rq_other = _rq("rq-2", "rp-2")
        ev1 = EvidenceUnit(
            evidence_id="ev-1", project_id="rp-1", source_id="src-1",
            source_version=1, kind="direct_quote", locator="p.1",
            content="c", rq_ids=["rq-2"],
        )
        src1 = _src()
        g = ProvenanceGraph(
            projects=[rp1, rp2], questions=[rq_other],
            sources=[src1], evidence_units=[ev1],
        )
        violations = IntegrityService().validate_project("rp-1", g)
        r06 = [v for v in violations if v.rule_id == "ACAD-RULE-06"]
        assert len(r06) == 1
        assert r06[0].entity_type == "evidence_unit"
        assert "rq_id" in r06[0].detail

    def test_section_parent_cross_project(self) -> None:
        rp1 = _rp()
        rp2 = _rp("rp-2", "P2")
        sec_parent = _sec("sec-p", "rp-2")
        sec_child = _sec("sec-c", "rp-1", parent="sec-p")
        g = ProvenanceGraph(
            projects=[rp1, rp2], sections=[sec_parent, sec_child],
        )
        violations = IntegrityService().validate_project("rp-1", g)
        r06 = [v for v in violations if v.rule_id == "ACAD-RULE-06"]
        assert len(r06) == 1
        assert r06[0].entity_type == "paper_section"

    def test_citation_claim_cross_project(self) -> None:
        rp1 = _rp()
        rp2 = _rp("rp-2", "P2")
        src1 = _src()
        cl_other = Claim(
            claim_id="cl-2", project_id="rp-2", claim_text="Other",
            support_state="unsupported",
        )
        cit1 = CitationLink(
            citation_id="cit-1", project_id="rp-1", claim_id="cl-2",
            source_id="src-1",
        )
        g = ProvenanceGraph(
            projects=[rp1, rp2], sources=[src1], claims=[cl_other],
            citations=[cit1],
        )
        violations = IntegrityService().validate_project("rp-1", g)
        r06 = [v for v in violations if v.rule_id == "ACAD-RULE-06"]
        assert len(r06) == 1
        assert r06[0].entity_type == "citation_link"


class TestR07:
    """ACAD-RULE-07: verified citation without verified verification record."""

    def test_verified_no_record(self) -> None:
        rp1 = _rp()
        src1 = _src()
        cl1 = _cl_supported_with_evidence()
        cit1 = _cit_verified()
        g = ProvenanceGraph(
            projects=[rp1], sources=[src1], claims=[cl1], citations=[cit1],
        )
        violations = IntegrityService().validate_project("rp-1", g)
        r07 = [v for v in violations if v.rule_id == "ACAD-RULE-07"]
        assert len(r07) == 1
        assert "ACAD-INV-02" in r07[0].detail

    def test_verified_with_record_no_violation(self) -> None:
        rp1 = _rp()
        src1 = _src()
        cl1 = _cl_supported_with_evidence()
        cit1 = _cit_verified()
        vr1 = _vr()
        g = ProvenanceGraph(
            projects=[rp1], sources=[src1], claims=[cl1],
            citations=[cit1], records=[vr1],
        )
        violations = IntegrityService().validate_project("rp-1", g)
        r07 = [v for v in violations if v.rule_id == "ACAD-RULE-07"]
        assert r07 == []


class TestSorting:
    """Violations must be sorted by (rule_id, entity_id)."""

    def test_sorting_order(self) -> None:
        rp1 = _rp()
        rp2 = _rp("rp-2", "P2")
        rq_other = _rq("rq-2", "rp-2")
        src1 = _src("src-1")
        src2 = _src("src-2", "rp-2")
        ev_a = EvidenceUnit(
            evidence_id="ev-a", project_id="rp-1", source_id="src-miss-a",
            source_version=1, kind="direct_quote", locator="p.1", content="c",
        )
        ev_b = EvidenceUnit(
            evidence_id="ev-b", project_id="rp-1", source_id="src-miss-b",
            source_version=1, kind="direct_quote", locator="p.2", content="d",
        )
        cl1 = _cl_supported_empty("cl-a")
        g = ProvenanceGraph(
            projects=[rp1, rp2], questions=[rq_other], sources=[src1, src2],
            evidence_units=[ev_a, ev_b], claims=[cl1],
        )
        violations = IntegrityService().validate_project("rp-1", g)
        rule_ids = [v.rule_id for v in violations]
        entity_ids = [v.entity_id for v in violations]
        # Verify sorted
        pairs = list(zip(rule_ids, entity_ids))
        assert pairs == sorted(pairs)


class TestNoDuplicateViolations:
    """Each (rule_id, entity_id) appears at most once."""

    def test_no_duplicates(self) -> None:
        rp1 = _rp()
        ev1 = _ev(sid="src-missing")
        # Multiple checks on same evidence should yield one R02 violation
        g = ProvenanceGraph(projects=[rp1], evidence_units=[ev1])
        violations = IntegrityService().validate_project("rp-1", g)
        r02 = [v for v in violations if v.rule_id == "ACAD-RULE-02"]
        assert len(r02) == 1


class TestValidateAll:
    """validate_all returns per-project map."""

    def test_multiple_projects(self) -> None:
        rp1 = _rp("rp-1", "P1")
        rp2 = _rp("rp-2", "P2")
        cl1 = _cl_supported_empty("cl-1", "rp-1")
        cl2 = _cl_supported_empty("cl-2", "rp-2")
        g = ProvenanceGraph(projects=[rp1, rp2], claims=[cl1, cl2])
        result = IntegrityService().validate_all(g)
        assert set(result.keys()) == {"rp-1", "rp-2"}
        assert len(result["rp-1"]) == 1
        assert result["rp-1"][0].entity_id == "cl-1"
        assert len(result["rp-2"]) == 1
        assert result["rp-2"][0].entity_id == "cl-2"

    def test_empty_graph(self) -> None:
        result = IntegrityService().validate_all(ProvenanceGraph())
        assert result == {}