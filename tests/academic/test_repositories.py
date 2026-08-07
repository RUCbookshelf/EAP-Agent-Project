"""Tests for app/academic/repositories.py — full protocol + behavior matrix."""

from __future__ import annotations

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
from app.academic.errors import AcademicDomainError
from app.academic.repositories import (
    AcademicRepositories,
    CitationLinkRepository,
    CitationVerificationRecordRepository,
    ClaimRepository,
    EvidenceRepository,
    InMemoryRepositories,
    PaperSectionRepository,
    ResearchProjectRepository,
    ResearchQuestionRepository,
    SourceRepository,
)


# ---------------------------------------------------------------------------
# Helpers — small synthetic entities
# ---------------------------------------------------------------------------


def _project(pid: str = "rp-001") -> ResearchProject:
    return ResearchProject(project_id=pid, title=f"Project {pid}")


def _question(qid: str = "rq-001", pid: str = "rp-001") -> ResearchQuestion:
    return ResearchQuestion(question_id=qid, project_id=pid, question_text=f"Q {qid}")


def _source(sid: str = "src-001", pid: str = "rp-001") -> Source:
    return Source(source_id=sid, project_id=pid, title=f"Source {sid}", origin="learner_entered")


def _evidence(
    eid: str = "ev-001",
    pid: str = "rp-001",
    sid: str = "src-001",
) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=eid,
        project_id=pid,
        source_id=sid,
        source_version=1,
        kind="direct_quote",
        locator="p.1",
        content=f"Evidence {eid}",
    )


def _claim(
    cid: str = "cl-001",
    pid: str = "rp-001",
    evidence_links: list[ClaimEvidenceLink] | None = None,
) -> Claim:
    links = evidence_links or []
    return Claim(
        claim_id=cid,
        project_id=pid,
        claim_text=f"Claim {cid}",
        evidence_links=links,
    )


def _section(secid: str = "sec-001", pid: str = "rp-001") -> PaperSection:
    return PaperSection(section_id=secid, project_id=pid, section_title=f"Section {secid}")


def _citation(
    citid: str = "cit-001",
    pid: str = "rp-001",
    claim_id: str = "cl-001",
    source_id: str = "src-001",
) -> CitationLink:
    return CitationLink(
        citation_id=citid,
        project_id=pid,
        claim_id=claim_id,
        source_id=source_id,
    )


def _record(
    rid: str = "vr-001",
    citid: str = "cit-001",
    run_time: datetime | None = None,
) -> CitationVerificationRecord:
    if run_time is None:
        run_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return CitationVerificationRecord(
        record_id=rid,
        citation_id=citid,
        rule_id="rule-1",
        rule_version="1.0",
        run_time=run_time,
        result="unverified",
    )


def _verified_record(
    rid: str = "vr-001",
    citid: str = "cit-001",
    run_time: datetime | None = None,
) -> CitationVerificationRecord:
    if run_time is None:
        run_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return CitationVerificationRecord(
        record_id=rid,
        citation_id=citid,
        rule_id="rule-1",
        rule_version="1.0",
        source_revision_hash="a" * 64,
        run_time=run_time,
        result="verified",
    )


# ===========================================================================
# Projects
# ===========================================================================


class TestResearchProjectRepository:
    def test_create_get_list(self) -> None:
        repos = InMemoryRepositories()
        p = _project("rp-001")
        repos.projects.create(p)
        assert repos.projects.get("rp-001") == p
        assert repos.projects.list() == [p]

    def test_create_duplicate_raises(self) -> None:
        repos = InMemoryRepositories()
        repos.projects.create(_project("rp-001"))
        with pytest.raises(AcademicDomainError) as exc_info:
            repos.projects.create(_project("rp-001"))
        assert exc_info.value.code == "duplicate_id"
        assert "rp-001" in str(exc_info.value)

    def test_get_unknown_returns_none(self) -> None:
        repos = InMemoryRepositories()
        assert repos.projects.get("rp-nonesuch") is None

    def test_list_sorted_by_id(self) -> None:
        repos = InMemoryRepositories()
        repos.projects.create(_project("rp-003"))
        repos.projects.create(_project("rp-001"))
        repos.projects.create(_project("rp-002"))
        ids = [p.project_id for p in repos.projects.list()]
        assert ids == ["rp-001", "rp-002", "rp-003"]


