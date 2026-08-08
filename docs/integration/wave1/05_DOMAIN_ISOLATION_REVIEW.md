# 05 — Domain Attribution & Isolation Review

**Gate:** WU7 GREEN — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)

## 1. Production expectation (verified)

```text
l2       = functional/default
academic = reserved/foundation only
```

No Academic workflow surface exists in the integrated baseline. Isolation verification therefore uses the merged Shared Core discriminator, controlled synthetic fixtures, and source-level construction checks (Goal section 12) — no Academic production route was invented.

## 2. Verification results

| Check (Goal section 12) | Result | Evidence |
| --- | --- | --- |
| Client cannot authoritatively relabel domain | PASS | `validate_advisory` rejects `academic`/unknown against server-derived `l2`; API layer returns 422 (shared-core tests); all workflow surfaces derive `l2`; no `academic` key in `WORKFLOW_SURFACE_DOMAIN` |
| Legacy L2 behavior stays safe | PASS | legacy payload (no advisory fields) accepted; resolver defaults to `l2`; migration 13 unchanged; zero L2 module edits |
| Submission ancestry preserves domain | PASS | shared `test_ancestry_resolver.py` 35 tests: multi-hop chains, derived tables (analysis/feedback/revision/practice) inherit, cycle detection, invalid stored values raise `DomainError` |
| Derived artifacts preserve ancestry | PASS | table-family registry covers `analysis_runs`, `metric_results`, `diagnoses`, `feedback_records`, `revision_groups`, `revisions`, `practice`, `learner_history` as `derived` |
| Unknown domain values fail safely | PASS | `validate_domain_scope` rejects unknown values; resolver raises `DomainError` on invalid stored values — never guesses |
| Academic entities cannot contaminate L2 learner history | PASS | AST contract test: zero `app.*` imports in `app/academic`; zero `app.academic` imports across 12 L2 consumer trees (analysis, analyzer, calf, calibration, diagnosis, feedback, journey, learner, practice, revision, research, services) |
| Academic entities not exposed through L2 Journey/Revision/Practice | PASS | same consumer-tree isolation test covers journey, revision, practice; academic has no Journey/Revision/Practice wiring |
| Research/export scope | PASS | exports remain l2-only data; `validate_domain_scope` is the D-36 export seam (wiring decision in WU8); no academic export surface exists |
| Learner-level aggregation | PASS | `learner_history` is resolver-covered; `same_domain` predicate enforces domain equality for revision-candidate selection and history/journey filters (shared tests) |

## 3. D-31 invariant mapping

| D-31 invariant | Status | Named contract |
| --- | --- | --- |
| 1. No cross-domain submission in another domain's history/journey/revision-candidates/practice provenance | PASS (by construction + mechanism) | `tests/contracts/test_wave1_domain_isolation.py` consumer-tree isolation; shared ancestry filter tests |
| 2. Exports domain-scoped by default and reject mixed input | PASS (mechanism available; wiring = WU8 seam; no mixed data can exist today) | `validate_domain_scope` contract tests; WU8 decision |
| 3. Learner-level endpoints filter by domain | PASS (mechanism + single resolver) | `same_domain`/`get_table_family` contract tests; shared resolver tests |
| 4. Revision candidate selection requires domain equality | PASS | shared `test_across_revision_candidates` + `same_domain` tests |
| 5. Each invariant is a named contract test | PASS | this file + `tests/contracts/test_wave1_vocabulary_convergence.py` + shared suites |

## 4. Integration-owned code changes

| Change | Why integration owns it | Frozen contract | Not feature development | Tests |
| --- | --- | --- | --- | --- |
| `tests/contracts/test_wave1_domain_isolation.py` (26 tests) | Cross-department isolation is an architecture-level gate (D-31); no single department can own the combined boundary | D-31 invariants 1-5, D-21, D-23, Goal section 12 | Pure contract tests over merged mechanisms; zero product behavior change | 26 passed |

## 5. Conclusion

**WU7 GREEN.** The merged Shared Core discriminator correctly serves the integrated domains: `l2` functional/default, `academic` reserved/foundation-only. All seven Goal section-12 checks and all five D-31 invariants pass as named contract tests. Academic remains unexposed to any L2 learner surface, and no Academic production route was added to test isolation.
