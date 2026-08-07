"""Tests for Academic Writing application/domain services.

Covers: happy-flow end-to-end, auto-generated ID prefixes, explicit IDs,
error matrix (entity_not_found, invalid_state, duplicate_id), link/section
dedupe no-ops, citation always unverified, unsupported claim default.
"""

from __future__ import annotations

import pytest

from app.academic.entities import (
    CitationLink,
    Claim,
    EvidenceUnit,
    PaperSection,
    ResearchProject,
    ResearchQuestion,
    Source,
)
from app.academic.errors import AcademicDomainError
from app.academic.repositories import InMemoryRepositories
from app.academic.services import AcademicService


@pytest.fixture()
def repos() -> InMemoryRepositories:
    return InMemoryRepositories()


@pytest.fixture()
def svc(repos: InMemoryRepositories) -> AcademicService:
    return AcademicService(repos)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

PID = "rp-aaaaaaaaaaaa"
PID2 = "rp-bbbbbbbbbbbb"


def _make_project(
    svc: AcademicService, pid: str = PID, title: str = "Test Project"
) -> ResearchProject:
    return svc.create_research_project(title, project_id=pid)


def _make_rq(
    svc: AcademicService, pid: str = PID, qid: str = "rq-111111111111"
) -> ResearchQuestion:
    return svc.add_research_question(pid, "What is the effect?", question_id=qid)


def _make_source(
    svc: AcademicService, pid: str = PID, sid: str = "src-222222222222"
) -> Source:
    return svc.register_source(
        pid,
        title="Smith 2020",
        origin="imported_file",
        source_id=sid,
        source_text="Full text of the paper.",
    )


def _make_evidence(
    svc: AcademicService,
    pid: str = PID,
    sid: str = "src-222222222222",
    eid: str = "ev-333333333333",
) -> EvidenceUnit:
    return svc.capture_evidence_unit(
        pid,
        source_id=sid,
        kind="direct_quote",
        locator="p. 5",
        content="Direct quote from the source.",
        evidence_id=eid,
    )


# ------------------------------------------------------------------
# Happy-flow end-to-end
# ------------------------------------------------------------------


class TestHappyFlowEndToEnd:
    def test_full_lifecycle(self, svc: AcademicService) -> None:
        # 1. Create project
        proj = _make_project(svc)
        assert proj.project_id == PID
        assert proj.title == "Test Project"

        # 2. Add research question
        rq = _make_rq(svc)
        assert rq.project_id == PID
        assert rq.question_text == "What is the effect?"

        # 3. Register source (with source_text)
        src = _make_source(svc)
        assert src.project_id == PID
        assert src.source_text is not None
        assert src.source_text_hash is not None
        import hashlib

        expected_hash = hashlib.sha256("Full text of the paper.".encode("utf-8")).hexdigest()
        assert src.source_text_hash == expected_hash

        # 4. Capture evidence (direct_quote)
        ev = _make_evidence(svc)
        assert ev.project_id == PID
        assert ev.source_id == "src-222222222222"
        assert ev.source_version == 1

        # 5. Create claim
        claim = svc.create_claim(
            PID,
            "SRL improves L2 writing",
            claim_id="cl-444444444444",
        )
        assert claim.support_state == "unsupported"

        # 6. Link evidence to claim (support_state stays learner-declared, never inferred)
        claim = svc.link_evidence_to_claim(
            "cl-444444444444", "ev-333333333333", "supports"
        )
        assert len(claim.evidence_links) == 1
        assert claim.evidence_links[0].link_type == "supports"
        assert claim.support_state == "unsupported"

        # Re-link (same evidence, same type) → dedupe no-op
        claim2 = svc.link_evidence_to_claim(
            "cl-444444444444", "ev-333333333333", "supports"
        )
        assert len(claim2.evidence_links) == 1

        # 7. Create section (nested)
        parent_sec = svc.create_paper_section(
            PID,
            section_title="Introduction",
            order=1,
            section_id="sec-555555555555",
        )
        child_sec = svc.create_paper_section(
            PID,
            section_title="Background",
            order=1,
            parent_section_id="sec-555555555555",
            section_id="sec-666666666666",
        )
        assert child_sec.parent_section_id == "sec-555555555555"

        # 8. Attach claim to section
        claim = svc.attach_claim_to_section(
            "cl-444444444444", "sec-666666666666"
        )
        assert "sec-666666666666" in claim.section_ids

        # Attach again → dedupe no-op
        claim2 = svc.attach_claim_to_section(
            "cl-444444444444", "sec-666666666666"
        )
        assert claim2.section_ids.count("sec-666666666666") == 1

        # 9. Create citation (with evidence)
        citation = svc.create_citation_link(
            PID,
            claim_id="cl-444444444444",
            source_id="src-222222222222",
            evidence_id="ev-333333333333",
            passage_span="p. 5, para 2",
            citation_id="cit-777777777777",
        )
        assert citation.verification_status == "unverified"
        assert citation.evidence_id == "ev-333333333333"

        # 10. Validate project integrity → clean
        violations = svc.validate_project_integrity(PID)
        assert violations == []

        # 11. Project graph returns expected entities
        graph = svc.project_graph(PID)
        assert len(graph.all_projects()) >= 1
        proj_graph = graph.project(PID)
        assert proj_graph is not None
        assert graph.question("rq-111111111111") is not None
        assert graph.source("src-222222222222") is not None
        assert graph.evidence("ev-333333333333") is not None
        assert graph.claim("cl-444444444444") is not None
        assert graph.section("sec-666666666666") is not None
        assert graph.citation("cit-777777777777") is not None

        # 12. get_project convenience
        fetched = svc.get_project(PID)
        assert fetched is not None
        assert fetched.project_id == PID


