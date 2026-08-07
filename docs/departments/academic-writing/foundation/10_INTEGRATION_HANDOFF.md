# 10 — Integration Handoff

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU10 GREEN (handoff complete; DEPARTMENT GREEN)

## 1. Final branch state

- Branch: `dept/academic-foundation`
- Baseline: b171cce (corrected common Wave-1 baseline; fast-forwarded per user direction)
- Final HEAD: see final report (last commit of this Goal)
- Mergeability: branch is a descendant path from b171cce (all commits additive under `app/academic/`, `tests/academic/`, `docs/departments/academic-writing/foundation/`); no conflicts expected with Corpus Stage 5 or other department branches.

## 2. New domain modules (additive)

| Module | Contents |
| --- | --- |
| app/academic/__init__.py | module docstring |
| app/academic/errors.py | AcademicDomainError(message, code) |
| app/academic/entities.py | 7 entities + ClaimEvidenceLink + CitationVerificationRecord (frozen Pydantic v2, extra=forbid) |
| app/academic/provenance.py | ProvenanceGraph (13 queries + getters, deterministic) |
| app/academic/integrity.py | IntegrityService + ACAD-RULE-01..07 + versioned registry |
| app/academic/vocabulary.py | evidence-status mirror + epistemic re-export + downgrade helper + provisional adapter |
| app/academic/repositories.py | 8 runtime_checkable protocols + AcademicRepositories + InMemoryRepositories + to_graph |
| app/academic/services.py | AcademicService (12+1 use cases) |
| app/academic/citation.py | CitationVerifier + CitationVerificationService + versioned rule manifest |
| tests/academic/* | fixtures + 9 test modules (322 tests) |

## 3. Seven core entities

ResearchProject, ResearchQuestion, Source, EvidenceUnit, Claim (with ClaimEvidenceLink), PaperSection, CitationLink — all implemented, validated, serializable, frozen (edits create new versions).

## 4. Domain invariants

ACAD-INV-01..05 (see 08_TEST_AND_VERIFICATION.md section 3) + ACAD-RULE-01..07 (04_ACADEMIC_INTEGRITY_RULES.md). Honest states are first-class: unsupported/undetermined claims, unverified/verification_unavailable citations are valid and never silently repaired.

## 5. Provenance model

Four independent chains (source / evidence / claim-evidence / citation) traversable via ProvenanceGraph without flattening into one source_id (03_PROVENANCE_MODEL.md).

## 6. Citation verification behavior

Local + deterministic only; versioned manifest (academic-citation-verification-v0.1.0, CIT-RULE-01..05); D-32 append-only records; verified impossible without a record (ACAD-INV-02); no source text => verification_unavailable; no semantic support claims; no external APIs (05_CITATION_VERIFICATION_BOUNDARY.md).

## 7. Repository protocols

8 consumer-owned runtime_checkable protocols + in-memory adapters (append-only record repo; deterministic sorted lists); persistence handoff documented (07_PERSISTENCE_BOUNDARY.md); no SQLite, no migration.

## 8. Application services

AcademicService use cases (create project, add RQ, register source, capture evidence, create claim, link evidence, declare support state, create section, attach claim, create citation, validate integrity, project graph) — framework-neutral (06_APPLICATION_SERVICES.md).

## 9. Tests

Focused Academic suite 322 passed / 0 failed; regression results in section 14 below.

## 10. Shared Core dependencies (exact symbols Academic expects)

- Domain discriminator values `l2`/`academic` + server-derived attribution resolver (D-21)
- Migration 14 additive columns (`domain` + `language`, CHECK + DEFAULT) per D-17/D-36
- Domain-pack layout `app/configuration/domain_packs/academic/{version}/...` (D-26)
- Evidence-status vocabulary: `verified/candidate/insufficient/suppressed/not_applicable/unavailable/legacy/unresolved`
- Epistemic-status vocabulary: `observed_descriptive/gated_inference/recommendation/outcome_claim` (persistence form Researcher decision required)
- Composition root + version single-sourcing (D-20)
- FeedbackPolicy contract (Academic instance later; D-03)
- Academic module registration: none until composition-root consolidation lands

## 11. Research Governance dependencies

- Citation policy decision (default: never by default)
- Academic task/paper/section taxonomy authority (source_type/section_kind currently free text)
- Domain-scoped export validation (D-36)
- Plagiarism detection: NA

## 12. Frontend dependencies

- Domain data contracts before any Academic surfaces
- Domain-workspace selector (D-10) + additive locale keys
- StableReferenceNav extension (paper/section references) — OPTIONAL
- "academic journey unavailable in MVP" honest state (D-37/RT-20)

## 13. Migration requirements

None. Migration 13 remains the authority; this Goal created no migration. Future persistence requires one additive Academic migration coordinated through Architecture & Integration (04:6).

## 14. Verification (final regression)

| Check | Result |
| --- | --- |
| Focused Academic suite | 322 passed / 0 failed |
| Existing core smoke (architecture/database/corpus/contracts) | see final report |
| git diff --check | clean (after whitespace fix) |
| git status | only .agent-workflow/ untracked (noncanonical runtime planning state) |
| Production L2 behavior | unchanged (zero L2 module edits) |

## 15. Shared-contract assumptions

- No shared contract was invented; vocabulary mirrors are marked INTEGRATION_POINT and owned by Shared Platform & Core.
- Academic verification states are domain states; registry-level evidence-status alignment is Shared Core's job (02:4).
- Academic entities remain unregistered until Shared Core H1 provides the seam.

## 16. Likely merge-conflict files

None expected: all additions are new paths (`app/academic/`, `tests/academic/`, `docs/departments/academic-writing/`); no overlap with Corpus Stage 5 (app/corpus, docs/corpus-intelligence, tests/corpus) or other departments. If any department later touches `app/` package-level `__init__` or requirements, coordinate via Architecture & Integration.

## 17. Recommended integration order

1. Shared Core H1 (composition root, discriminator, migration 14, vocabularies, domain packs layout) — prerequisites per 12_DEPENDENCY_ROADMAP.md.
2. Research Evaluation: citation policy + taxonomy authority.
3. Academic persistence adapters (SQLite implementing the existing protocols; additive migration).
4. Academic API routing (thin routers over AcademicService).
5. Frontend Academic surfaces (paper/sections/sources) after domain data contracts.
6. Milestone Integration Gate (13_INTEGRATION_AND_GOVERNANCE.md section 6) before any production exposure.

## 18. Post-merge tests

- Domain-isolation contract tests (D-31): no cross-domain submission in another domain's history/journey/revision/practice; exports domain-scoped.
- Full core suite (L2 unchanged) + focused Academic suite.
- Integration handoff re-verification: provenance chains survive persistence; ACAD-INV-02 holds through SQLite adapters; locale parity if UI keys are added.