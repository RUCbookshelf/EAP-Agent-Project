"""Domain-owned repository protocols and in-memory adapters for Academic Writing.

Consumer-owned protocols; core services depend on Protocol types, never concrete adapters.
In-memory adapters exist for foundation/testing; persistence adapters arrive later.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .entities import (
    CitationLink,
    CitationVerificationRecord,
    Claim,
    EvidenceUnit,
    PaperSection,
    ResearchProject,
    ResearchQuestion,
    Source,
)
from .errors import AcademicDomainError
from .provenance import ProvenanceGraph


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class ResearchProjectRepository(Protocol):
    def create(self, project: ResearchProject) -> ResearchProject: ...
    def get(self, project_id: str) -> ResearchProject | None: ...
    def list(self) -> list[ResearchProject]: ...


@runtime_checkable
class ResearchQuestionRepository(Protocol):
    def create(self, question: ResearchQuestion) -> ResearchQuestion: ...
    def get(self, question_id: str) -> ResearchQuestion | None: ...
    def list(self) -> list[ResearchQuestion]: ...


@runtime_checkable
class SourceRepository(Protocol):
    def create(self, source: Source) -> Source: ...
    def get(self, source_id: str) -> Source | None: ...
    def list(self) -> list[Source]: ...
    def save(self, source: Source) -> Source: ...


@runtime_checkable
class EvidenceRepository(Protocol):
    def create(self, evidence: EvidenceUnit) -> EvidenceUnit: ...
    def get(self, evidence_id: str) -> EvidenceUnit | None: ...
    def list(self) -> list[EvidenceUnit]: ...


@runtime_checkable
class ClaimRepository(Protocol):
    def create(self, claim: Claim) -> Claim: ...
    def get(self, claim_id: str) -> Claim | None: ...
    def list(self) -> list[Claim]: ...
    def save(self, claim: Claim) -> Claim: ...


@runtime_checkable
class PaperSectionRepository(Protocol):
    def create(self, section: PaperSection) -> PaperSection: ...
    def get(self, section_id: str) -> PaperSection | None: ...
    def list(self) -> list[PaperSection]: ...


@runtime_checkable
class CitationLinkRepository(Protocol):
    def create(self, citation: CitationLink) -> CitationLink: ...
    def get(self, citation_id: str) -> CitationLink | None: ...
    def list(self) -> list[CitationLink]: ...
    def save(self, citation: CitationLink) -> CitationLink: ...


@runtime_checkable
class CitationVerificationRecordRepository(Protocol):
    def append(self, record: CitationVerificationRecord) -> CitationVerificationRecord: ...
    def list_for_citation(self, citation_id: str) -> list[CitationVerificationRecord]: ...
    def list(self) -> list[CitationVerificationRecord]: ...


@runtime_checkable
class AcademicRepositories(Protocol):
    projects: ResearchProjectRepository
    questions: ResearchQuestionRepository
    sources: SourceRepository
    evidence: EvidenceRepository
    claims: ClaimRepository
    sections: PaperSectionRepository
    citations: CitationLinkRepository
    records: CitationVerificationRecordRepository


# ---------------------------------------------------------------------------
# In-memory private adapters
# ---------------------------------------------------------------------------


def _id_key(entity_id: str) -> str:
    return entity_id


class _InMemoryProjectRepo:
    def __init__(self) -> None:
        self._store: dict[str, ResearchProject] = {}

    def create(self, project: ResearchProject) -> ResearchProject:
        pid = project.project_id
        if pid in self._store:
            raise AcademicDomainError(
                f"Project with id {pid!r} already exists",
                code="duplicate_id",
            )
        self._store[pid] = project
        return project

    def get(self, project_id: str) -> ResearchProject | None:
        return self._store.get(project_id)

    def list(self) -> list[ResearchProject]:
        return [self._store[k] for k in sorted(self._store)]


class _InMemoryQuestionRepo:
    def __init__(self) -> None:
        self._store: dict[str, ResearchQuestion] = {}

    def create(self, question: ResearchQuestion) -> ResearchQuestion:
        qid = question.question_id
        if qid in self._store:
            raise AcademicDomainError(
                f"Question with id {qid!r} already exists",
                code="duplicate_id",
            )
        self._store[qid] = question
        return question

    def get(self, question_id: str) -> ResearchQuestion | None:
        return self._store.get(question_id)

    def list(self) -> list[ResearchQuestion]:
        return [self._store[k] for k in sorted(self._store)]


class _InMemorySourceRepo:
    def __init__(self) -> None:
        self._store: dict[str, Source] = {}

    def create(self, source: Source) -> Source:
        sid = source.source_id
        if sid in self._store:
            raise AcademicDomainError(
                f"Source with id {sid!r} already exists",
                code="duplicate_id",
            )
        self._store[sid] = source
        return source

    def get(self, source_id: str) -> Source | None:
        return self._store.get(source_id)

    def list(self) -> list[Source]:
        return [self._store[k] for k in sorted(self._store)]

    def save(self, source: Source) -> Source:
        sid = source.source_id
        if sid not in self._store:
            raise AcademicDomainError(
                f"Source with id {sid!r} not found",
                code="entity_not_found",
            )
        self._store[sid] = source
        return source


class _InMemoryEvidenceRepo:
    def __init__(self) -> None:
        self._store: dict[str, EvidenceUnit] = {}

    def create(self, evidence: EvidenceUnit) -> EvidenceUnit:
        eid = evidence.evidence_id
        if eid in self._store:
            raise AcademicDomainError(
                f"Evidence with id {eid!r} already exists",
                code="duplicate_id",
            )
        self._store[eid] = evidence
        return evidence

    def get(self, evidence_id: str) -> EvidenceUnit | None:
        return self._store.get(evidence_id)

    def list(self) -> list[EvidenceUnit]:
        return [self._store[k] for k in sorted(self._store)]


class _InMemoryClaimRepo:
    def __init__(self) -> None:
        self._store: dict[str, Claim] = {}

    def create(self, claim: Claim) -> Claim:
        cid = claim.claim_id
        if cid in self._store:
            raise AcademicDomainError(
                f"Claim with id {cid!r} already exists",
                code="duplicate_id",
            )
        self._store[cid] = claim
        return claim

    def get(self, claim_id: str) -> Claim | None:
        return self._store.get(claim_id)

    def list(self) -> list[Claim]:
        return [self._store[k] for k in sorted(self._store)]

    def save(self, claim: Claim) -> Claim:
        cid = claim.claim_id
        if cid not in self._store:
            raise AcademicDomainError(
                f"Claim with id {cid!r} not found",
                code="entity_not_found",
            )
        self._store[cid] = claim
        return claim


class _InMemorySectionRepo:
    def __init__(self) -> None:
        self._store: dict[str, PaperSection] = {}

    def create(self, section: PaperSection) -> PaperSection:
        sid = section.section_id
        if sid in self._store:
            raise AcademicDomainError(
                f"Section with id {sid!r} already exists",
                code="duplicate_id",
            )
        self._store[sid] = section
        return section

    def get(self, section_id: str) -> PaperSection | None:
        return self._store.get(section_id)

    def list(self) -> list[PaperSection]:
        return [self._store[k] for k in sorted(self._store)]


class _InMemoryCitationRepo:
    def __init__(self) -> None:
        self._store: dict[str, CitationLink] = {}

    def create(self, citation: CitationLink) -> CitationLink:
        cid = citation.citation_id
        if cid in self._store:
            raise AcademicDomainError(
                f"Citation with id {cid!r} already exists",
                code="duplicate_id",
            )
        self._store[cid] = citation
        return citation

    def get(self, citation_id: str) -> CitationLink | None:
        return self._store.get(citation_id)

    def list(self) -> list[CitationLink]:
        return [self._store[k] for k in sorted(self._store)]

    def save(self, citation: CitationLink) -> CitationLink:
        cid = citation.citation_id
        if cid not in self._store:
            raise AcademicDomainError(
                f"Citation with id {cid!r} not found",
                code="entity_not_found",
            )
        self._store[cid] = citation
        return citation


class _InMemoryRecordRepo:
    """Append-only: no update or delete methods exist."""

    def __init__(self) -> None:
        self._store: dict[str, CitationVerificationRecord] = {}

    def append(self, record: CitationVerificationRecord) -> CitationVerificationRecord:
        rid = record.record_id
        if rid in self._store:
            raise AcademicDomainError(
                f"Record with id {rid!r} already exists",
                code="duplicate_id",
            )
        self._store[rid] = record
        return record

    def list_for_citation(self, citation_id: str) -> list[CitationVerificationRecord]:
        filtered = [r for r in self._store.values() if r.citation_id == citation_id]
        filtered.sort(key=lambda r: (r.run_time, r.record_id))
        return filtered

    def list(self) -> list[CitationVerificationRecord]:
        return sorted(self._store.values(), key=lambda r: r.record_id)


# ---------------------------------------------------------------------------
# Composite in-memory adapter
# ---------------------------------------------------------------------------


class InMemoryRepositories:
    """Dict-backed adapters implementing all protocols; single composite for services."""

    def __init__(self) -> None:
        self.projects: _InMemoryProjectRepo = _InMemoryProjectRepo()
        self.questions: _InMemoryQuestionRepo = _InMemoryQuestionRepo()
        self.sources: _InMemorySourceRepo = _InMemorySourceRepo()
        self.evidence: _InMemoryEvidenceRepo = _InMemoryEvidenceRepo()
        self.claims: _InMemoryClaimRepo = _InMemoryClaimRepo()
        self.sections: _InMemorySectionRepo = _InMemorySectionRepo()
        self.citations: _InMemoryCitationRepo = _InMemoryCitationRepo()
        self.records: _InMemoryRecordRepo = _InMemoryRecordRepo()

    def to_graph(self) -> ProvenanceGraph:
        """Deterministic snapshot of all stores into a ProvenanceGraph."""
        return ProvenanceGraph(
            projects=self.projects.list(),
            questions=self.questions.list(),
            sources=self.sources.list(),
            evidence_units=self.evidence.list(),
            claims=self.claims.list(),
            sections=self.sections.list(),
            citations=self.citations.list(),
            records=self.records.list(),
        )