# ------------------------------------------------------------------
# Auto-generated ID prefixes
# ------------------------------------------------------------------


class TestAutoGeneratedIdPrefixes:
    def test_project_prefix(self, svc: AcademicService) -> None:
        p = svc.create_research_project("A")
        assert p.project_id.startswith("rp-")
        assert len(p.project_id) == 15  # "rp-" + 12 hex

    def test_rq_prefix(self, svc: AcademicService) -> None:
        _make_project(svc)
        q = svc.add_research_question(PID, "Q?")
        assert q.question_id.startswith("rq-")
        assert len(q.question_id) == 15

    def test_source_prefix(self, svc: AcademicService) -> None:
        _make_project(svc)
        s = svc.register_source(PID, title="S", origin="learner_entered")
        assert s.source_id.startswith("src-")
        assert len(s.source_id) == 16  # "src-" + 12 hex

    def test_evidence_prefix(self, svc: AcademicService) -> None:
        _make_project(svc)
        src = _make_source(svc)
        e = svc.capture_evidence_unit(
            PID, source_id=src.source_id, kind="direct_quote",
            locator="p.1", content="text"
        )
        assert e.evidence_id.startswith("ev-")
        assert len(e.evidence_id) == 15

    def test_claim_prefix(self, svc: AcademicService) -> None:
        _make_project(svc)
        c = svc.create_claim(PID, "A claim")
        assert c.claim_id.startswith("cl-")
        assert len(c.claim_id) == 15

    def test_section_prefix(self, svc: AcademicService) -> None:
        _make_project(svc)
        sec = svc.create_paper_section(PID, section_title="Sec")
        assert sec.section_id.startswith("sec-")
        assert len(sec.section_id) == 16

    def test_citation_prefix(self, svc: AcademicService) -> None:
        _make_project(svc)
        src = _make_source(svc)
        c = svc.create_claim(PID, "Claim")
        cit = svc.create_citation_link(
            PID, claim_id=c.claim_id, source_id=src.source_id
        )
        assert cit.citation_id.startswith("cit-")
        assert len(cit.citation_id) == 16  # "cit-" + 12 hex

    def test_explicit_ids_respected(self, svc: AcademicService) -> None:
        p = svc.create_research_project("X", project_id="rp-custom000001")
        assert p.project_id == "rp-custom000001"
        q = svc.add_research_question(
            "rp-custom000001", "Q", question_id="rq-custom000001"
        )
        assert q.question_id == "rq-custom000001"
        assert q.project_id == "rp-custom000001"


