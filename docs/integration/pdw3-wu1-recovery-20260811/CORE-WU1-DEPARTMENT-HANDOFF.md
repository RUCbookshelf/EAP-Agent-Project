# CORE WU1 DEPARTMENT GREEN HANDOFF — PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811

- handoff_id: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811__20260811T150744Z__ad2fdd
- goal_id: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811
- owner: CORE
- worktree / branch / HEAD: A:\EAP Agent Project\worktrees\shared-core /
  dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
- starting_sha == final_sha: 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
  (no commit created; preserved partial diff + repairs remain the candidate)
- verdict: **DEPARTMENT GREEN** (INT gate authority retained; no promotion)
- returned_at: 2026-08-11T15:59:43Z

## 1. Inherited inventory (Phase 1 read-only decomposition)

Four bounded read-only workers (all deepseek/deepseek-v4-flash + ultra,
PLANNING_DISABLED=1) produced durable findings under
`docs/integration/pdw3-wu1-recovery-20260811/workers/*/`. The coordinator
collected them into the visible inventory
`inventory/A-B-C-D-E-PARTIAL-DIFF-INVENTORY.md` before any repair:

- A COMPLETE/COHERENT: real fsrs 6.3.2 adapter + deterministic vectors;
  three rating channels + versioned provenance; evidence-separation
  contracts; additive Migration 15 + single-source version; close/reopen
  persistence; one composition root; no semantic leakage; 53/53 review
  tests green with Cases A/C/E/F/I covered.
- B IMPLEMENTED BUT UNVERIFIED: full root regression; `fsrs.__version__`
  probe nuance; `app/learning_items/` path N/A; client-asserted system
  rating/authentic evidence; pre-existing TEST-ONLY sqlite3.connect in
  L2/LEARNER wave2 modules.
- C INCOMPLETE: incomplete Wave-2 root-test v14 reconciliation; Case D/B/H/G
  coverage gaps; FK->500 boundary; duplicate-ID overwrite; missing
  ownership binding; ValueError->500 boundary.
- D INCORRECT/CONTRACT-INCOMPATIBLE: test_calf_v08 rollback chain; 4
  confirmed stale-14 root failures; FK 500; duplicate-ID silent overwrite;
  cross-student acceptance.
- E OUT-OF-SCOPE DRIFT: none in product scope; pre-existing TEST-ONLY
  modules and verification nuances flagged.

## 2. Every worker's scope / model / reasoning / files / tests / verdict

### Phase 1 review workers (read-only)

| Worker | Scope | Model/reasoning | Files/tests | Verdict |
| --- | --- | --- | --- | --- |
| A FSRS/scheduler | app/review; learning_items contracts; fsrs pin; scheduler/rating/service tests | deepseek/deepseek-v4-flash, ultra, PLANNING_DISABLED=1 | 23 targeted + 53 full review tests; raw-vector cross-checks; 9 fail-closed probes | PASS |
| B migration/persistence/repository | migrations.py Migration 15; version.py; repository/review.py; connection manager; migration/repo tests | same | 10 migration/repo + 13 version-sourcing tests; 5/5 probes; distinctness probe | PASS |
| C contracts/composition/evidence separation | api/main.py diff; routers/review.py; repositories/__init__.py; review contracts; composition/semantic/wave2 tests | same | 10 required + 47 extended tests; 21-check composition probe; edge probes | PASS_WITH_CONCERNS |
| D tests/Cases A-I coverage | tests/review + modified root tests + stale-14 inventory | same | 53/53 review; 1 failed + 84 passed modified roots; 4 failed + 18 passed stale-14 probe | FAIL (test layer) |

### Phase 2 repair workers (bounded slices, disjoint files)

