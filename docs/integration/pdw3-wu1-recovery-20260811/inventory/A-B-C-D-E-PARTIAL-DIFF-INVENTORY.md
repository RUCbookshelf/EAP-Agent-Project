# CORE WU1 PARTIAL-DIFF INVENTORY (A/B/C/D/E)

- inventory_id: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811__INV-001
- created_at: 2026-08-11 (local; epoch 2026-08-11T15:07:44Z run)
- goal_id: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811
- owner: CORE coordinator
- worktree / branch / HEAD: A:\EAP Agent Project\worktrees\shared-core /
  dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
- basis: four durable Phase-1 review findings (workers A-D) + raw evidence
  logs under `docs/integration/pdw3-wu1-recovery-20260811/workers/*/`
- status: INVENTORY COMPLETE — Phase 2 bounded repair authorized below

## Review-worker summary

| Worker | Scope | Tests/evidence | Verdict |
| --- | --- | --- | --- |
| A FSRS/scheduler | app/review scheduler/rating/service/models; real fsrs==6.3.2 API; determinism; provenance; fail-closed | 23 targeted + 53 full review; raw-library vector cross-checks; 9 fail-closed probes | PASS |
| B migration/persistence/repository | Migration 15 additive/version; fresh/existing/idempotent; close/reopen; single file; protocol boundary | 10 migration+repo tests, 13 version-sourcing tests, 5/5 probes, distinctness probe | PASS |
| C contracts/composition/evidence separation | composition root; rating channels; evidence separation; fail-closed API; Wave-2 compatibility | 10 required + 47 extended tests; 21-check composition probe; edge probes | PASS_WITH_CONCERNS |
| D tests/Cases A-I coverage | tests/review + modified root tests + stale-14 inventory | 53/53 review; 1 failed + 84 passed modified roots; 4 failed + 18 passed stale-14 probe | FAIL (test layer) |

All four workers ran as deepseek/deepseek-v4-flash + ultra with
PLANNING_DISABLED=1, wrote only inside their worker evidence directories, and
verified zero product/Program-Control/git mutation. Worker C's first dispatch
was BLOCKED by the Windows sandbox helper (durable `final-message.txt`); its
single bounded retry completed successfully.

## A — COMPLETE / COHERENT

- A1. Real fsrs==6.3.2 integration: adapter uses `Scheduler.review_card`
  with real `Card`/`Rating`; signature-verified; fuzzing forced off;
  deterministic vectors exactly match raw library computation (next + repeat
  review) [A findings A1-A3/A8; evidence 02/03].
- A2. Rating/state lifecycle core: New -> Learning -> Review -> Relearning
  executed through the real scheduler with correct 4-level mapping and
  ordinal parity [A A3; D matrix A/B].
- A3. Three rating channels + provenance: `ReviewEvent` keeps system
  provisional / learner self / final scheduler ratings separate; versioned
  `rating-rule-v1.0.0` + scheduler identity/parameters + state_before/after
  persisted; deterministic reconstruction proven [A A4-A5; C B; D matrix F].
- A4. Evidence separation in contracts: PracticeActivity (evidence_kind
  literal "practice") vs durable LearningItem v1 (no-FSRS/no-practice
  contract preserved) vs ReviewEvent; scheduler state kept outside
  LearningItem v1 [A A7; B E4-E5; C C].
- A5. Migration 15 strictly additive after Migration 14 (3 tables, 5
  indexes, no ALTER/DROP on existing tables; `_migration_14` byte-identical
  to HEAD); version single-source LATEST==app/version.py==15; fresh,
  existing-14-with-data, idempotent, close/reopen, single-file all proven
  [B E1-E7, tests/probes].
- A6. One composition root / API namespace: `ReviewService` +
  `FSRSSchedulerAdapter` constructed once; 5 review routes registered once;
  18 Wave-2 routes coexist; no second runtime/database/registry/event bus
  [A A8; C A/E].
