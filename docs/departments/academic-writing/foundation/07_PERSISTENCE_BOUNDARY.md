# 07 — Persistence Boundary

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU6 GREEN

## 1. Decision

Domain contracts + in-memory/test adapters + a clear future persistence handoff. NO SQLite migration was created in this Goal (migration 13 remains the authority; architecture 04:6). No second platform-wide persistence framework.

## 2. Repository protocols (consumer-owned, structural)

| Protocol | Key methods | Notes |
| --- | --- | --- |
| ResearchProjectRepository | create / get / list | sorted deterministic lists |
| ResearchQuestionRepository | create / get / list | |
| SourceRepository | create / get / list / save | save = upsert (new versions replace current; entity carries version) |
| EvidenceRepository | create / get / list | |
| ClaimRepository | create / get / list / save | save used by link/attach updates |
| PaperSectionRepository | create / get / list | |
| CitationLinkRepository | create / get / list / save | save used by verification status updates |
| CitationVerificationRecordRepository | append / list_for_citation / list | APPEND-ONLY by construction (no update/delete) |
| AcademicRepositories | composite protocol | structural attribute contract for services |

Conventions: duplicate create => AcademicDomainError(duplicate_id); unknown get => None; unknown save => entity_not_found; lists sorted by id; all protocols runtime_checkable for conformance tests.

## 3. In-memory adapters

`InMemoryRepositories` implements every protocol (dict-backed, deterministic, thread-confined to the test/foundation context) and exposes `to_graph()`: a deterministic snapshot bridge into `ProvenanceGraph` consumed by integrity validation and citation verification.

## 4. Future persistence handoff (integration-owned, NOT implemented here)

- SQLite adapters under `app/infrastructure/sqlite/repositories/` following the existing repository convention, implementing the same protocols (no service changes).
- One additive migration (Academic tables under the Academic namespace; `domain` discriminator columns arrive with the shared migration 14 per D-17/D-36).
- Append-only verification outcomes (history_evidence_registry precedent, 05:5): records never updated/deleted; entity edits create new versions, never overwrite verified records.
- Persistence form of epistemic status: Researcher decision required (compute-at-boundary interim).
- No graph store (05:5 graph verdict: read-time projection only).

## 5. Evidence

- `app/academic/repositories.py`; `tests/academic/test_repositories.py`
- Frozen references: goal section 18; 04:6; 05:5