| Slice | Scope (files owned) | Model/reasoning | Tests | Verdict |
| --- | --- | --- | --- | --- |
| R1 review robustness | app/api/routers/review.py; app/review/service.py; app/review/protocols.py; app/infrastructure/sqlite/repositories/review.py | deepseek/deepseek-v4-flash, ultra, PLANNING_DISABLED=1 | 53/53 review retained; 10/10 fail-closed probes | DONE |
| R2 root test reconciliation | 8 root test files (+ all rg-verified v14 hardcodes), tests/ excluding tests/review/ | same | 110/110 targeted; 22/22 stale-14; 96/96 adjacent; rg sweep clean | DONE |
| R3 tests/review coverage | tests/review/** only | same | 82/82 (53 + 29 new) | DONE |

### Phase 3 verifier

| V1 independent read-only verifier | evidence only | deepseek/deepseek-v4-flash, ultra, PLANNING_DISABLED=1 | 82/82 review; 206/206 root/shared; 50/50 independent probes + rollback-gate probe; git status identical (35/35) | PASS |

## 3. Final implementation state

The preserved partial diff plus R1-R3 repairs, uncommitted in the authorized
worktree:

- Product (7 tracked-modified + untracked review package):
  app/api/main.py, app/database/migrations.py (Migration 15 additive only),
  app/database/repository.py,
  app/infrastructure/sqlite/repositories/__init__.py, app/version.py,
  pyproject.toml (fsrs==6.3.2), uv.lock, app/api/routers/review.py,
  app/infrastructure/sqlite/repositories/review.py, app/review/**.
- Tests: 13 root test files reconciled + tests/review/** (11 modules, 82
  tests).
- Evidence: docs/integration/pdw3-wu1-recovery-20260811/** (checkpoint,
  inventory, repair status, worker/repair/verifier findings, this handoff).

## 4. FSRS

Real installed fsrs==6.3.2 (importlib.metadata; `fsrs.__version__` does not
exist in 6.3.2). Adapter identity py-fsrs/6.3.2/FSRS with 21 JSON-safe
parameters, fuzzing forced off. First/repeat review vectors match raw
library computation exactly. Rating space again/hard/good/easy == fsrs
ordinals 1-4. State machine New -> Learning -> Review -> Relearning
executed by the real Scheduler.review_card; invalid transition vectors and
impossible persisted states fail closed with no write.

## 5. Migration 15

Strictly additive after Migration 14 (3 tables + 5 indexes, no ALTER/DROP;
`_migration_14` body untouched). Fresh path -> 15; genuine migration-14 DB
with Wave-2 learning_items/writing_tasks -> 15 with byte-identical rows;
re-upgrade idempotent; one-step ledger-only rollback (15->14) preserved
with data; non-adjacent rollback raises the documented ValueError.
Version single-source: LATEST == PLATFORM_DATABASE_MIGRATION_VERSION == 15.

## 6. Persistence

Practice activity, review event, and scheduler state survive close + reopen
of the SAME SQLite file with stable LearningItem identity; ReviewEvent rows
separate from scheduler-state rows; LearningItem v1 keeps its no-FSRS
contract; one SQLite file, no ATTACH, no second engine.

## 7. Cases A-I

All PASS per V1 matrix (section 4 of verification-report.md): A real fsrs
6.3.2 + deterministic vectors; B rating/state lifecycle + invalid
transitions fail closed; C migration 15 fresh; D migration 15 existing
Wave-2 path preserved/idempotent; E close/reopen persistence; F three
channels + versioned provenance with deterministic reconstruction; G
evidence separation + no mastery/proficiency/ability semantics; H
fail-closed inputs (404/409/403/422 with zero writes); I real composition +
Wave-2 compatibility, no second DB/runtime.

## 8. Wave-2 regression

206/206 on the reconciled root/shared surface (13 modified root test files +
version single-sourcing + service-narrowing + drop-column note). Route
contract pin includes the 5 review routes; 18 Wave-2 routes coexist;
LearningItem v1 contract untouched. No remaining stale latest-semantics
`==14` assertions in root tests.

## 9. Semantic safety

PracticeActivity evidence_kind literal "practice" (not spoofable);
observed/inference/recommendation/outcome distinction asserted directly;
scheduling state never named as proficiency/mastery/ability/learning gain;
AST + live API response-key scans clean.

## 10. Risks / observations (non-blocking, for INT)

1. Impossible persisted scheduler state (never written by the product
   path) would surface as raw 500 if ever reached at the API boundary;
   service-level fail-closed-with-no-write asserted.
2. `card_id=None` wall-clock id non-determinism is unreachable through
   ReviewService (always uses deterministic `_stable_card_id`).
3. Platform error envelope exposes message text rather than the stable
   ReviewError kind string; kinds asserted at service level.
4. Pre-existing TEST-ONLY direct sqlite3.connect in L2/LEARNER wave2
   modules remains outside the composition root (INT gate re-confirm).

## 11. Resource hygiene

All workers/verifier ran bounded and terminated; no stray processes or
servers attributable to this work; git status identical before/after V1
(35 entries); no commit/push/PR/merge/promotion; no Program Control writes;
no raw SWECCL access; no other worktree touched.

## 12. Gate conclusion

DEPARTMENT GREEN candidate for the consolidated INT Wave-3 integration
gate. INT retains gate authority; promotion is not eligible under this
goal. LEARNER/L2/UX Wave-3 implementation remains gated.

