# 08 — Test and Verification

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU9 GREEN

## 1. Test layers (tests/academic/)

| Layer | Files | Coverage |
| --- | --- | --- |
| Entity contracts | test_entities.py | happy paths, ID prefixes, blank/length/extra/frozen rejection, Source hash consistency, serialization round-trips, list defaults, Claim support-state invariants, D-32 record invariants |
| Provenance graph | test_provenance.py | all 13 queries, empty graphs, unknown ids, deterministic ordering, duplicate dedupe, constructor type checks, getters |
| Integrity guardrails | test_integrity.py | ACAD-RULE-01..07 (each rule + clean case), sorting, no-duplicate emission, R06 detail summarization, rules registry |
| Vocabulary boundary | test_vocabulary.py | frozen 8-value evidence status, epistemic re-export, downgrade-only matrix, provisional adapter, no cross-axis conflation |
| Repository protocols | test_repositories.py | create/get/list/save, duplicates, unknown ids, append-only records, runtime-checkable conformance, to_graph round-trip |
| Application services | test_services.py | full happy flow, auto/explicit ids, error matrix (12+), dedupe no-ops, citation unverified, unsupported default, support-state declaration |
| Citation verification | test_citation.py | verified/unverified/unavailable paths, ACAD-INV-02 cross-layer contract, history growth + frozen records, manifest, no network imports |
| Fixture matrix | test_fixture_matrix.py | goal-section-21 matrix presence, provenance queries, integrity on invalid rows, citation verification + honest states, no L2 contamination, serialization spot-checks |

## 2. Suite results

- Focused Academic suite: 322 passed / 0 failed (pytest tests/academic, Python 3.11.15, worktree venv).
- Every work-unit gate ran the full focused suite (not just the new file), so cross-module regressions within the domain are caught continuously.
- Independent reviews (fresh deepseek-v4-flash) at WU2 (entities), WU3 (provenance), WU4+WU5 (integrity+vocabulary), WU7+WU8 (services+citation): APPROVE_WITH_FINDINGS each; all findings dispositioned (fixed or explicitly deferred with named invariants). Review notes under `.agent-workflow/academic-writing-foundation/evidence/` (noncanonical runtime).

## 3. Domain invariant tests (named)

- ACAD-INV-01: Claim support-state/link consistency (entity validator + integrity R01).
- ACAD-INV-02: verified citation requires an append-only verified record (service construction + integrity R07 cross-layer contract test).
- ACAD-INV-03: cross-project references rejected at write time and detected by integrity (R02/03/04/06).
- ACAD-INV-04: verification_unavailable frozen without source text (entity + verifier).
- ACAD-INV-05: verification records append-only and frozen.

## 4. Regression scope (WU10)

- Focused Academic suite (above).
- Existing core smoke: architecture test, database test, corpus baseline tests (in-baseline content), contract inventory smoke — run at WU10 gate; results recorded in 10_INTEGRATION_HANDOFF.md and the final report.
- No production L2 behavior changes: zero modifications to L2 modules; git diff limited to `app/academic/`, `tests/academic/`, `docs/departments/academic-writing/foundation/`.

## 5. Evidence

- All test files under `tests/academic/`; runtime evidence in `.agent-workflow/academic-writing-foundation/run-ledger.jsonl`