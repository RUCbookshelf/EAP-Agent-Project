# 09 — Cross-Department Dependencies

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU5 GREEN (dependencies declared; nothing implemented)

Every item below is a dependency Academic Writing declares for later integration. None are implemented in this Goal (goal sections 3/10/26: locally encapsulated; integration deferred to Architecture & Integration).

## Shared Platform & Core

| Dependency | Marker | Detail |
| --- | --- | --- |
| Domain discriminator (`domain=l2/academic`) | REQUIRED FOR INTEGRATION | server-derived attribution (D-21); additive migration 14 (D-17/D-36); Academic entities never assume it exists |
| Domain-pack registration layout (`app/configuration/domain_packs/academic/...`) | REQUIRED FOR INTEGRATION | registry-content layout (D-26); Academic paper/section kinds register in a separate namespace (D-04) |
| Evidence-status vocabulary (verified/candidate/insufficient/suppressed/not_applicable/unavailable/legacy/unresolved) | REQUIRED FOR INTEGRATION | Academic mirrors it domain-locally (`app/academic/vocabulary.py::EvidenceStatus`) with provisional adapter `academic_verification_to_shared`; no competing global contract |
| Epistemic-status vocabulary (observed_descriptive/gated_inference/recommendation/outcome_claim) | REQUIRED FOR INTEGRATION | mirror + downgrade-only helper; persistence form Researcher decision required |
| Composition root consolidation + version single-sourcing | REQUIRED FOR INTEGRATION | Academic module stays unregistered until then (D-20) |
| Persistence integration (SQLite adapters + additive migration) | REQUIRED FOR INTEGRATION | see 07_PERSISTENCE_BOUNDARY.md |
| API routing (academic endpoints) | DEFERRED | no endpoints in this Goal |
| FeedbackPolicy contract (Academic instance with source-verification pre-gate, D-03) | DEFERRED | blocked until Shared Core contract + citation policy decision |
| Journey event vocabulary / academic journey honest state | DEFERRED | "academic journey unavailable in MVP" honest state is the frozen disposition (D-37/RT-20) |

## Frontend & Product Experience

| Dependency | Marker | Detail |
| --- | --- | --- |
| Academic paper/sections/sources surfaces | DEFERRED | blocked until domain data contracts exist (Frontend charter) |
| Domain-workspace selector | DEFERRED | appears only when Academic ships (D-10) |
| Locale keys for Academic labels | DEFERRED | additive-only keys; 600/600 parity contract (Frontend-owned) |
| StableReferenceNav with paper/section references | OPTIONAL | later; no UI work in this Goal |

## Research Evaluation & Data Governance

| Dependency | Marker | Detail |
| --- | --- | --- |
| Citation policy decision (never / source-grounded-only / disabled-by-default) | REQUIRED FOR INTEGRATION | default: never by default (15: D. citation policy); Academic verification boundary is ready either way |
| Academic task/paper/section taxonomy authority | REQUIRED FOR INTEGRATION | `source_type`/`section_kind` stay free text until the taxonomy decision |
| Domain-scoped exports for Academic data | DEFERRED | export-time domain validation is Research Evaluation-owned (D-36) |
| Plagiarism detection | NA | separate product/instrument decision; never this Goal |

## Integration-point markers (module-level constants)

- `app/academic/vocabulary.py::SHARED_CORE_EVIDENCE_STATUS`, `SHARED_CORE_EPISTEMIC_STATUS`, `EPISTEMIC_STATUS_PERSISTENCE` — exact symbols Academic expects from Shared Core, listed for the handoff.
- `app/academic/integrity.py::INTEGRITY_RULES_VERSION`, `app/academic/citation.py::VERIFICATION_RULES_VERSION` — versioned manifests Academic owns.

## Evidence

- `app/academic/vocabulary.py`; `docs/architecture/writing-intelligence-platform/12_DEPENDENCY_ROADMAP.md`; `DEPARTMENT_GOAL_HANDOFFS.md`