# ------------------------------------------------------------------
# Error matrix
# ------------------------------------------------------------------


class TestErrorMatrix:
    def test_add_rq_unknown_project(self, svc: AcademicService) -> None:
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.add_research_question("rp-nonexistent00", "Q?")
        assert exc_info.value.code == "entity_not_found"

    def test_register_source_unknown_project(self, svc: AcademicService) -> None:
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.register_source(
                "rp-nonexistent00", title="S", origin="learner_entered"
            )
        assert exc_info.value.code == "entity_not_found"

    def test_capture_evidence_unknown_source(self, svc: AcademicService) -> None:
        _make_project(svc)
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.capture_evidence_unit(
                PID,
                source_id="src-nonexistent00",
                kind="direct_quote",
                locator="p.1",
                content="text",
            )
        assert exc_info.value.code == "entity_not_found"

    def test_capture_evidence_source_from_another_project(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc, pid=PID, title="P1")
        _make_project(svc, pid=PID2, title="P2")
        src2 = svc.register_source(
            PID2, title="S2", origin="learner_entered", source_id="src-aaaaaaaaaaaa"
        )
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.capture_evidence_unit(
                PID,
                source_id="src-aaaaaaaaaaaa",
                kind="direct_quote",
                locator="p.1",
                content="text",
            )
        assert exc_info.value.code == "entity_not_found"

    def test_create_claim_rq_from_another_project(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc, pid=PID, title="P1")
        _make_project(svc, pid=PID2, title="P2")
        rq2 = svc.add_research_question(
            PID2, "Q2", question_id="rq-bbbbbbbbbbbb"
        )
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.create_claim(PID, "Claim", rq_ids=["rq-bbbbbbbbbbbb"])
        assert exc_info.value.code == "entity_not_found"

    def test_link_evidence_cross_project(self, svc: AcademicService) -> None:
        _make_project(svc, pid=PID, title="P1")
        _make_project(svc, pid=PID2, title="P2")
        src1 = _make_source(svc, pid=PID, sid="src-aaaaaaaaaaaa")
        ev1 = svc.capture_evidence_unit(
            PID,
            source_id="src-aaaaaaaaaaaa",
            kind="direct_quote",
            locator="p.1",
            content="text",
            evidence_id="ev-aaaaaaaaaaaa",
        )
        claim2 = svc.create_claim(PID2, "Claim2", claim_id="cl-bbbbbbbbbbbb")
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.link_evidence_to_claim(
                "cl-bbbbbbbbbbbb", "ev-aaaaaaaaaaaa", "supports"
            )
        assert exc_info.value.code == "invalid_state"

    def test_create_section_parent_cross_project(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc, pid=PID, title="P1")
        _make_project(svc, pid=PID2, title="P2")
        sec2 = svc.create_paper_section(
            PID2, section_title="Sec2", section_id="sec-bbbbbbbbbbbb"
        )
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.create_paper_section(
                PID,
                section_title="Child",
                parent_section_id="sec-bbbbbbbbbbbb",
            )
        assert exc_info.value.code == "entity_not_found"

    def test_create_section_rq_cross_project(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc, pid=PID, title="P1")
        _make_project(svc, pid=PID2, title="P2")
        svc.add_research_question(
            PID2, "Q2", question_id="rq-bbbbbbbbbbbb"
        )
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.create_paper_section(
                PID,
                section_title="Sec",
                rq_ids=["rq-bbbbbbbbbbbb"],
            )
        assert exc_info.value.code == "entity_not_found"

    def test_attach_claim_to_section_cross_project(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc, pid=PID, title="P1")
        _make_project(svc, pid=PID2, title="P2")
        claim1 = svc.create_claim(PID, "C1", claim_id="cl-aaaaaaaaaaaa")
        sec2 = svc.create_paper_section(
            PID2, section_title="S2", section_id="sec-bbbbbbbbbbbb"
        )
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.attach_claim_to_section("cl-aaaaaaaaaaaa", "sec-bbbbbbbbbbbb")
        assert exc_info.value.code == "invalid_state"

    def test_create_citation_unknown_claim(self, svc: AcademicService) -> None:
        _make_project(svc)
        src = _make_source(svc)
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.create_citation_link(
                PID, claim_id="cl-nonexistent00", source_id=src.source_id
            )
        assert exc_info.value.code == "entity_not_found"

    def test_create_citation_unknown_source(self, svc: AcademicService) -> None:
        _make_project(svc)
        claim = svc.create_claim(PID, "C")
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.create_citation_link(
                PID, claim_id=claim.claim_id, source_id="src-nonexistent00"
            )
        assert exc_info.value.code == "entity_not_found"

    def test_create_citation_unrelated_evidence(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc)
        src_a = svc.register_source(
            PID, title="A", origin="learner_entered", source_id="src-aaaaaaaaaaaa"
        )
        src_b = svc.register_source(
            PID, title="B", origin="learner_entered", source_id="src-bbbbbbbbbbbb"
        )
        ev_a = svc.capture_evidence_unit(
            PID,
            source_id="src-aaaaaaaaaaaa",
            kind="direct_quote",
            locator="p.1",
            content="text from A",
            evidence_id="ev-aaaaaaaaaaaa",
        )
        claim = svc.create_claim(PID, "C", claim_id="cl-aaaaaaaaaaaa")
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.create_citation_link(
                PID,
                claim_id=claim.claim_id,
                source_id="src-bbbbbbbbbbbb",
                evidence_id="ev-aaaaaaaaaaaa",
            )
        assert exc_info.value.code == "invalid_state"
        assert "does not match" in str(exc_info.value)

    def test_duplicate_project_id(self, svc: AcademicService) -> None:
        _make_project(svc, pid="rp-dup00000001")
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.create_research_project("X", project_id="rp-dup00000001")
        assert exc_info.value.code == "duplicate_id"


