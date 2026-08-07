"""Tests for app.academic.citation -- deterministic citation verification boundary."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from app.academic.citation import (
    VERIFICATION_RULES,
    VERIFICATION_RULES_VERSION,
    CitationVerificationService,
    CitationVerifier,
    _normalize_whitespace,
)
from app.academic.entities import (
    CitationLink,
    CitationVerificationRecord,
    Claim,
    ClaimEvidenceLink,
    EvidenceUnit,
    ResearchProject,
    Source,
    utc_now,
)
from app.academic.errors import AcademicDomainError
from app.academic.integrity import IntegrityService
from app.academic.repositories import InMemoryRepositories

_T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
_T1 = datetime(2026, 1, 2, tzinfo=timezone.utc)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


SOURCE_TEXT = "The quick brown fox jumps over the lazy dog. This is a test passage."
SOURCE_TEXT_HASH = _sha256(SOURCE_TEXT)
QUOTE_CONTENT = "The quick brown fox jumps over the lazy dog."
QUOTE_LOCATOR = "p.5"
DOI_VALID = "10.1234/abc.def"
DOI_INVALID = "not-a-doi"


def _make_repos() -> InMemoryRepositories:
    return InMemoryRepositories()


def _create_project(repos: InMemoryRepositories, pid: str = "rp-1") -> ResearchProject:
    rp = ResearchProject(project_id=pid, title="Test Project")
    repos.projects.create(rp)
    return rp


def _create_source(
    repos: InMemoryRepositories,
    sid: str = "src-1",
    pid: str = "rp-1",
    source_text: str | None = SOURCE_TEXT,
    doi: str | None = DOI_VALID,
    availability: str = "active",
) -> Source:
    kwargs: dict = {
        "source_id": sid,
        "project_id": pid,
        "title": f"Source {sid}",
        "origin": "learner_entered",
        "availability": availability,
        "doi": doi,
    }
    if source_text is not None:
        kwargs["source_text"] = source_text
        kwargs["source_text_hash"] = _sha256(source_text)
    src = Source(**kwargs)
    repos.sources.create(src)
    return src


def _create_claim(
    repos: InMemoryRepositories,
    cid: str = "cl-1",
    pid: str = "rp-1",
    evidence_id: str | None = "ev-1",
) -> Claim:
    links = []
    if evidence_id is not None:
        links.append(ClaimEvidenceLink(evidence_id=evidence_id, link_type="supports"))
    cl = Claim.model_construct(
        claim_id=cid,
        project_id=pid,
        claim_text="Test claim text",
        support_state="supported" if links else "unsupported",
        rq_ids=[],
        section_ids=[],
        evidence_links=links,
    )
    repos.claims.create(cl)
    return cl


def _create_evidence(
    repos: InMemoryRepositories,
    eid: str = "ev-1",
    pid: str = "rp-1",
    sid: str = "src-1",
    kind: str = "direct_quote",
    content: str = QUOTE_CONTENT,
    locator: str = QUOTE_LOCATOR,
) -> EvidenceUnit:
    ev = EvidenceUnit(
        evidence_id=eid,
        project_id=pid,
        source_id=sid,
        source_version=1,
        kind=kind,
        locator=locator,
        content=content,
    )
    repos.evidence.create(ev)
    return ev


def _create_citation(
    repos: InMemoryRepositories,
    cit_id: str = "cit-1",
    pid: str = "rp-1",
    claim_id: str = "cl-1",
    source_id: str = "src-1",
    evidence_id: str | None = "ev-1",
) -> CitationLink:
    cit = CitationLink(
        citation_id=cit_id,
        project_id=pid,
        claim_id=claim_id,
        source_id=source_id,
        evidence_id=evidence_id,
    )
    repos.citations.create(cit)
    return cit


def _setup_full_verified(repos: InMemoryRepositories):
    _create_project(repos)
    src = _create_source(repos)
    _create_evidence(repos)
    _create_claim(repos)
    cit = _create_citation(repos)
    return cit, src


class TestManifestConstants:
    def test_rules_version_value(self) -> None:
        assert VERIFICATION_RULES_VERSION == "academic-citation-verification-v0.1.0"

    def test_rules_manifest_has_five_entries(self) -> None:
        assert len(VERIFICATION_RULES) == 5
        expected_ids = {f"CIT-RULE-0{i}" for i in range(1, 6)}
        assert set(VERIFICATION_RULES.keys()) == expected_ids

    def test_rules_manifest_returns_copy(self) -> None:
        svc = CitationVerificationService(_make_repos())
        manifest = svc.rules_manifest()
        manifest["FAKE"] = "fake"
        assert "FAKE" not in VERIFICATION_RULES

    def test_rules_version_matches_constant(self) -> None:
        svc = CitationVerificationService(_make_repos())
        assert svc.rules_version() == VERIFICATION_RULES_VERSION


class TestVerifiedPath:
    def test_verified_all_checks_pass(self) -> None:
        repos = _make_repos()
        cit, src = _setup_full_verified(repos)
        svc = CitationVerificationService(repos)
        updated_cit, record = svc.verify_citation(cit.citation_id, run_time=_T0)
        assert record.result == "verified"
        assert updated_cit.verification_status == "verified"
        assert record.source_revision_hash == src.source_text_hash
        assert record.matched_spans == [QUOTE_LOCATOR]
        assert record.created_by == "system"
        assert record.run_time == _T0

    def test_verified_has_hash(self) -> None:
        repos = _make_repos()
        _setup_full_verified(repos)
        svc = CitationVerificationService(repos)
        _, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.source_revision_hash is not None

    def test_verified_acad_inv_02_satisfied(self) -> None:
        repos = _make_repos()
        _setup_full_verified(repos)
        svc = CitationVerificationService(repos)
        updated_cit, _ = svc.verify_citation("cit-1", run_time=_T0)
        assert updated_cit.verification_status == "verified"
        history = svc.verification_history("cit-1")
        assert any(r.result == "verified" for r in history)

    def test_verified_r07_not_flagged(self) -> None:
        repos = _make_repos()
        _setup_full_verified(repos)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T0)
        graph = repos.to_graph()
        violations = IntegrityService().validate_project("rp-1", graph)
        r07 = [v for v in violations if v.rule_id == "ACAD-RULE-07"]
        assert r07 == []

    def test_verified_status_persisted_on_citation(self) -> None:
        repos = _make_repos()
        _setup_full_verified(repos)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T0)
        saved = repos.citations.get("cit-1")
        assert saved is not None
        assert saved.verification_status == "verified"


class TestUnverifiedPaths:
    def test_unverified_quote_miss(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos)
        _create_evidence(repos, content="This quote does not exist in the source.")
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        updated_cit, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "unverified"
        assert updated_cit.verification_status == "unverified"
        assert record.matched_spans == []

    def test_unverified_evidence_source_mismatch(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos, sid="src-1")
        _create_source(repos, sid="src-2")
        _create_evidence(repos, eid="ev-1", sid="src-2")
        _create_claim(repos, evidence_id="ev-1")
        _create_citation(repos, source_id="src-1", evidence_id="ev-1")
        svc = CitationVerificationService(repos)
        updated_cit, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "unverified"
        assert updated_cit.verification_status == "unverified"

    def test_unverified_doi_invalid(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos, doi=DOI_INVALID)
        _create_evidence(repos)
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        updated_cit, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "unverified"
        assert updated_cit.verification_status == "unverified"

    def test_unverified_missing_claim(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos)
        _create_evidence(repos)
        _create_citation(repos, claim_id="cl-missing")
        svc = CitationVerificationService(repos)
        updated_cit, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "unverified"
        assert updated_cit.verification_status == "unverified"

    def test_doi_none_passes_rule_04(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos, doi=None)
        _create_evidence(repos)
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        _, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "verified"

    def test_no_evidence_passes_rules_03_and_05(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos)
        _create_claim(repos, evidence_id=None)
        _create_citation(repos, evidence_id=None)
        svc = CitationVerificationService(repos)
        _, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "verified"
        assert record.matched_spans == []

    def test_paraphrase_evidence_passes_rule_05(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos)
        _create_evidence(repos, kind="learner_paraphrase", content="some paraphrase")
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        _, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "verified"


class TestVerificationUnavailable:
    def test_no_source_text(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos, source_text=None)
        _create_evidence(repos)
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        updated_cit, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "verification_unavailable"
        assert record.source_revision_hash is None
        assert updated_cit.verification_status == "verification_unavailable"
        assert record.matched_spans == []

    def test_source_missing(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_evidence(repos)
        _create_claim(repos)
        _create_citation(repos, source_id="src-missing")
        svc = CitationVerificationService(repos)
        updated_cit, record = svc.verify_citation("cit-1", run_time=_T0)
        assert record.result == "verification_unavailable"
        assert record.source_revision_hash is None
        assert updated_cit.verification_status == "verification_unavailable"

    def test_r07_not_flagged_for_honest_unavailable(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos, source_text=None)
        _create_evidence(repos)
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T0)
        graph = repos.to_graph()
        violations = IntegrityService().validate_project("rp-1", graph)
        r07 = [v for v in violations if v.rule_id == "ACAD-RULE-07"]
        assert r07 == []

    def test_verification_unavailable_cannot_be_verified_with_hash(self) -> None:
        with pytest.raises(Exception):
            CitationVerificationRecord(
                record_id="vr-unavail",
                citation_id="cit-1",
                rule_id="test",
                rule_version="1.0",
                source_revision_hash="a" * 64,
                run_time=_T0,
                result="verification_unavailable",
            )


class TestVerificationHistory:
    def test_history_grows(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos)
        _create_evidence(repos, content="not in source")
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T0)
        history1 = svc.verification_history("cit-1")
        assert len(history1) == 1
        assert history1[0].result == "unverified"
        fixed_text = SOURCE_TEXT + " not in source"
        repos.sources.save(
            repos.sources.get("src-1").new_version(
                source_text=fixed_text,
                source_text_hash=_sha256(fixed_text),
            )
        )
        svc.verify_citation("cit-1", run_time=_T1)
        history2 = svc.verification_history("cit-1")
        assert len(history2) == 2
        assert history2[0].result == "unverified"
        assert history2[1].result == "verified"

    def test_records_frozen(self) -> None:
        repos = _make_repos()
        _setup_full_verified(repos)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T0)
        history = svc.verification_history("cit-1")
        record = history[0]
        with pytest.raises(Exception):
            record.result = "unverified"

    def test_records_sorted_by_run_time(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos, source_text=None)
        _create_evidence(repos)
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T1)
        svc.verify_citation("cit-1", run_time=_T0)
        history = svc.verification_history("cit-1")
        assert len(history) == 2
        assert history[0].run_time <= history[1].run_time

    def test_record_ids_unique(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos, source_text=None)
        _create_evidence(repos)
        _create_claim(repos)
        _create_citation(repos)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T0)
        svc.verify_citation("cit-1", run_time=_T1)
        history = svc.verification_history("cit-1")
        ids = [r.record_id for r in history]
        assert len(ids) == len(set(ids))


class TestAcadInv02CrossLayer:
    def test_tampered_verified_without_record_flagged(self) -> None:
        repos = _make_repos()
        _create_project(repos)
        _create_source(repos)
        _create_evidence(repos)
        _create_claim(repos)
        _create_citation(repos)
        cit = repos.citations.get("cit-1")
        tampered = cit.model_copy(update={"verification_status": "verified", "updated_at": utc_now()})
        repos.citations.save(tampered)
        graph = repos.to_graph()
        violations = IntegrityService().validate_project("rp-1", graph)
        r07 = [v for v in violations if v.rule_id == "ACAD-RULE-07"]
        assert len(r07) == 1
        assert r07[0].entity_id == "cit-1"
        assert "ACAD-INV-02" in r07[0].detail

    def test_service_path_not_flagged(self) -> None:
        repos = _make_repos()
        _setup_full_verified(repos)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T0)
        graph = repos.to_graph()
        violations = IntegrityService().validate_project("rp-1", graph)
        r07 = [v for v in violations if v.rule_id == "ACAD-RULE-07"]
        assert r07 == []

    def test_tampered_then_service_cleans(self) -> None:
        repos = _make_repos()
        _setup_full_verified(repos)
        cit = repos.citations.get("cit-1")
        tampered = cit.model_copy(update={"verification_status": "verified", "updated_at": utc_now()})
        repos.citations.save(tampered)
        graph = repos.to_graph()
        violations = IntegrityService().validate_project("rp-1", graph)
        assert any(v.rule_id == "ACAD-RULE-07" for v in violations)
        svc = CitationVerificationService(repos)
        svc.verify_citation("cit-1", run_time=_T0)
        graph = repos.to_graph()
        violations = IntegrityService().validate_project("rp-1", graph)
        assert not any(v.rule_id == "ACAD-RULE-07" for v in violations)


class TestErrorPaths:
    def test_missing_citation_raises(self) -> None:
        repos = _make_repos()
        svc = CitationVerificationService(repos)
        with pytest.raises(AcademicDomainError) as exc_info:
            svc.verify_citation("cit-missing")
        assert exc_info.value.code == "entity_not_found"

    def test_verifier_missing_citation_raises(self) -> None:
        repos = _make_repos()
        verifier = CitationVerifier(repos)
        with pytest.raises(AcademicDomainError) as exc_info:
            verifier.verify("cit-missing")
        assert exc_info.value.code == "entity_not_found"


class TestNormalizeWhitespace:
    def test_collapse_spaces(self) -> None:
        assert _normalize_whitespace("  hello   world  ") == "hello world"

    def test_tabs_newlines(self) -> None:
        assert _normalize_whitespace("hello\t\n  world") == "hello world"

    def test_empty(self) -> None:
        assert _normalize_whitespace("") == ""

    def test_case_sensitive(self) -> None:
        assert _normalize_whitespace("Hello") != _normalize_whitespace("hello")


class TestDoiFormat:
    def test_valid_doi_pattern(self) -> None:
        from app.academic.citation import _DOI_PATTERN
        assert _DOI_PATTERN.match("10.1234/abc")
        assert _DOI_PATTERN.match("10.1000/182")
        assert _DOI_PATTERN.match("10.5555/abc.def.ghi")

    def test_invalid_doi_patterns(self) -> None:
        from app.academic.citation import _DOI_PATTERN
        assert not _DOI_PATTERN.match("doi:10.1234/abc")
        assert not _DOI_PATTERN.match("10.1/abc")
        assert not _DOI_PATTERN.match("not-a-doi")
        assert not _DOI_PATTERN.match("10.1234/")


class TestNoExternalImports:
    def test_no_network_imports(self) -> None:
        import app.academic.citation as mod
        source = open(mod.__file__).read()
        for forbidden in ("import requests", "import httpx", "import urllib", "from requests", "from httpx", "from urllib"):
            assert forbidden not in source, f"Forbidden import: {forbidden}"

    def test_no_semantic_claims_in_api(self) -> None:
        import app.academic.citation as mod
        source = open(mod.__file__).read()
        assert "semantic" in source.lower()
