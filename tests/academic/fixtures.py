"""Synthetic foundation fixtures for the Academic Writing domain.

Covers the full goal-section-21 matrix: one project, multiple RQs/sources,
evidence units, supported/unsupported/partially-supported claims, nested
sections, valid/broken/cross-project citations, and honest verification states.

Synthetic content only; no copyrighted source text.
"""

from __future__ import annotations

import hashlib

from app.academic.citation import CitationVerificationService
from app.academic.repositories import InMemoryRepositories
from app.academic.services import AcademicService


def _sha256_hex(text: str) -> str:
    """Compute SHA-256 hex digest for source_text_hash fields."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_foundation_fixture() -> InMemoryRepositories:
    """Build and return InMemoryRepositories covering the full goal-section-21 matrix.

    Returns:
        InMemoryRepositories populated with synthetic entities covering every
        goal-section-21 item. Callers should use ``repos.to_graph()`` to build
        a ProvenanceGraph for queries and integrity checks.
    """
    repos = InMemoryRepositories()
    svc = AcademicService(repos)

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------
    rp_main = svc.create_research_project(
        "Foundation Fixture Project",
        project_id="rp-main",
    )

    # ------------------------------------------------------------------
    # Research Questions (3)
    # ------------------------------------------------------------------
    rq_1 = svc.add_research_question(
        "rp-main",
        "How does metacognitive strategy instruction affect L2 writing quality?",
        question_id="rq-1",
    )
    rq_2 = svc.add_research_question(
        "rp-main",
        "What peer feedback mechanisms support argumentative writing development?",
        question_id="rq-2",
    )
    rq_3 = svc.add_research_question(
        "rp-main",
        "How do goal-setting practices influence revision behaviour?",
        question_id="rq-3",
    )

    # ------------------------------------------------------------------
    # Sources (3)
    # ------------------------------------------------------------------
    # src-1: learner_entered, source_text present, valid DOI
    src_1_text = (
        "Metacognitive strategy instruction significantly improved "
        "argumentative writing scores in the treatment group."
    )
    src_1 = svc.register_source(
        "rp-main",
        title="Metacognition and L2 Writing",
        origin="learner_entered",
        authors="Synthetic Author A",
        year=2023,
        publication="Journal of Synthetic Research",
        doi="10.1234/example.doi",
        source_text=src_1_text,
        source_id="src-1",
    )

    # src-2: imported_file, source_text present
    src_2_text = (
        "Peer feedback workshops led to measurable gains in "
        "coherence and cohesion for intermediate learners."
    )
    src_2 = svc.register_source(
        "rp-main",
        title="Peer Feedback in L2 Contexts",
        origin="imported_file",
        authors="Synthetic Author B",
        year=2022,
        publication="Synthetic Review of Education",
        source_text=src_2_text,
        source_id="src-2",
    )

    # src-3: learner_entered, NO source_text (honest unavailable)
    src_3 = svc.register_source(
        "rp-main",
        title="Incomplete Source Record",
        origin="learner_entered",
        authors="Synthetic Author C",
        year=2021,
        source_id="src-3",
    )

    # ------------------------------------------------------------------
    # Evidence Units (4)
    # ------------------------------------------------------------------
    # ev-1: direct_quote from src-1, content matches src-1 text exactly
    ev_1 = svc.capture_evidence_unit(
        "rp-main",
        source_id="src-1",
        kind="direct_quote",
        locator="p.1",
        content=src_1_text,
        rq_ids=["rq-1"],
        evidence_id="ev-1",
    )

    # ev-2: learner_paraphrase from src-1
    ev_2 = svc.capture_evidence_unit(
        "rp-main",
        source_id="src-1",
        kind="learner_paraphrase",
        locator="p.2",
        content="Students improved their writing when taught metacognitive strategies.",
        rq_ids=["rq-2"],
        evidence_id="ev-2",
    )

    # ev-3: direct_quote from src-2
    ev_3 = svc.capture_evidence_unit(
        "rp-main",
        source_id="src-2",
        kind="direct_quote",
        locator="p.3",
        content=src_2_text,
        rq_ids=["rq-2"],
        evidence_id="ev-3",
    )

    # ev-4: direct_quote from src-3 (no source text available)
    ev_4 = svc.capture_evidence_unit(
        "rp-main",
        source_id="src-3",
        kind="direct_quote",
        locator="p.4",
        content="Placeholder content for evidence from an unavailable source.",
        rq_ids=["rq-3"],
        evidence_id="ev-4",
    )

    # ------------------------------------------------------------------
    # Sections (2, nested: sec-2 child of sec-1)
    # ------------------------------------------------------------------
    sec_1 = svc.create_paper_section(
        "rp-main",
        section_title="Literature Review",
        order=0,
        section_id="sec-1",
    )
    sec_2 = svc.create_paper_section(
        "rp-main",
        section_title="Findings Discussion",
        order=1,
        parent_section_id="sec-1",
        section_id="sec-2",
    )

    # ------------------------------------------------------------------
    # Claims (4)
    # ------------------------------------------------------------------
    # cl-1: SUPPORTED via ev-1 (src-1) + ev-3 (src-2) -> multiple sources
    cl_1 = svc.create_claim(
        "rp-main",
        "Strategy instruction and peer feedback together improve L2 writing.",
        support_state="unsupported",
        rq_ids=["rq-1", "rq-2"],
        section_ids=["sec-1"],
        claim_id="cl-1",
    )
    cl_1 = svc.link_evidence_to_claim("cl-1", "ev-1", "supports")
    cl_1 = svc.link_evidence_to_claim("cl-1", "ev-3", "supports")
    cl_1 = svc.set_claim_support_state("cl-1", "supported")

    # cl-2: unsupported, no evidence links, attached to sec-2
    cl_2 = svc.create_claim(
        "rp-main",
        "Self-regulation has no measurable impact on writing outcomes.",
        support_state="unsupported",
        rq_ids=["rq-3"],
        section_ids=["sec-2"],
        claim_id="cl-2",
    )

    # cl-3: partially_supported via ev-2 (contextualizes)
    cl_3 = svc.create_claim(
        "rp-main",
        "Metacognitive awareness correlates with revision frequency.",
        support_state="unsupported",
        rq_ids=["rq-1"],
        claim_id="cl-3",
    )
    cl_3 = svc.link_evidence_to_claim("cl-3", "ev-2", "contextualizes")
    cl_3 = svc.set_claim_support_state("cl-3", "partially_supported")

    # cl-4: unsupported, linked to ev-4 (src-3 supports another claim)
    cl_4 = svc.create_claim(
        "rp-main",
        "Goal-setting is the primary driver of revision quality.",
        support_state="unsupported",
        rq_ids=["rq-3"],
        claim_id="cl-4",
    )
    cl_4 = svc.link_evidence_to_claim("cl-4", "ev-4", "supports")

    # ------------------------------------------------------------------
    # Citations (3)
    # ------------------------------------------------------------------
    # cit-ok: valid citation, will be verified (cl-1 -> src-1, evidence ev-1)
    cit_ok = svc.create_citation_link(
        "rp-main",
        claim_id="cl-1",
        source_id="src-1",
        evidence_id="ev-1",
        passage_span="p.1",
        citation_id="cit-ok",
    )

    # cit-broken: src-3 has no source_text -> verification_unavailable (honest state)
    cit_broken = svc.create_citation_link(
        "rp-main",
        claim_id="cl-2",
        source_id="src-3",
        evidence_id="ev-4",
        passage_span="p.4",
        citation_id="cit-broken",
    )

    # Verify cit-ok through the service (sets verification_status = verified)
    cv_service = CitationVerificationService(repos)
    cv_service.verify_citation("cit-ok")

    # Verify cit-broken (results in verification_unavailable, honest state)
    cv_service.verify_citation("cit-broken")

    # cit-missing: references a non-existent source (ACAD-RULE-03)
    # Created via repos.citations.create directly to bypass service guards
    from app.academic.entities import CitationLink

    cit_missing = CitationLink(
        citation_id="cit-missing",
        project_id="rp-main",
        claim_id="cl-1",
        source_id="src-missing",
        evidence_id=None,
        verification_status="unverified",
    )
    repos.citations.create(cit_missing)

    # ------------------------------------------------------------------
    # Cross-project invalid citation (ACAD-RULE-06)
    # ------------------------------------------------------------------
    # Second project with one claim; cit-xproj in rp-main references cl-other
    rp_other = svc.create_research_project(
        "Secondary Fixture Project",
        project_id="rp-other",
    )
    rq_other = svc.add_research_question(
        "rp-other",
        "What are the effects of collaborative writing?",
        question_id="rq-4",
    )
    cl_other = svc.create_claim(
        "rp-other",
        "Collaborative writing enhances genre awareness.",
        support_state="unsupported",
        rq_ids=["rq-4"],
        claim_id="cl-other",
    )

    # cit-xproj: in rp-main, claim belongs to rp-other (cross-project reference)
    cit_xproj = CitationLink(
        citation_id="cit-xproj",
        project_id="rp-main",
        claim_id="cl-other",
        source_id="src-1",
        evidence_id=None,
        verification_status="unverified",
    )
    repos.citations.create(cit_xproj)

    return repos