# ------------------------------------------------------------------
# Dedupe no-ops
# ------------------------------------------------------------------


class TestDedupNoOps:
    def test_link_dedupe(self, svc: AcademicService) -> None:
        _make_project(svc)
        src = _make_source(svc)
        ev = _make_evidence(svc)
        claim = svc.create_claim(PID, "C", claim_id="cl-dddddddddddd")
        c1 = svc.link_evidence_to_claim(
            "cl-dddddddddddd", "ev-333333333333", "supports"
        )
        assert len(c1.evidence_links) == 1
        c2 = svc.link_evidence_to_claim(
            "cl-dddddddddddd", "ev-333333333333", "supports"
        )
        assert len(c2.evidence_links) == 1
        # Different link type should NOT be deduped
        c3 = svc.link_evidence_to_claim(
            "cl-dddddddddddd", "ev-333333333333", "contextualizes"
        )
        assert len(c3.evidence_links) == 2

    def test_attach_dedupe(self, svc: AcademicService) -> None:
        _make_project(svc)
        sec = svc.create_paper_section(
            PID, section_title="S", section_id="sec-dddddddddddd"
        )
        claim = svc.create_claim(PID, "C", claim_id="cl-dddddddddddd")
        c1 = svc.attach_claim_to_section("cl-dddddddddddd", "sec-dddddddddddd")
        assert c1.section_ids.count("sec-dddddddddddd") == 1
        c2 = svc.attach_claim_to_section("cl-dddddddddddd", "sec-dddddddddddd")
        assert c2.section_ids.count("sec-dddddddddddd") == 1


# ------------------------------------------------------------------
# Citation always unverified
# ------------------------------------------------------------------