# ===========================================================================
# Questions
# ===========================================================================


class TestResearchQuestionRepository:
    def test_create_get_list(self) -> None:
        repos = InMemoryRepositories()
        q = _question("rq-001")
        repos.questions.create(q)
        assert repos.questions.get("rq-001") == q
        assert repos.questions.list() == [q]

    def test_get_unknown_returns_none(self) -> None:
        repos = InMemoryRepositories()
        assert repos.questions.get("rq-nonesuch") is None

    def test_list_sorted_by_id(self) -> None:
        repos = InMemoryRepositories()
        repos.questions.create(_question("rq-003"))
        repos.questions.create(_question("rq-001"))
        repos.questions.create(_question("rq-002"))
        ids = [q.question_id for q in repos.questions.list()]
        assert ids == ["rq-001", "rq-002", "rq-003"]


# ===========================================================================
# Sources
# ===========================================================================


class TestSourceRepository:
    def test_create_get_list(self) -> None:
        repos = InMemoryRepositories()
        s = _source("src-001")
        repos.sources.create(s)
        assert repos.sources.get("src-001") == s
        assert repos.sources.list() == [s]

    def test_create_duplicate_raises(self) -> None:
        repos = InMemoryRepositories()
        repos.sources.create(_source("src-001"))
        with pytest.raises(AcademicDomainError) as exc_info:
            repos.sources.create(_source("src-001"))
        assert exc_info.value.code == "duplicate_id"

    def test_get_unknown_returns_none(self) -> None:
        repos = InMemoryRepositories()
        assert repos.sources.get("src-nonesuch") is None

    def test_list_sorted_by_id(self) -> None:
        repos = InMemoryRepositories()
        repos.sources.create(_source("src-003"))
        repos.sources.create(_source("src-001"))
        repos.sources.create(_source("src-002"))
        ids = [s.source_id for s in repos.sources.list()]
        assert ids == ["src-001", "src-002", "src-003"]

    def test_save_upsert(self) -> None:
        repos = InMemoryRepositories()
        s = _source("src-001")
        repos.sources.create(s)
        s2 = s.new_version(title="Updated Source")
        repos.sources.save(s2)
        got = repos.sources.get("src-001")
        assert got is not None
        assert got.version == 2
        assert got.title == "Updated Source"

    def test_save_unknown_raises(self) -> None:
        repos = InMemoryRepositories()
        with pytest.raises(AcademicDomainError) as exc_info:
            repos.sources.save(_source("src-nonesuch"))
        assert exc_info.value.code == "entity_not_found"


# ===========================================================================
# Evidence
# ===========================================================================


class TestEvidenceRepository:
    def test_create_get_list(self) -> None:
        repos = InMemoryRepositories()
        ev = _evidence("ev-001")
        repos.evidence.create(ev)
        assert repos.evidence.get("ev-001") == ev
        assert repos.evidence.list() == [ev]

    def test_get_unknown_returns_none(self) -> None:
        repos = InMemoryRepositories()
        assert repos.evidence.get("ev-nonesuch") is None

    def test_list_sorted_by_id(self) -> None:
        repos = InMemoryRepositories()
        repos.evidence.create(_evidence("ev-003"))
        repos.evidence.create(_evidence("ev-001"))
        repos.evidence.create(_evidence("ev-002"))
        ids = [e.evidence_id for e in repos.evidence.list()]
        assert ids == ["ev-001", "ev-002", "ev-003"]


# ===========================================================================
# Claims
# ===========================================================================


