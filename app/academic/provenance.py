"""In-memory read-only provenance graph for Academic domain entities."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .entities import (
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


def _checked(items: Iterable, cls: type, label: str) -> list:
    """Validate constructor input types deterministically (TypeError, not AttributeError)."""
    out = list(items)
    for item in out:
        if not isinstance(item, cls):
            raise TypeError(f"{label} must contain only {cls.__name__} instances")
    return out


class ProvenanceGraph:
    """In-memory read-only traversal over a snapshot of Academic entities."""

    def __init__(
        self,
        *,
        projects: Iterable[ResearchProject] = (),
        questions: Iterable[ResearchQuestion] = (),
        sources: Iterable[Source] = (),
        evidence_units: Iterable[EvidenceUnit] = (),
        claims: Iterable[Claim] = (),
        sections: Iterable[PaperSection] = (),
        citations: Iterable[CitationLink] = (),
        records: Iterable[CitationVerificationRecord] = (),
    ) -> None:
        # Accept duplicates defensively: last-wins per id (documented).
        self._projects: dict[str, ResearchProject] = {}
        self._questions: dict[str, ResearchQuestion] = {}
        self._sources: dict[str, Source] = {}
        self._evidence: dict[str, EvidenceUnit] = {}
        self._claims: dict[str, Claim] = {}
        self._sections: dict[str, PaperSection] = {}
        self._citations: dict[str, CitationLink] = {}
        self._records: dict[str, list[CitationVerificationRecord]] = defaultdict(list)

        for p in _checked(projects, ResearchProject, "projects"):
            self._projects[p.project_id] = p
        for q in _checked(questions, ResearchQuestion, "questions"):
            self._questions[q.question_id] = q
        for s in _checked(sources, Source, "sources"):
            self._sources[s.source_id] = s
        for ev in _checked(evidence_units, EvidenceUnit, "evidence_units"):
            self._evidence[ev.evidence_id] = ev
        for c in _checked(claims, Claim, "claims"):
            self._claims[c.claim_id] = c
        for sec in _checked(sections, PaperSection, "sections"):
            self._sections[sec.section_id] = sec
        for cit in _checked(citations, CitationLink, "citations"):
            self._citations[cit.citation_id] = cit
        for rec in _checked(records, CitationVerificationRecord, "records"):
            self._records[rec.citation_id].append(rec)

        # Sort records per citation by run_time then record_id for determinism.
        for cid in self._records:
            self._records[cid].sort(key=lambda r: (r.run_time, r.record_id))

        # --- Reverse indexes ---
        # evidence_id -> set of claim_ids that reference it
        self._ev_to_claims: dict[str, set[str]] = defaultdict(set)
        for cl in self._claims.values():
            for link in cl.evidence_links:
                self._ev_to_claims[link.evidence_id].add(cl.claim_id)

        # rq_id -> set of claim_ids
        self._rq_to_claims: dict[str, set[str]] = defaultdict(set)
        for cl in self._claims.values():
            for rq_id in cl.rq_ids:
                self._rq_to_claims[rq_id].add(cl.claim_id)

        # section_id -> set of claim_ids
        self._sec_to_claims: dict[str, set[str]] = defaultdict(set)
        for cl in self._claims.values():
            for sec_id in cl.section_ids:
                self._sec_to_claims[sec_id].add(cl.claim_id)

        # claim_id -> set of citation_ids
        self._cl_to_citations: dict[str, set[str]] = defaultdict(set)
        for cit in self._citations.values():
            self._cl_to_citations[cit.claim_id].add(cit.citation_id)

        # source_id -> set of citation_ids
        self._src_to_citations: dict[str, set[str]] = defaultdict(set)
        for cit in self._citations.values():
            self._src_to_citations[cit.source_id].add(cit.citation_id)

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def evidence_for_claim(self, claim_id: str) -> list[EvidenceUnit]:
        """Distinct evidence units linked from the claim's evidence_links, sorted by evidence_id."""
        claim = self._claims.get(claim_id)
        if claim is None:
            return []
        ids: set[str] = set()
        for link in claim.evidence_links:
            ev = self._evidence.get(link.evidence_id)
            if ev is not None:
                ids.add(ev.evidence_id)
        result = [self._evidence[i] for i in sorted(ids)]
        return result

    def links_for_claim(self, claim_id: str) -> list[ClaimEvidenceLink]:
        """Typed claim-evidence links, sorted by (evidence_id, link_type)."""
        claim = self._claims.get(claim_id)
        if claim is None:
            return []
        return sorted(claim.evidence_links, key=lambda l: (l.evidence_id, l.link_type))

    def claims_for_evidence(self, evidence_id: str) -> list[Claim]:
        """Claims that reference this evidence_id in any evidence_link, sorted by claim_id."""
        claim_ids = self._ev_to_claims.get(evidence_id, set())
        result = [self._claims[cid] for cid in sorted(claim_ids)]
        return result

    def claims_for_rq(self, rq_id: str) -> list[Claim]:
        """Claims containing rq_id in claim.rq_ids, sorted by claim_id."""
        claim_ids = self._rq_to_claims.get(rq_id, set())
        result = [self._claims[cid] for cid in sorted(claim_ids)]
        return result

    def sources_for_claim(self, claim_id: str) -> list[Source]:
        """Distinct sources reachable via claim.evidence_links -> evidence -> source_id, sorted by source_id."""
        claim = self._claims.get(claim_id)
        if claim is None:
            return []
        source_ids: set[str] = set()
        for link in claim.evidence_links:
            ev = self._evidence.get(link.evidence_id)
            if ev is not None:
                source_ids.add(ev.source_id)
        result = [self._sources[sid] for sid in sorted(source_ids)]
        return result

    def citations_for_claim(self, claim_id: str) -> list[CitationLink]:
        """Citations whose claim_id matches, sorted by citation_id."""
        cit_ids = self._cl_to_citations.get(claim_id, set())
        result = [self._citations[cid] for cid in sorted(cit_ids)]
        return result

    def unsupported_claims(self, project_id: str) -> list[Claim]:
        """Claims in project with support_state == 'unsupported' (undetermined excluded), sorted by claim_id."""
        result = [
            cl
            for cl in self._claims.values()
            if cl.project_id == project_id and cl.support_state == "unsupported"
        ]
        result.sort(key=lambda c: c.claim_id)
        return result

    def orphan_evidence(self, project_id: str) -> list[EvidenceUnit]:
        """Evidence units in project not referenced by any Claim.evidence_links, sorted by evidence_id."""
        referenced: set[str] = set()
        for cl in self._claims.values():
            for link in cl.evidence_links:
                referenced.add(link.evidence_id)
        result = [
            ev
            for ev in self._evidence.values()
            if ev.project_id == project_id and ev.evidence_id not in referenced
        ]
        result.sort(key=lambda e: e.evidence_id)
        return result

    def broken_citation_links(self, project_id: str) -> list[CitationLink]:
        """Citations in project where referenced entities are missing or cross-project, sorted by citation_id."""
        result = []
        for cit in self._citations.values():
            if cit.project_id != project_id:
                continue
            broken = False
            claim = self._claims.get(cit.claim_id)
            if claim is None or claim.project_id != project_id:
                broken = True
            source = self._sources.get(cit.source_id)
            if source is None or source.project_id != project_id:
                broken = True
            if cit.evidence_id is not None:
                ev = self._evidence.get(cit.evidence_id)
                if ev is None or ev.project_id != project_id:
                    broken = True
            if broken:
                result.append(cit)
        result.sort(key=lambda c: c.citation_id)
        return result

    def claims_for_section(self, section_id: str) -> list[Claim]:
        """Claims containing section_id in claim.section_ids, sorted by claim_id."""
        claim_ids = self._sec_to_claims.get(section_id, set())
        result = [self._claims[cid] for cid in sorted(claim_ids)]
        return result

    def sources_for_evidence(self, evidence_id: str) -> list[Source]:
        """Source behind an evidence unit, sorted by source_id (0 or 1 element)."""
        ev = self._evidence.get(evidence_id)
        if ev is None:
            return []
        src = self._sources.get(ev.source_id)
        if src is None:
            return []
        return [src]

    def citations_for_source(self, source_id: str) -> list[CitationLink]:
        """Citations referencing this source_id, sorted by citation_id."""
        cit_ids = self._src_to_citations.get(source_id, set())
        result = [self._citations[cid] for cid in sorted(cit_ids)]
        return result

    def records_for_citation(self, citation_id: str) -> list[CitationVerificationRecord]:
        """Verification records for a citation, sorted by run_time then record_id."""
        return list(self._records.get(citation_id, []))

    # ------------------------------------------------------------------
    # Lookup getters (single entity)
    # ------------------------------------------------------------------

    def project(self, project_id: str) -> ResearchProject | None:
        """Return the project or None."""
        return self._projects.get(project_id)

    def question(self, question_id: str) -> ResearchQuestion | None:
        """Return the question or None."""
        return self._questions.get(question_id)

    def source(self, source_id: str) -> Source | None:
        """Return the source or None."""
        return self._sources.get(source_id)

    def evidence(self, evidence_id: str) -> EvidenceUnit | None:
        """Return the evidence unit or None."""
        return self._evidence.get(evidence_id)

    def claim(self, claim_id: str) -> Claim | None:
        """Return the claim or None."""
        return self._claims.get(claim_id)

    def section(self, section_id: str) -> PaperSection | None:
        """Return the section or None."""
        return self._sections.get(section_id)

    def citation(self, citation_id: str) -> CitationLink | None:
        """Return the citation link or None."""
        return self._citations.get(citation_id)

    # ------------------------------------------------------------------
    # Sorted all_* iterators
    # ------------------------------------------------------------------

    def all_projects(self) -> list[ResearchProject]:
        """All projects sorted by project_id."""
        return sorted(self._projects.values(), key=lambda p: p.project_id)

    def all_questions(self) -> list[ResearchQuestion]:
        """All questions sorted by question_id."""
        return sorted(self._questions.values(), key=lambda q: q.question_id)

    def all_sources(self) -> list[Source]:
        """All sources sorted by source_id."""
        return sorted(self._sources.values(), key=lambda s: s.source_id)

    def all_evidence(self) -> list[EvidenceUnit]:
        """All evidence units sorted by evidence_id."""
        return sorted(self._evidence.values(), key=lambda e: e.evidence_id)

    def all_claims(self) -> list[Claim]:
        """All claims sorted by claim_id."""
        return sorted(self._claims.values(), key=lambda c: c.claim_id)

    def all_sections(self) -> list[PaperSection]:
        """All sections sorted by section_id."""
        return sorted(self._sections.values(), key=lambda s: s.section_id)

    def all_citations(self) -> list[CitationLink]:
        """All citations sorted by citation_id."""
        return sorted(self._citations.values(), key=lambda c: c.citation_id)