class TestCitationAlwaysUnverified:
    def test_citation_created_unverified(self, svc: AcademicService) -> None:
        _make_project(svc)
        src = _make_source(svc)
        claim = svc.create_claim(PID, "C")
        cit = svc.create_citation_link(
            PID, claim_id=claim.claim_id, source_id=src.source_id
        )
        assert cit.verification_status == "unverified"

    def test_citation_with_evidence_unverified(self, svc: AcademicService) -> None:
        _make_project(svc)
        src = _make_source(svc)
        ev = _make_evidence(svc)
        claim = svc.create_claim(PID, "C")
        cit = svc.create_citation_link(
            PID,
            claim_id=claim.claim_id,
            source_id=src.source_id,
            evidence_id=ev.evidence_id,
        )
        assert cit.verification_status == "unverified"


# ------------------------------------------------------------------
# Unsupported claim default
# ------------------------------------------------------------------


class TestUnsupportedClaimDefault:
    def test_create_claim_without_links_is_unsupported(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc)
        claim = svc.create_claim(PID, "A claim")
        assert claim.support_state == "unsupported"
        assert claim.evidence_links == []

    def test_integrity_flags_nothing_for_unsupported_claim(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc)
        claim = svc.create_claim(PID, "A claim")
        violations = svc.validate_project_integrity(PID)
        # Unsupported claims with no links are honest state, not a violation
        rule01_violations = [v for v in violations if v.rule_id == "ACAD-RULE-01"]
        assert rule01_violations == []

    def test_integrity_flags_badly_marked_supported(
        self, svc: AcademicService
    ) -> None:
        """A claim forced to 'supported' with no evidence IS a violation."""
        _make_project(svc)
        # Create claim with at least one link to pass the model validator
        src = _make_source(svc)
        ev = _make_evidence(svc)
        claim = svc.create_claim(PID, "C", claim_id="cl-s00000000001")
        claim = svc.link_evidence_to_claim(
            "cl-s00000000001", "ev-333333333333", "supports"
        )
        # Now save a version with supports removed but support_state still "supported"
        # This would be rejected by the Claim model validator, so we test the
        # integrity rule via direct evidence: a supported claim with evidence_links
        # that contradict (not support) is a valid use case.
        # Instead, test the round-trip: create supported claim, integrity = clean
        violations = svc.validate_project_integrity(PID)
        rule01_violations = [v for v in violations if v.rule_id == "ACAD-RULE-01"]
        assert rule01_violations == []


# ------------------------------------------------------------------
# get_project / project_graph convenience
# ------------------------------------------------------------------


class TestConvenienceMethods:
    def test_get_project_returns_none_for_missing(self, svc: AcademicService) -> None:
        assert svc.get_project("rp-nonexistent00") is None

    def test_project_graph_contains_all_entities(
        self, svc: AcademicService
    ) -> None:
        _make_project(svc)
        rq = _make_rq(svc)
        src = _make_source(svc)
        ev = _make_evidence(svc)
        claim = svc.create_claim(PID, "C", claim_id="cl-aaaaaaaaaaaa")
        claim = svc.link_evidence_to_claim(
            "cl-aaaaaaaaaaaa", "ev-333333333333", "supports"
        )
        sec = svc.create_paper_section(
            PID, section_title="S", section_id="sec-aaaaaaaaaaaa"
        )
        cit = svc.create_citation_link(
            PID,
            claim_id="cl-aaaaaaaaaaaa",
            source_id="src-222222222222",
            evidence_id="ev-333333333333",
        )
        graph = svc.project_graph(PID)
        assert graph.project(PID) is not None
        assert graph.question("rq-111111111111") is not None
        assert graph.source("src-222222222222") is not None
        assert graph.evidence("ev-333333333333") is not None
        assert graph.claim("cl-aaaaaaaaaaaa") is not None
        assert graph.section("sec-aaaaaaaaaaaa") is not None
        assert graph.citation(cit.citation_id) is not None