class TestClaimRepository:
    def test_create_get_list(self) -> None:
        repos = InMemoryRepositories()
        cl = _claim("cl-001")
        repos.claims.create(cl)
        assert repos.claims.get("cl-001") == cl
        assert repos.claims.list() == [cl]

    def test_get_unknown_returns_none(self) -> None:
        repos = InMemoryRepositories()
        assert repos.claims.get("cl-nonesuch") is None

    def test_list_sorted_by_id(self) -> None:
        repos = InMemoryRepositories()
        repos.claims.create(_claim("cl-003"))
        repos.claims.create(_claim("cl-001"))
        repos.claims.create(_claim("cl-002"))
        ids = [c.claim_id for c in repos.claims.list()]
        assert ids == ["cl-001", "cl-002", "cl-003"]

    def test_save_upsert_updates_links(self) -> None:
        repos = InMemoryRepositories()
        repos.evidence.create(_evidence("ev-001"))
        cl = _claim("cl-001")
        repos.claims.create(cl)
        link = ClaimEvidenceLink(evidence_id="ev-001", link_type="supports")
        cl2 = _claim("cl-001", evidence_links=[link])
        repos.claims.save(cl2)
        got = repos.claims.get("cl-001")
        assert got is not None
        assert len(got.evidence_links) == 1
        assert got.evidence_links[0].link_type == "supports"

    def test_save_unknown_raises(self) -> None:
        repos = InMemoryRepositories()
        with pytest.raises(AcademicDomainError) as exc_info:
            repos.claims.save(_claim("cl-nonesuch"))
        assert exc_info.value.code == "entity_not_found"


# ===========================================================================
# Sections
# ===========================================================================


class TestPaperSectionRepository:
    def test_create_get_list(self) -> None:
        repos = InMemoryRepositories()
        sec = _section("sec-001")
        repos.sections.create(sec)
        assert repos.sections.get("sec-001") == sec
        assert repos.sections.list() == [sec]

    def test_get_unknown_returns_none(self) -> None:
        repos = InMemoryRepositories()
        assert repos.sections.get("sec-nonesuch") is None

    def test_list_sorted_by_id(self) -> None:
        repos = InMemoryRepositories()
        repos.sections.create(_section("sec-003"))
        repos.sections.create(_section("sec-001"))
        repos.sections.create(_section("sec-002"))
        ids = [s.section_id for s in repos.sections.list()]
        assert ids == ["sec-001", "sec-002", "sec-003"]


# ===========================================================================
# Citations
# ===========================================================================


class TestCitationLinkRepository:
    def test_create_get_list(self) -> None:
        repos = InMemoryRepositories()
        cit = _citation("cit-001")
        repos.citations.create(cit)
        assert repos.citations.get("cit-001") == cit
        assert repos.citations.list() == [cit]

    def test_get_unknown_returns_none(self) -> None:
        repos = InMemoryRepositories()
        assert repos.citations.get("cit-nonesuch") is None

    def test_list_sorted_by_id(self) -> None:
        repos = InMemoryRepositories()
        repos.citations.create(_citation("cit-003"))
        repos.citations.create(_citation("cit-001"))
        repos.citations.create(_citation("cit-002"))
        ids = [c.citation_id for c in repos.citations.list()]
        assert ids == ["cit-001", "cit-002", "cit-003"]

    def test_save_upsert(self) -> None:
        repos = InMemoryRepositories()
        cit = _citation("cit-001")
        repos.citations.create(cit)
        cit2 = CitationLink(
            citation_id="cit-001",
            project_id="rp-001",
            claim_id="cl-001",
            source_id="src-001",
            verification_status="verified",
        )
        repos.citations.save(cit2)
        got = repos.citations.get("cit-001")
        assert got is not None
        assert got.verification_status == "verified"

    def test_save_unknown_raises(self) -> None:
        repos = InMemoryRepositories()
        with pytest.raises(AcademicDomainError) as exc_info:
            repos.citations.save(_citation("cit-nonesuch"))
        assert exc_info.value.code == "entity_not_found"


# ===========================================================================
# Citation Verification Records (append-only)
# ===========================================================================


class TestCitationVerificationRecordRepository:
    def test_append_get_list(self) -> None:
        repos = InMemoryRepositories()
        rec = _record("vr-001", "cit-001")
        repos.records.append(rec)
        assert repos.records.list() == [rec]

    def test_append_duplicate_raises(self) -> None:
        repos = InMemoryRepositories()
        repos.records.append(_record("vr-001", "cit-001"))
        with pytest.raises(AcademicDomainError) as exc_info:
            repos.records.append(_record("vr-001", "cit-001"))
        assert exc_info.value.code == "duplicate_id"
        assert "vr-001" in str(exc_info.value)

    def test_list_for_citation_sorted_by_run_time(self) -> None:
        repos = InMemoryRepositories()
        t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2025, 6, 15, tzinfo=timezone.utc)
        repos.records.append(_record("vr-002", "cit-001", run_time=t2))
        repos.records.append(_record("vr-001", "cit-001", run_time=t1))
        result = repos.records.list_for_citation("cit-001")
        assert [r.record_id for r in result] == ["vr-001", "vr-002"]

    def test_list_for_citation_empty(self) -> None:
        repos = InMemoryRepositories()
        assert repos.records.list_for_citation("cit-nonesuch") == []

    def test_list_sorted_by_record_id(self) -> None:
        repos = InMemoryRepositories()
        repos.records.append(_record("vr-003", "cit-001"))
        repos.records.append(_record("vr-001", "cit-001"))
        repos.records.append(_record("vr-002", "cit-001"))
        ids = [r.record_id for r in repos.records.list()]
        assert ids == ["vr-001", "vr-002", "vr-003"]

    def test_no_update_or_delete_attributes(self) -> None:
        repos = InMemoryRepositories()
        assert not hasattr(repos.records, "update")
        assert not hasattr(repos.records, "delete")
        assert not hasattr(repos.records, "save")


