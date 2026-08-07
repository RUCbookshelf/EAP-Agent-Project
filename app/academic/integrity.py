"""Deterministic academic-integrity guardrails for the Academic Writing domain.

Enforces structural invariants over a ProvenanceGraph snapshot.
No LLM judgment; no automated plagiarism detection.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .provenance import ProvenanceGraph

# ---------------------------------------------------------------------------
# Rules registry
# ---------------------------------------------------------------------------

INTEGRITY_RULES_VERSION = "academic-integrity-rules-v0.1.0"

INTEGRITY_RULES: dict[str, str] = {
    "ACAD-RULE-01": "Claim marked supported/partially_supported has zero supporting evidence links",
    "ACAD-RULE-02": "EvidenceUnit references a missing or cross-project Source",
    "ACAD-RULE-03": "CitationLink references a missing or cross-project Source",
    "ACAD-RULE-04": "CitationLink references an unrelated EvidenceUnit (missing, cross-project, or evidence source != citation source)",
    "ACAD-RULE-05": "Removed Source is still referenced by EvidenceUnit or CitationLink",
    "ACAD-RULE-06": "Cross-project reference detected (rq/section/parent-section/claim/evidence linkage)",
    "ACAD-RULE-07": "CitationLink marked verified without an append-only verification record with result verified (ACAD-INV-02)",
}


# ---------------------------------------------------------------------------
# Violation model
# ---------------------------------------------------------------------------


class IntegrityViolation(BaseModel):
    """A single deterministic integrity violation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    entity_type: str  # e.g. "claim", "evidence_unit", "citation_link", "source"
    entity_id: str
    project_id: str
    severity: Literal["error", "warning"] = "error"
    detail: str


# ---------------------------------------------------------------------------
# Integrity service
# ---------------------------------------------------------------------------


