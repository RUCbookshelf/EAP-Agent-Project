# CORE WU1 Decomposition Recovery — Repair Status Register

- register_id: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811__REPAIR-STATUS-001
- updated: 2026-08-11 (local)
- inventory basis: inventory/A-B-C-D-E-PARTIAL-DIFF-INVENTORY.md (INV-001)

## R1 — review robustness / fail-closed boundaries — DONE (GREEN slice)

- worker: deepseek/deepseek-v4-flash + ultra, PLANNING_DISABLED=1
- verdict: DONE — all assigned findings repaired
- findings addressed: D3 (FK-nonexistent activity -> 404, no write), D4
  (duplicate PA/RE IDs -> 409, original rows intact; scheduler-state upsert
  intentionally remains last-write-wins), D5 (student/ownership binding ->
  403 kinds), C9 (naive/non-UTC datetime -> 422 `invalid_reviewed_at`;
  narrow ValueError -> 422 fallback; no 500/traceback)
- modified files: app/api/routers/review.py; app/review/service.py;
  app/review/protocols.py (additive conflict-error contract);
  app/infrastructure/sqlite/repositories/review.py
- verification: tests/review 53/53 passed (final run evidence
  pytest-review-suite-final.log); fail-closed probes 10/10
  (probe-failclosed.log, PROBE_EXIT=0); zero product writes outside the four
  in-scope files; no tests/migrations/Program Control touched
- findings: repairs/R1-REVIEW-ROBUSTNESS/findings.md
- risk: none reported by worker

## R2 — root test migration-14 reconciliation — DONE (GREEN slice)

- worker: deepseek/deepseek-v4-flash + ultra, PLANNING_DISABLED=1
- verdict: DONE — all assigned root-test findings reconciled
- findings addressed: D1 (test_calf_v08.py rollback chain), D2 (four
  confirmed stale-14 failures), C1 (all rg-verified hard-coded v14 latest
  semantics in root tests); also refreshed the pinned route contract in
  test_v095b_router_contract.py for the five WU1 review routes
- modified files: tests/test_calf_v08.py; tests/test_wave2_migration_v14.py;
  tests/test_v06_configuration_dashboard.py;
  tests/test_snapshot_repository_v03.py; tests/test_v071_reliability_ui.py;
  tests/test_v095b_router_contract.py; tests/test_v095g_facade_contraction.py;
  tests/test_v097b_wu3_target_creation.py
- verification: baseline 5 failed / 33 passed; targeted 110/110;
  Worker-D stale-14 probe set 22/22; adjacent suites 96/96; final rg sweep
  clean (only intentional one-step rollback / v14-era / non-migration
  literals remain); no product file touched
- findings: repairs/R2-ROOT-TESTS-MIGRATION15/findings.md
- risk: none reported by worker

## R3 — tests/review coverage + R1 regression tests — DONE (GREEN slice)

- worker: deepseek/deepseek-v4-flash + ultra, PLANNING_DISABLED=1
- write scope: tests/review/** ONLY (disjoint from R1 product files and R2
  root tests)
- verdict: DONE — all assigned coverage gaps and regression tests delivered
- addresses: inventory C2-C5 closed with real-behavior tests
  (Case B invalid transitions, Case D genuine v14->15 Wave-2 data
  preservation, Case G four-way evidence semantics + "ability" AST scan,
  Case H malformed provenance + API 422 negatives) and R1 regression tests
  (D3-D5, C9 as final 404/409/403/422 behavior, all with no-write checks)
- modified/added files (tests/review only):
  test_scheduler_invalid_transitions.py (new, 10 tests);
  test_review_fail_closed_api.py (new, 14 tests);
  test_migration_15.py (+1); test_semantic_boundaries.py (+1);
  test_models_and_boundaries.py (+3)
- verification: full tests/review suite 82 passed (53 + 29 new);
  real-fsrs transition probe exit 0; ability AST pre-verification;
  git delta limited to tests/review/** + evidence
- findings: repairs/R3-TESTS-REVIEW-COVERAGE/findings.md
- risk: none blocking; two non-blocking observations recorded (raw
  AssertionError for corrupted persisted scheduler state if ever reached at
  API; card_id=None wall-clock id non-determinism documented, not pinned)
- packet: repairs/R3-TESTS-REVIEW-COVERAGE/task-packet.md

## V1 — independent read-only verification — DONE (PASS)

- dispatch order: after R3 completes
- write scope: evidence only under repairs/V1-VERIFIER/ (no product or test
  writes)
- verdict: PASS — all 12 validation-matrix items and all explicit Cases A-I
  verified with direct evidence
- verification: tests/review 82/82; root/shared reconciled surface 206/206;
  independent probes 50/50 (11 fsrs + 15 migration/persistence + 14
  fail-closed API + 10 composition/semantics) + rollback-gate probe, all
  exit 0; git status identical before/after (35 entries)
- report: repairs/V1-VERIFIER/verification-report.md
- blocker: none; three non-blocking observations carried to INT (raw 500
  only for impossible persisted state never written by product path;
  card_id=None unreachable via service; error envelope exposes message text
  not kind)

## Handoff — CREATED

- CORE-WU1-DEPARTMENT-HANDOFF.md / .json written under
  docs/integration/pdw3-wu1-recovery-20260811/
- verdict: DEPARTMENT GREEN (INT gate authority retained; no promotion)