# ===========================================================================
# runtime_checkable conformance
# ===========================================================================


class TestProtocolConformance:
    def test_in_memory_repositories_satisfies_academic_repositories(self) -> None:
        repos = InMemoryRepositories()
        assert isinstance(repos, AcademicRepositories)

    def test_individual_protocol_conformance(self) -> None:
        repos = InMemoryRepositories()
        assert isinstance(repos.projects, ResearchProjectRepository)
        assert isinstance(repos.questions, ResearchQuestionRepository)
        assert isinstance(repos.sources, SourceRepository)
        assert isinstance(repos.evidence, EvidenceRepository)
        assert isinstance(repos.claims, ClaimRepository)
        assert isinstance(repos.sections, PaperSectionRepository)
        assert isinstance(repos.citations, CitationLinkRepository)
        assert isinstance(repos.records, CitationVerificationRecordRepository)


# ===========================================================================
# to_graph round-trip
# ===========================================================================


class TestToGraph:
    def test_round_trip(self) -> None:
        repos = InMemoryRepositories()

        p = _project("rp-001")
        repos.projects.create(p)

        q = _question("rq-001")
        repos.questions.create(q)

        s = _source("src-001")
        repos.sources.create(s)

        ev = _evidence("ev-001", sid="src-001")
        repos.evidence.create(ev)

        link = ClaimEvidenceLink(evidence_id="ev-001", link_type="supports")
        cl = _claim("cl-001", evidence_links=[link])
        repos.claims.create(cl)

        sec = _section("sec-001")
        repos.sections.create(sec)

        cit = _citation("cit-001", claim_id="cl-001", source_id="src-001")
        repos.citations.create(cit)

        rec = _verified_record("vr-001", "cit-001")
        repos.records.append(rec)

        graph = repos.to_graph()

        # evidence_for_claim returns the evidence linked to the claim
        ev_result = graph.evidence_for_claim("cl-001")
        assert len(ev_result) == 1
        assert ev_result[0].evidence_id == "ev-001"

        # records_for_citation returns the verification record
        rec_result = graph.records_for_citation("cit-001")
        assert len(rec_result) == 1
        assert rec_result[0].record_id == "vr-001"

        # all_* queries work
        assert len(graph.all_projects()) == 1
        assert len(graph.all_questions()) == 1
        assert len(graph.all_sources()) == 1
        assert len(graph.all_evidence()) == 1
        assert len(graph.all_claims()) == 1
        assert len(graph.all_sections()) == 1
        assert len(graph.all_citations()) == 1

        # deterministic sorted lists
        repos.projects.create(_project("rp-002"))
        graph2 = repos.to_graph()
        assert [p.project_id for p in graph2.all_projects()] == ["rp-001", "rp-002"]


# ===========================================================================
# Zero L2 imports
# ===========================================================================


class TestZeroL2Imports:
    def test_no_l2_imports(self) -> None:
        """repositories.py must not import from existing app modules (L2 or revision)."""
        import app.academic.repositories as mod

        source = open(mod.__file__).read()  # noqa: SIM115
        assert "from app.revision" not in source
        assert "from app." not in source or "from app.academic" in source.split("from app.academic")[0] + "from app.academic"
        # Simpler check: only app.academic submodules imported
        import_lines = [l for l in source.splitlines() if l.startswith("from app.")]
        for line in import_lines:
            assert line.startswith("from .") or "app.academic" in line, f"Unexpected import: {line}"
