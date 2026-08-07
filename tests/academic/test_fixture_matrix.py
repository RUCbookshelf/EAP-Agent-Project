"""Comprehensive invariant tests exercising the full Academic foundation
through the goal-section-21 synthetic fixture.

Synthetic content only; no copyrighted source text.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.academic.citation import CitationVerificationService
from app.academic.integrity import IntegrityService
from app.academic.repositories import InMemoryRepositories

from .fixtures import build_foundation_fixture


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def repos() -> InMemoryRepositories:
    """Module-scoped fixture built once for all tests in this file."""
    return build_foundation_fixture()


@pytest.fixture(scope="module")
def graph(repos: InMemoryRepositories):
    """ProvenanceGraph snapshot from the repos fixture."""
    return repos.to_graph()


# ---------------------------------------------------------------------------
# test_every_required_fixture_item_present
# ---------------------------------------------------------------------------


def test_every_required_fixture_item_present(repos, graph):
    """Assert the full goal-section-21 fixture matrix."""
    # Projects
    projects = graph.all_projects()
    assert len(projects) == 2
    rp_ids = [p.project_id for p in projects]
    assert "rp-main" in rp_ids
    assert "rp-other" in rp_ids

    # Research questions
    questions = graph.all_questions()
    rq_ids = [q.question_id for q in questions]
    assert len(questions) >= 3
    for qid in ("rq-1", "rq-2", "rq-3"):
        assert qid in rq_ids

    # Sources
    sources = graph.all_sources()
    src_ids = [s.source_id for s in sources]
    assert len(sources) >= 3
    for sid in ("src-1", "src-2", "src-3"):
        assert sid in src_ids

    # Evidence units
    evidence = graph.all_evidence()
    ev_ids = [e.evidence_id for e in evidence]
    assert len(evidence) >= 4
    for eid in ("ev-1", "ev-2", "ev-3", "ev-4"):
        assert eid in ev_ids

    # cl-1 supported with evidence from 2 distinct sources
    cl1 = graph.claim("cl-1")
    assert cl1 is not None
    assert cl1.support_state == "supported"
    sources_for_cl1 = graph.sources_for_claim("cl-1")
    assert len(sources_for_cl1) >= 2
    src_ids_for_cl1 = [s.source_id for s in sources_for_cl1]
    assert "src-1" in src_ids_for_cl1
    assert "src-2" in src_ids_for_cl1

    # At least one source supports 2 claims (src-1 supports cl-1 and cl-3)
    claims_by_src1 = graph.claims_for_evidence("ev-1")
    claims_by_src1 += graph.claims_for_evidence("ev-2")
    cl_ids_via_src1 = {c.claim_id for c in claims_by_src1}
    assert "cl-1" in cl_ids_via_src1
    assert "cl-3" in cl_ids_via_src1

    # Nested sections: sec-2 is child of sec-1
    sec1 = graph.section("sec-1")
    sec2 = graph.section("sec-2")
    assert sec1 is not None
    assert sec2 is not None
    assert sec1.parent_section_id is None
    assert sec2.parent_section_id == "sec-1"
    assert sec1.order < sec2.order

    # Citations exist
    all_citations = graph.all_citations()
    cit_ids = [c.citation_id for c in all_citations]
    assert "cit-ok" in cit_ids
    assert "cit-broken" in cit_ids
    assert "cit-missing" in cit_ids
    assert "cit-xproj" in cit_ids


# ---------------------------------------------------------------------------
# test_provenance_queries_on_fixture
# ---------------------------------------------------------------------------


def test_provenance_queries_on_fixture(repos, graph):
    """Verify provenance query API returns correct relationships."""
    # evidence_for_claim(cl-1) == [ev-1, ev-3]
    ev_for_cl1 = graph.evidence_for_claim("cl-1")
    ev_ids = [e.evidence_id for e in ev_for_cl1]
    assert ev_ids == ["ev-1", "ev-3"]

    # sources_for_claim(cl-1) == [src-1, src-2]
    src_for_cl1 = graph.sources_for_claim("cl-1")
    src_ids = [s.source_id for s in src_for_cl1]
    assert src_ids == ["src-1", "src-2"]

    # claims_for_evidence(ev-1) == [cl-1]
    cl_for_ev1 = graph.claims_for_evidence("ev-1")
    cl_ids = [c.claim_id for c in cl_for_ev1]
    assert cl_ids == ["cl-1"]

    # orphan_evidence == [] (all evidence is referenced by at least one claim)
    orphans = graph.orphan_evidence("rp-main")
    assert orphans == []

    # unsupported_claims(rp-main) == [cl-2]  (cl-4 has links but is still unsupported)
    unsup = graph.unsupported_claims("rp-main")
    unsup_ids = [c.claim_id for c in unsup]
    # cl-2 is unsupported with no evidence links; cl-4 is unsupported but has links
    # both have support_state == "unsupported"
    assert "cl-2" in unsup_ids
    assert "cl-4" in unsup_ids


# ---------------------------------------------------------------------------
# test_integrity_on_fixture
# ---------------------------------------------------------------------------


def test_integrity_on_fixture(repos, graph):
    """IntegrityService flags expected violations and honest states are not flagged."""
    svc = IntegrityService()
    violations = svc.validate_project("rp-main", graph)

    # Collect violation (rule_id, entity_id) pairs
    flagged = {(v.rule_id, v.entity_id) for v in violations}

    # ACAD-RULE-03: cit-missing references a non-existent source
    assert ("ACAD-RULE-03", "cit-missing") in flagged

    # ACAD-RULE-06: cit-xproj has a cross-project claim reference
    assert ("ACAD-RULE-06", "cit-xproj") in flagged

    # cit-ok should NOT be flagged by R07 (it has a verified record)
    assert ("ACAD-RULE-07", "cit-ok") not in flagged

    # cit-broken: verification_unavailable is an honest state, NOT flagged by R07
    # (R07 only flags verification_status == "verified" without records)
    assert ("ACAD-RULE-07", "cit-broken") not in flagged

    # No other ACAD-RULE-03 or ACAD-RULE-06 violations beyond the two expected
    r03_ids = {e for r, e in flagged if r == "ACAD-RULE-03"}
    r06_ids = {e for r, e in flagged if r == "ACAD-RULE-06"}
    assert r03_ids == {"cit-missing"}
    assert r06_ids == {"cit-xproj"}


# ---------------------------------------------------------------------------
# test_citation_verification_on_fixture
# ---------------------------------------------------------------------------


def test_citation_verification_on_fixture(repos, graph):
    """Citation verification produces correct states and histories."""
    cv_svc = CitationVerificationService(repos)

    # cit-ok: already verified, has >= 1 verified record
    cit_ok = graph.citation("cit-ok")
    assert cit_ok.verification_status == "verified"
    ok_records = cv_svc.verification_history("cit-ok")
    assert len(ok_records) >= 1
    assert any(r.result == "verified" for r in ok_records)

    # Re-verify cit-broken -> verification_unavailable (no source text)
    updated_broken, broken_record = cv_svc.verify_citation("cit-broken")
    assert broken_record.result == "verification_unavailable"
    assert broken_record.source_revision_hash is None
    assert updated_broken.verification_status == "verification_unavailable"

    # verification_history(cit-ok) is non-empty
    history = cv_svc.verification_history("cit-ok")
    assert len(history) > 0


# ---------------------------------------------------------------------------
# test_no_l2_contamination
# ---------------------------------------------------------------------------


def test_no_l2_contamination():
    """fixtures.py contains only app.academic imports; no L2 module imports."""
    fixtures_path = Path(inspect.getfile(build_foundation_fixture))
    source = fixtures_path.read_text(encoding="utf-8")

    # Parse to AST and collect all import module names
    tree = ast.parse(source, filename=str(fixtures_path))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imported_modules.append(node.module)

    # L2-specific modules that must never appear in fixtures.py
    forbidden_prefixes = (
        "app.analysis",
        "app.diagnosis",
        "app.feedback",
        "app.llm",
        "app.models",
        "app.prompts",
        "app.analyzer",
    )

    for mod in imported_modules:
        for prefix in forbidden_prefixes:
            assert not mod.startswith(prefix), (
                f"fixtures.py imports forbidden L2 module {mod!r} "
                f"(matches prefix {prefix!r})"
            )


# ---------------------------------------------------------------------------
# test_serialization_roundtrip_spotcheck
# ---------------------------------------------------------------------------


def test_serialization_roundtrip_spotcheck(repos, graph):
    """One entity of each kind round-trips through model_dump_json / model_validate_json."""
    # ResearchProject
    proj = graph.project("rp-main")
    json_str = proj.model_dump_json()
    restored = type(proj).model_validate_json(json_str)
    assert restored.project_id == proj.project_id
    assert restored.title == proj.title

    # ResearchQuestion
    rq = graph.question("rq-1")
    json_str = rq.model_dump_json()
    restored = type(rq).model_validate_json(json_str)
    assert restored.question_id == rq.question_id
    assert restored.question_text == rq.question_text

    # Source
    src = graph.source("src-1")
    json_str = src.model_dump_json()
    restored = type(src).model_validate_json(json_str)
    assert restored.source_id == src.source_id
    assert restored.source_text == src.source_text
    assert restored.source_text_hash == src.source_text_hash

    # EvidenceUnit
    ev = graph.evidence("ev-1")
    json_str = ev.model_dump_json()
    restored = type(ev).model_validate_json(json_str)
    assert restored.evidence_id == ev.evidence_id
    assert restored.content == ev.content

    # Claim
    cl = graph.claim("cl-1")
    json_str = cl.model_dump_json()
    restored = type(cl).model_validate_json(json_str)
    assert restored.claim_id == cl.claim_id
    assert restored.support_state == cl.support_state
    assert len(restored.evidence_links) == len(cl.evidence_links)

    # PaperSection
    sec = graph.section("sec-2")
    json_str = sec.model_dump_json()
    restored = type(sec).model_validate_json(json_str)
    assert restored.section_id == sec.section_id
    assert restored.parent_section_id == sec.parent_section_id

    # CitationLink
    cit = graph.citation("cit-ok")
    json_str = cit.model_dump_json()
    restored = type(cit).model_validate_json(json_str)
    assert restored.citation_id == cit.citation_id
    assert restored.verification_status == cit.verification_status
