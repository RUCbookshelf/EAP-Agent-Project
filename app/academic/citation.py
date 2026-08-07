"""Local deterministic citation verification boundary for the Academic Writing domain.

Provides a versioned verification-rule manifest, append-only verification records (D-32),
and the only write path that can set a CitationLink's verification_status to verified.

No external APIs, no fabricated metadata, no semantic support-equivalence claims.
Verifying a citation establishes reference existence and deterministic text matching only,
never that the source semantically supports the claim.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from .entities import (
    CitationLink,
    CitationVerificationRecord,
    utc_now,
)
from .errors import AcademicDomainError
from .repositories import AcademicRepositories

# ---------------------------------------------------------------------------
# Versioned rule manifest (D-32)
# ---------------------------------------------------------------------------

VERIFICATION_RULES_VERSION = "academic-citation-verification-v0.1.0"

VERIFICATION_RULES: dict[str, str] = {
    "CIT-RULE-01": "Citation target references resolve in the project graph (claim, source, optional evidence)",
    "CIT-RULE-02": "Source identity exists and is active in the project",
    "CIT-RULE-03": "Evidence link exists and evidence source matches citation source",
    "CIT-RULE-04": "Bibliographic identifier consistency: DOI format-valid when supplied (no external lookup)",
    "CIT-RULE-05": "Direct-quote evidence content deterministically matches the source text (normalized whitespace substring)",
}

_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")


def _normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs to a single space and strip."""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Deterministic verifier
# ---------------------------------------------------------------------------


class CitationVerifier:
    """Deterministic local verifier; returns a D-32 record for one citation.

    This verifier performs only local, deterministic checks.  It never makes
    external network calls and never asserts semantic support.  A verified
    result means that deterministic reference-resolution and text-matching
    checks passed, not that the source semantically supports the claim.
    """

    def __init__(self, repositories: AcademicRepositories) -> None:
        self._repos = repositories

    def verify(
        self,
        citation_id: str,
        *,
        run_time: datetime | None = None,
    ) -> CitationVerificationRecord:
        """Run deterministic checks and return a single verification record.

        The caller (CitationVerificationService) is responsible for appending
        the record and updating the citation's verification_status.
        """
        citation = self._repos.citations.get(citation_id)
        if citation is None:
            raise AcademicDomainError(
                f"Citation with id {citation_id!r} not found",
                code="entity_not_found",
            )

        graph = self._repos.to_graph()
        source = graph.source(citation.source_id)

        now = run_time or utc_now()

        # --- verification_unavailable: no source or no source text ---
        if source is None or source.source_text is None:
            return CitationVerificationRecord(
                record_id=f"vr-{uuid.uuid4().hex[:12]}",
                citation_id=citation_id,
                rule_id=VERIFICATION_RULES_VERSION,
                rule_version=VERIFICATION_RULES_VERSION,
                source_revision_hash=None,
                matched_spans=[],
                run_time=now,
                result="verification_unavailable",
                created_by="system",
            )

        # --- deterministic checks (all applicable rules must pass) ---
        all_pass = True
        matched_spans: list[str] = []

        # CIT-RULE-01: claim exists in same project; evidence (if set) exists in same project
        claim = graph.claim(citation.claim_id)
        if claim is None or claim.project_id != citation.project_id:
            all_pass = False
        if citation.evidence_id is not None:
            evidence = graph.evidence(citation.evidence_id)
            if evidence is None or evidence.project_id != citation.project_id:
                all_pass = False

        # CIT-RULE-02: source exists (guaranteed) and is active
        if source.availability != "active":
            all_pass = False

        # CIT-RULE-03: if evidence_id set, evidence.source_id == citation.source_id
        if citation.evidence_id is not None:
            ev = graph.evidence(citation.evidence_id)
            if ev is not None and ev.source_id != citation.source_id:
                all_pass = False

        # CIT-RULE-04: DOI format check when supplied
        if source.doi is not None:
            if not _DOI_PATTERN.match(source.doi):
                all_pass = False

        # CIT-RULE-05: direct-quote evidence content in normalized source text
        if citation.evidence_id is not None:
            ev = graph.evidence(citation.evidence_id)
            if ev is not None and ev.kind == "direct_quote":
                norm_source = _normalize_whitespace(source.source_text)
                norm_content = _normalize_whitespace(ev.content)
                if norm_content in norm_source:
                    matched_spans.append(ev.locator)
                else:
                    all_pass = False

        result = "verified" if all_pass else "unverified"

        return CitationVerificationRecord(
            record_id=f"vr-{uuid.uuid4().hex[:12]}",
            citation_id=citation_id,
            rule_id=VERIFICATION_RULES_VERSION,
            rule_version=VERIFICATION_RULES_VERSION,
            source_revision_hash=source.source_text_hash,
            matched_spans=matched_spans,
            run_time=now,
            result=result,
            created_by="system",
        )


# ---------------------------------------------------------------------------
# Verification service (the ONLY path that can set verified)
# ---------------------------------------------------------------------------


class CitationVerificationService:
    """Composes verifier + repositories; the ONLY path that sets verification_status to verified.

    This service appends a verification record and updates the citation's
    verification_status atomically.  No other code path may set a citation
    to verified (ACAD-INV-02 by construction).
    """

    def __init__(self, repositories: AcademicRepositories) -> None:
        self._repos = repositories
        self._verifier = CitationVerifier(repositories)

    def verify_citation(
        self,
        citation_id: str,
        *,
        run_time: datetime | None = None,
    ) -> tuple[CitationLink, CitationVerificationRecord]:
        """Verify a citation: append record + update citation status.

        Returns the updated citation and the verification record.
        This is the ONLY path that may set verification_status to verified.
        """
        record = self._verifier.verify(citation_id, run_time=run_time)
        self._repos.records.append(record)
        citation = self._repos.citations.get(citation_id)
        if citation is None:
            raise AcademicDomainError(
                f"Citation with id {citation_id!r} not found",
                code="entity_not_found",
            )
        updated = citation.model_copy(
            update={
                "verification_status": record.result,
                "updated_at": utc_now(),
            }
        )
        self._repos.citations.save(updated)
        return updated, record

    def verification_history(
        self, citation_id: str
    ) -> list[CitationVerificationRecord]:
        """Return all verification records for a citation, sorted by run_time."""
        return self._repos.records.list_for_citation(citation_id)

    def rules_manifest(self) -> dict[str, str]:
        """Return a copy of the verification rules manifest."""
        return dict(VERIFICATION_RULES)

    def rules_version(self) -> str:
        """Return the verification rules version string."""
        return VERIFICATION_RULES_VERSION