- A7. No semantic leakage: field/AST/API-response scans clean of
  mastery/proficiency/learning-gain/score/percentage/CEFR/CET [A A7; C E;
  D matrix G].
- A8. tests/review suite green and meaningful: 53/53; Cases A, C, E, F, I
  explicitly covered with real library, exact vectors, raw-column and
  close/reopen assertions; no mocks/stubs [D sections 3-4].

## B — IMPLEMENTED BUT UNVERIFIED

- B1. Full root regression not run in Phase 1; known red items make the
  full suite unverified as a set (see C1/D2) [D B].
- B2. `fsrs.__version__` does not exist in fsrs 6.3.2 (packet probe nuance);
  authoritative version via `importlib.metadata` = 6.3.2 [A B2].
- B3. `app/learning_items/` does not exist in this worktree; packet scope
  item maps to `LearningItemReaderProtocol` + Wave-2 repository (no
  functional gap found) [A C1].
- B4. System provisional rating and `authentic_evidence_status` are
  client-asserted (WU1 has no server-side evaluator/authentic-evidence
  source); attribution only via provenance; defaults fail closed [C
  observation].
- B5. Pre-existing TEST-ONLY direct `sqlite3.connect` in
  `app/l2/wave2/sqlite_repository.py:70` and
  `app/learner/wave2/sqlite_repository.py:68` predate WU1, are not wired
  into the composition root; INT gate should re-confirm they stay out [B D1].

## C — INCOMPLETE

- C1. Wave-2 root-test reconciliation incomplete: the six modified root test
  files were updated to LATEST=15, but at least seven further root test
  files still hard-code migration version 14
  (test_wave2_migration_v14.py, test_v06_configuration_dashboard.py,
  test_snapshot_repository_v03.py, test_v071_reliability_ui.py,
  test_v095b_router_contract.py, test_v095g_facade_contraction.py,
  test_v097b_wu3_target_creation.py) [D D-2].
- C2. Case D coverage gap: no dedicated test upgrades a genuine migration-14
  DB containing Wave-2 rows (learning_items/writing_tasks) to 15 and
  asserts preservation [D C].
- C3. Case B coverage gap: invalid transition sequences through the real
  scheduler are not tested (only invalid state values at model boundary)
  [D C].
- C4. Case H coverage gaps: malformed provenance untested at any layer; no
  API-layer 422 negatives for invalid rating/authentic-evidence status
  [D C].
- C5. Case G coverage gap: four-way observed/inference/recommendation/outcome
  distinction not asserted directly; "ability" token absent from AST scan
  list [D C].
- C6. FK failure boundary: review with nonexistent `practice_activity_id`
  dies in the repository as unhandled `sqlite3.IntegrityError` -> HTTP 500
  (write correctly rejected atomically, but boundary not clean) [C D1;
  A E2 analog for non-ReviewError].
- C7. Duplicate-ID semantics: `save_practice_activity` (and `review_events`
  path) use `INSERT OR REPLACE`; client-supplied duplicate activity ID
  silently overwrites durable evidence [C D3; A E1].
- C8. Ownership binding: `_require_learning_item` checks existence only;
  cross-student review events and cross-student practice-activity links are
  accepted (200) [C D2].
- C9. Router maps only `ReviewError`; a naive/non-UTC `reviewed_at` (or other
  raw `ValueError`) surfaces as 500 rather than 4xx [A E2; C D minor].

## D — INCORRECT / CONTRACT-INCOMPATIBLE

- D1. `tests/test_calf_v08.py::test_migration_10_is_additive_and_logical_rollback_preserves_rows`
  FAILS on the preserved diff: `rollback(connection, 13)` now starts from
  user_version 15 and the one-step rollback rule raises `ValueError`; the
  file's version constants were updated but the rollback chain was not.
  Passed on HEAD (LATEST=14); failure introduced by the partial diff [D D-1].
