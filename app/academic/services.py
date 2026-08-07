"""Academic Writing application/domain services.

Framework-neutral: no FastAPI, no Streamlit, no LLM.  Deterministic
use-case orchestration over repository protocols, integrity, and provenance.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Optional

from .entities import (
    CitationLink,
    Claim,
    ClaimEvidenceLink,
    ClaimSupportState,
    EvidenceKind,
    EvidenceUnit,
    PaperSection,
    ResearchProject,
    ResearchQuestion,
    Source,
    SourceOrigin,
)
from .errors import AcademicDomainError
from .integrity import IntegrityService, IntegrityViolation
from .provenance import ProvenanceGraph
from .repositories import AcademicRepositories


def _hex12() -> str:
    """Return 12-character lowercase hex from uuid4."""
    return uuid.uuid4().hex[:12]


class AcademicService:
    """Deterministic application/domain service for Academic Writing entities."""

    def __init__(self, repositories: AcademicRepositories) -> None:
        self._repos = repositories

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_project(self, project_id: str) -> ResearchProject | None:
        """Convenience passthrough to the project repository."""
        return self._repos.projects.get(project_id)

    def project_graph(self, project_id: str) -> ProvenanceGraph:
        """Return a full snapshot of all repositories as a ProvenanceGraph.

        Projection / filtering is caller-side.
        """
        return self._repos.to_graph()

    def validate_project_integrity(
        self, project_id: str
    ) -> list[IntegrityViolation]:
        """Validate structural integrity for a single project."""
        graph = self._repos.to_graph()
        return IntegrityService().validate_project(project_id, graph)

    # ------------------------------------------------------------------
    # Write — Projects
    # ------------------------------------------------------------------

    def create_research_project(
        self,
        title: str,
        *,
        research_scope: str | None = None,
        project_id: str | None = None,
    ) -> ResearchProject:
        pid = project_id or f"rp-{_hex12()}"
        project = ResearchProject(
            project_id=pid,
            title=title,
            research_scope=research_scope,
        )
        return self._repos.projects.create(project)

    # ------------------------------------------------------------------
    # Write — Research Questions
    # ------------------------------------------------------------------

    def add_research_question(
        self,
        project_id: str,
        question_text: str,
        *,
        question_id: str | None = None,
    ) -> ResearchQuestion:
        self._require_project(project_id)
        qid = question_id or f"rq-{_hex12()}"
        rq = ResearchQuestion(
            question_id=qid,
            project_id=project_id,
            question_text=question_text,
        )
        return self._repos.questions.create(rq)

    # ------------------------------------------------------------------
    # Write — Sources
    # ------------------------------------------------------------------

    def register_source(
        self,
        project_id: str,
        *,
        title: str,
        origin: SourceOrigin,
        authors: str | None = None,
        year: int | None = None,
        publication: str | None = None,
        doi: str | None = None,
        source_type: str | None = None,
        source_text: str | None = None,
        file_name: str | None = None,
        file_hash: str | None = None,
        source_id: str | None = None,
    ) -> Source:
        self._require_project(project_id)
        sid = source_id or f"src-{_hex12()}"
        st_hash = (
            hashlib.sha256(source_text.encode("utf-8")).hexdigest()
            if source_text is not None
            else None
        )
        source = Source(
            source_id=sid,
            project_id=project_id,
            title=title,
            origin=origin,
            authors=authors,
            year=year,
            publication=publication,
            doi=doi,
            source_type=source_type,
            source_text=source_text,
            source_text_hash=st_hash,
            file_name=file_name,
            file_hash=file_hash,
        )
        return self._repos.sources.create(source)

    # ------------------------------------------------------------------
    # Write - Evidence Units
    # ------------------------------------------------------------------

    def capture_evidence_unit(
        self,
        project_id: str,
        *,
        source_id: str,
        kind: EvidenceKind,
        locator: str,
        content: str,
        rq_ids: list[str] | None = None,
        learner_note: str | None = None,
        evidence_id: str | None = None,
    ) -> EvidenceUnit:
        source = self._require_source_in_project(project_id, source_id)
        eid = evidence_id or f"ev-{_hex12()}"
        ev = EvidenceUnit(
            evidence_id=eid,
            project_id=project_id,
            source_id=source_id,
            source_version=source.version,
            kind=kind,
            locator=locator,
            content=content,
            rq_ids=rq_ids or [],
            learner_note=learner_note,
        )
        return self._repos.evidence.create(ev)

    # ------------------------------------------------------------------
    # Write - Claims
    # ------------------------------------------------------------------

    def create_claim(
        self,
        project_id: str,
        claim_text: str,
        *,
        support_state: ClaimSupportState = "unsupported",
        rq_ids: list[str] | None = None,
        section_ids: list[str] | None = None,
        claim_id: str | None = None,
    ) -> Claim:
        self._require_project(project_id)
        # Validate referenced RQs belong to project
        for rq_id in (rq_ids or []):
            rq = self._repos.questions.get(rq_id)
            if rq is None or rq.project_id != project_id:
                raise AcademicDomainError(
                    f"Research question {rq_id!r} not found in project {project_id!r}",
                    code="entity_not_found",
                )
        # Validate referenced sections belong to project
        for sec_id in (section_ids or []):
            sec = self._repos.sections.get(sec_id)
            if sec is None or sec.project_id != project_id:
                raise AcademicDomainError(
                    f"Paper section {sec_id!r} not found in project {project_id!r}",
                    code="entity_not_found",
                )
        cid = claim_id or f"cl-{_hex12()}"
        claim = Claim(
            claim_id=cid,
            project_id=project_id,
            claim_text=claim_text,
            support_state=support_state,
            rq_ids=rq_ids or [],
            section_ids=section_ids or [],
        )
        return self._repos.claims.create(claim)

    # ------------------------------------------------------------------
    # Write — Claim-Evidence Links
    # ------------------------------------------------------------------

    def link_evidence_to_claim(
        self,
        claim_id: str,
        evidence_id: str,
        link_type: str,
    ) -> Claim:
        claim = self._repos.claims.get(claim_id)
        if claim is None:
            raise AcademicDomainError(
                f"Claim {claim_id!r} not found",
                code="entity_not_found",
            )
        evidence = self._repos.evidence.get(evidence_id)
        if evidence is None:
            raise AcademicDomainError(
                f"Evidence {evidence_id!r} not found",
                code="entity_not_found",
            )
        if claim.project_id != evidence.project_id:
            raise AcademicDomainError(
                f"Evidence {evidence_id!r} belongs to project {evidence.project_id!r}, "
                f"but claim {claim_id!r} belongs to project {claim.project_id!r}",
                code="invalid_state",
            )
        # Dedupe: if identical (evidence_id, link_type) already present, no-op
        existing = {
            (link.evidence_id, link.link_type) for link in claim.evidence_links
        }
        if (evidence_id, link_type) in existing:
            return claim
        new_link = ClaimEvidenceLink(evidence_id=evidence_id, link_type=link_type)
        updated = claim.model_copy(
            update={"evidence_links": [*claim.evidence_links, new_link]}
        )
        return self._repos.claims.save(updated)

    # ------------------------------------------------------------------
    # Write - Paper Sections
    # ------------------------------------------------------------------

    def create_paper_section(
        self,
        project_id: str,
        *,
        section_title: str,
        order: int = 0,
        section_kind: str | None = None,
        parent_section_id: str | None = None,
        passage_span: str | None = None,
        rq_ids: list[str] | None = None,
        section_id: str | None = None,
    ) -> PaperSection:
        self._require_project(project_id)
        if parent_section_id is not None:
            parent = self._repos.sections.get(parent_section_id)
            if parent is None or parent.project_id != project_id:
                raise AcademicDomainError(
                    f"Parent section {parent_section_id!r} not found in project {project_id!r}",
                    code="entity_not_found",
                )
        sid = section_id or f"sec-{_hex12()}"
        sec = PaperSection(
            section_id=sid,
            project_id=project_id,
            section_title=section_title,
            order=order,
            section_kind=section_kind,
            parent_section_id=parent_section_id,
            passage_span=passage_span,
            rq_ids=rq_ids or [],
        )
        return self._repos.sections.create(sec)

    # ------------------------------------------------------------------
    # Write - Attach Claim to Section
    # ------------------------------------------------------------------

    def attach_claim_to_section(self, claim_id: str, section_id: str) -> Claim:
        claim = self._repos.claims.get(claim_id)
        if claim is None:
            raise AcademicDomainError(
                f"Claim {claim_id!r} not found",
                code="entity_not_found",
            )
        section = self._repos.sections.get(section_id)
        if section is None:
            raise AcademicDomainError(
                f"Section {section_id!r} not found",
                code="entity_not_found",
            )
        if claim.project_id != section.project_id:
            raise AcademicDomainError(
                f"Section {section_id!r} belongs to project {section.project_id!r}, "
                f"but claim {claim_id!r} belongs to project {claim.project_id!r}",
                code="invalid_state",
            )
        # Dedupe no-op
        if section_id in claim.section_ids:
            return claim
        updated = claim.model_copy(
            update={"section_ids": [*claim.section_ids, section_id]}
        )
        return self._repos.claims.save(updated)

    # ------------------------------------------------------------------
    # Write - Citation Links
    # ------------------------------------------------------------------

    def create_citation_link(
        self,
        project_id: str,
        *,
        claim_id: str,
        source_id: str,
        evidence_id: str | None = None,
        passage_span: str | None = None,
        citation_id: str | None = None,
    ) -> CitationLink:
        # Claim must exist and belong to project
        claim = self._repos.claims.get(claim_id)
        if claim is None or claim.project_id != project_id:
            raise AcademicDomainError(
                f"Claim {claim_id!r} not found in project {project_id!r}",
                code="entity_not_found",
            )
        # Source must exist and belong to project
        source = self._repos.sources.get(source_id)
        if source is None or source.project_id != project_id:
            raise AcademicDomainError(
                f"Source {source_id!r} not found in project {project_id!r}",
                code="entity_not_found",
            )
        # Evidence (when supplied) must exist, belong to project, and have matching source
        if evidence_id is not None:
            evidence = self._repos.evidence.get(evidence_id)
            if evidence is None or evidence.project_id != project_id:
                raise AcademicDomainError(
                    f"Evidence {evidence_id!r} not found in project {project_id!r}",
                    code="entity_not_found",
                )
            if evidence.source_id != source_id:
                raise AcademicDomainError(
                    f"Evidence {evidence_id!r} source {evidence.source_id!r} "
                    f"does not match citation source {source_id!r}",
                    code="invalid_state",
                )
        cid = citation_id or f"cit-{_hex12()}"
        citation = CitationLink(
            citation_id=cid,
            project_id=project_id,
            claim_id=claim_id,
            source_id=source_id,
            evidence_id=evidence_id,
            passage_span=passage_span,
            verification_status="unverified",
        )
        return self._repos.citations.create(citation)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_project(self, project_id: str) -> ResearchProject:
        project = self._repos.projects.get(project_id)
        if project is None:
            raise AcademicDomainError(
                f"Project {project_id!r} not found",
                code="entity_not_found",
            )
        return project

    def _require_source_in_project(
        self, project_id: str, source_id: str
    ) -> Source:
        source = self._repos.sources.get(source_id)
        if source is None:
            raise AcademicDomainError(
                f"Source {source_id!r} not found",
                code="entity_not_found",
            )
        if source.project_id != project_id:
            raise AcademicDomainError(
                f"Source {source_id!r} belongs to project {source.project_id!r}, "
                f"not {project_id!r}",
                code="entity_not_found",
            )
        return source