class IntegrityService:
    """Deterministic integrity validation over a ProvenanceGraph snapshot."""

    @staticmethod
    def rules() -> dict[str, str]:
        """Return a copy of the rules registry."""
        return dict(INTEGRITY_RULES)

    @staticmethod
    def rules_version() -> str:
        """Return the rules version string."""
        return INTEGRITY_RULES_VERSION

    def validate_project(
        self, project_id: str, graph: ProvenanceGraph
    ) -> list[IntegrityViolation]:
        """Scan a single project snapshot and return sorted violations.

        Violations are sorted by (rule_id, entity_id) for determinism.
        At most one violation per (rule_id, entity_id) pair.
        """
        details: dict[tuple[str, str, str], list[str]] = {}

        def _record(
            rule_id: str,
            entity_type: str,
            entity_id: str,
            detail: str,
        ) -> None:
            key = (rule_id, entity_type, entity_id)
            details.setdefault(key, []).append(detail)

        # Collect project entities
        project_claims = [
            c for c in graph.all_claims() if c.project_id == project_id
        ]
        project_evidence = [
            e for e in graph.all_evidence() if e.project_id == project_id
        ]
        project_citations = [
            c for c in graph.all_citations() if c.project_id == project_id
        ]
        project_sources = [
            s for s in graph.all_sources() if s.project_id == project_id
        ]

        # --- R01: supported/partially_supported claim with zero evidence links ---
        for claim in project_claims:
            if claim.support_state in ("supported", "partially_supported"):
                if len(claim.evidence_links) == 0:
                    _record(
                        "ACAD-RULE-01",
                        "claim",
                        claim.claim_id,
                        f"support_state={claim.support_state} but evidence_links is empty",
                    )

        # --- R02: EvidenceUnit references missing or cross-project Source ---
        for ev in project_evidence:
            src = graph.source(ev.source_id)
            if src is None:
                _record(
                    "ACAD-RULE-02",
                    "evidence_unit",
                    ev.evidence_id,
                    f"source_id={ev.source_id!r} not found in graph",
                )
            elif src.project_id != ev.project_id:
                _record(
                    "ACAD-RULE-02",
                    "evidence_unit",
                    ev.evidence_id,
                    f"source_id={ev.source_id!r} belongs to project {src.project_id!r}, expected {ev.project_id!r}",
                )

        # --- R03: CitationLink references missing or cross-project Source ---
        for cit in project_citations:
            src = graph.source(cit.source_id)
            if src is None:
                _record(
                    "ACAD-RULE-03",
                    "citation_link",
                    cit.citation_id,
                    f"source_id={cit.source_id!r} not found in graph",
                )
            elif src.project_id != cit.project_id:
                _record(
                    "ACAD-RULE-03",
                    "citation_link",
                    cit.citation_id,
                    f"source_id={cit.source_id!r} belongs to project {src.project_id!r}, expected {cit.project_id!r}",
                )

        # --- R04: CitationLink references unrelated EvidenceUnit ---
        for cit in project_citations:
            if cit.evidence_id is None:
                continue
            ev = graph.evidence(cit.evidence_id)
            if ev is None:
                _record(
                    "ACAD-RULE-04",
                    "citation_link",
                    cit.citation_id,
                    f"evidence_id={cit.evidence_id!r} not found in graph",
                )
            elif ev.project_id != cit.project_id:
                _record(
                    "ACAD-RULE-04",
                    "citation_link",
                    cit.citation_id,
                    f"evidence_id={cit.evidence_id!r} belongs to project {ev.project_id!r}, expected {cit.project_id!r}",
                )
            elif ev.source_id != cit.source_id:
                _record(
                    "ACAD-RULE-04",
                    "citation_link",
                    cit.citation_id,
                    f"evidence source_id={ev.source_id!r} != citation source_id={cit.source_id!r}",
                )

        # --- R05: Removed Source still referenced ---
        ev_sources: set[str] = set()
        for ev in project_evidence:
            ev_sources.add(ev.source_id)
        cit_sources: set[str] = set()
        for cit in project_citations:
            cit_sources.add(cit.source_id)
        referenced_sources = ev_sources | cit_sources

        for src in project_sources:
            if src.availability == "removed" and src.source_id in referenced_sources:
                _record(
                    "ACAD-RULE-05",
                    "source",
                    src.source_id,
                    f"removed source still referenced by evidence or citation",
                )

        # --- R06: Cross-project references within this project ---
        for ev in project_evidence:
            for rq_id in ev.rq_ids:
                rq = graph.question(rq_id)
                if rq is not None and rq.project_id != ev.project_id:
                    _record(
                        "ACAD-RULE-06",
                        "evidence_unit",
                        ev.evidence_id,
                        f"rq_id={rq_id!r} belongs to project {rq.project_id!r}, expected {ev.project_id!r}",
                    )

        for claim in project_claims:
            for rq_id in claim.rq_ids:
                rq = graph.question(rq_id)
                if rq is not None and rq.project_id != claim.project_id:
                    _record(
                        "ACAD-RULE-06",
                        "claim",
                        claim.claim_id,
                        f"rq_id={rq_id!r} belongs to project {rq.project_id!r}, expected {claim.project_id!r}",
                    )
            for sec_id in claim.section_ids:
                sec = graph.section(sec_id)
                if sec is not None and sec.project_id != claim.project_id:
                    _record(
                        "ACAD-RULE-06",
                        "claim",
                        claim.claim_id,
                        f"section_id={sec_id!r} belongs to project {sec.project_id!r}, expected {claim.project_id!r}",
                    )
            for link in claim.evidence_links:
                ev = graph.evidence(link.evidence_id)
                if ev is None:
                    _record(
                        "ACAD-RULE-06",
                        "claim",
                        claim.claim_id,
                        f"evidence_id={link.evidence_id!r} not found in graph",
                    )
                elif ev.project_id != claim.project_id:
                    _record(
                        "ACAD-RULE-06",
                        "claim",
                        claim.claim_id,
                        f"evidence_id={link.evidence_id!r} belongs to project {ev.project_id!r}, expected {claim.project_id!r}",
                    )

        for sec in [s for s in graph.all_sections() if s.project_id == project_id]:
            for rq_id in sec.rq_ids:
                rq = graph.question(rq_id)
                if rq is not None and rq.project_id != sec.project_id:
                    _record(
                        "ACAD-RULE-06",
                        "paper_section",
                        sec.section_id,
                        f"rq_id={rq_id!r} belongs to project {rq.project_id!r}, expected {sec.project_id!r}",
                    )
            if sec.parent_section_id is not None:
                parent = graph.section(sec.parent_section_id)
                if parent is not None and parent.project_id != sec.project_id:
                    _record(
                        "ACAD-RULE-06",
                        "paper_section",
                        sec.section_id,
                        f"parent_section_id={sec.parent_section_id!r} belongs to project {parent.project_id!r}, expected {sec.project_id!r}",
                    )

        for cit in project_citations:
            claim = graph.claim(cit.claim_id)
            if claim is not None and claim.project_id != cit.project_id:
                _record(
                    "ACAD-RULE-06",
                    "citation_link",
                    cit.citation_id,
                    f"claim_id={cit.claim_id!r} belongs to project {claim.project_id!r}, expected {cit.project_id!r}",
                )

        # --- R07: verified citation without verification record (ACAD-INV-02) ---
        for cit in project_citations:
            if cit.verification_status == "verified":
                records = graph.records_for_citation(cit.citation_id)
                has_verified = any(r.result == "verified" for r in records)
                if not has_verified:
                    _record(
                        "ACAD-RULE-07",
                        "citation_link",
                        cit.citation_id,
                        "verification_status=verified but no append-only record with result=verified (ACAD-INV-02)",
                    )

        violations = [
            IntegrityViolation(
                rule_id=rule_id,
                entity_type=entity_type,
                entity_id=entity_id,
                project_id=project_id,
                detail="; ".join(sorted(set(detail_list))),
            )
            for (rule_id, entity_type, entity_id), detail_list in details.items()
        ]
        violations.sort(key=lambda v: (v.rule_id, v.entity_id))
        return violations

    def validate_all(
        self, graph: ProvenanceGraph
    ) -> dict[str, list[IntegrityViolation]]:
        """Validate every project in the graph. Returns project_id -> violations."""
        result: dict[str, list[IntegrityViolation]] = {}
        for proj in graph.all_projects():
            violations = self.validate_project(proj.project_id, graph)
            result[proj.project_id] = violations
        return result