- D2. Confirmed red unmodified root tests (probe: 4 failed / 18 passed):
  tests/test_wave2_migration_v14.py (3 failures: fresh DB now reaches 15,
  rollback 14->13 one-step chain, legacy upgrade lands on 15) and
  tests/test_v06_configuration_dashboard.py (1 failure: `assert 15 == 14`)
  [D D-2].
- D3. Confirmed behavior: nonexistent `practice_activity_id` -> unhandled
  `sqlite3.IntegrityError` -> HTTP 500 `backend_processing_error` with
  traceback instead of mapped 4xx [C D1].
- D4. Confirmed behavior: duplicate client-supplied `PA-DUP` activity ID ->
  second write silently replaces the prior durable row (provenance {batch:1}
  -> {batch:2}, 1 row remains) [C D3].
- D5. Confirmed behavior: S2 can record review events against S1's
  LearningItem, and events can link another student's practice activity;
  both accepted (200) — no student/ownership identity binding [C D2].

## E — OUT-OF-SCOPE DRIFT

- E1. No out-of-scope product code found in the WU1 partial diff (no
  LEARNER/L2/UX implementation, no Academic/Corpus/Campaign content, no
  second runtime/database, no Program Control edits, no raw SWECCL access)
  [A/B/C/D E sections].
- E2. Pre-existing TEST-ONLY sqlite3.connect modules (B5) are not WU1 drift
  but must remain composition-root-external at the INT gate.
- E3. `app/learning_items/` scope item mapped to Wave-2 repository contracts
  (N/A, not drift) [A C1].
- E4. Client-asserted system-provisional rating / authentic-evidence status
  is a WU1 boundary note for future LEARNER/L2 server-side sources; not a
  contract violation while provenance is recorded [C observation].
- E5. Verification-script nuance: use `importlib.metadata.version("fsrs")`,
  not `fsrs.__version__` [A B2].

## Repair decomposition (Phase 2, disjoint slices, serialized overlap)

No monolithic whole-WU1 repair. Ownership and file sets:

| Slice | Files owned | Findings addressed | Order |
| --- | --- | --- | --- |
| R1 review robustness/fail-closed | app/api/routers/review.py; app/review/service.py; app/review/protocols.py (only if contract change required); app/infrastructure/sqlite/repositories/review.py | D3 (FK->4xx), D4 (reject duplicate IDs, append-only evidence), D5 (student/ownership binding), C9 (ValueError->4xx) | First (product-only) |
| R2 root test migration-14 reconciliation | tests/*.py EXCLUDING tests/review/ (test_calf_v08.py, test_wave2_migration_v14.py, test_v06_configuration_dashboard.py, test_snapshot_repository_v03.py, test_v071_reliability_ui.py, test_v095b_router_contract.py, test_v095g_facade_contraction.py, test_v097b_wu3_target_creation.py + any other rg-verified hard-coded v14) | D1, D2, C1 | Parallel with R1 (disjoint files) |
| R3 tests/review coverage + regression | tests/review/*.py only | C2-C5 + regression tests for R1 behavior (D3-D5, C9) | After R1 (depends on final product behavior) |
| V1 independent read-only verifier | evidence only (docs/integration/.../verification/) | validates final state vs acceptance gate + Cases A-I | After R1/R2/R3 |

Shared-file serialization: R1 and R3 both touch tests/review indirectly only
through test runs, never the same write files; R3 writes only tests/review,
R1 writes only product files. R2 writes only root tests. No two slices write
the same file. Each repair worker returns scope/files/tests/verdict evidence;
failed slices get at most one bounded retry; sibling outputs are preserved.

## Gate notes

- Phase 1 read-only audits: complete (4/4 durable).
- Repair may begin: authorized by this inventory.
- No commit, push, PR, merge, promotion; no Program Control writes; no
  LEARNER/L2/UX/INT work before a valid CORE DEPARTMENT GREEN handoff.

