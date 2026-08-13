# CORE WU1 Decomposition Recovery — Checkpoint 001 (pre-dispatch)

- checkpoint_id: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811__CP-001
- created_at: 2026-08-11T15:25:00+08:00 (approx, local)
- goal_id: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811
- coordinator_run: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811__20260811T150744Z__ad2fdd
- owner: CORE
- worktree: A:\EAP Agent Project\worktrees\shared-core
- branch / HEAD: dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae

## 1. Have review workers A-D been dispatched?

**NOT YET.** Phase 1 is in pre-dispatch. Preflight is GREEN (worktree, branch,
HEAD, preserved partial diff, Program Control records, dispatch mechanism, and
model route all verified). No product repair has begun and no product file has
been modified by this coordinator run.

## 2. Dispatch plan (bounded read-only workers, all parallel)

| Worker | Bounded read scope | Model / reasoning | Planning | Durable output |
| --- | --- | --- | --- | --- |
| A FSRS/scheduler | app/review scheduler/rating/service/models; app/learning_items scheduling contracts; pyproject.toml + uv.lock fsrs entry; tests/review scheduler/rating/service tests; real installed fsrs==6.3.2 API | deepseek/deepseek-v4-flash + ultra | PLANNING_DISABLED=1 | workers/A-FSRS-SCHEDULER/findings.md |
| B Migration 15/persistence/repository | app/database/migrations.py (Migration 15 only), app/version.py, app/database/repository.py, app/infrastructure/sqlite/repositories, tests/review migration/repository tests | deepseek/deepseek-v4-flash + ultra | PLANNING_DISABLED=1 | workers/B-MIGRATION-PERSISTENCE/findings.md |
| C contracts/composition/evidence separation | app/api/main.py diff, app/api/routers/review.py, app/infrastructure/sqlite/repositories/__init__.py, app/practice, app/learning_items, tests/review composition/semantic/wave2 tests, modified Wave-2 test files | deepseek/deepseek-v4-flash + ultra | PLANNING_DISABLED=1 | workers/C-CONTRACTS-COMPOSITION-EVIDENCE/findings.md |
| D tests/Case A-I coverage | all tests/review/*.py plus modified root tests; coverage against explicit Cases A-I (defined below) | deepseek/deepseek-v4-flash + ultra | PLANNING_DISABLED=1 | workers/D-TESTS-CASES-AI/findings.md |

Each worker returns: scope, files inspected, tests run, A/B/C/D/E findings,
blocker, verdict. Workers must not repair product code.

## 3. Explicit Cases A-I (canonical for this epoch)

- Case A: Real installed fsrs==6.3.2 integration — scheduler uses the real
  package API with version identity and deterministic vectors (next review,
  repeat review).
- Case B: Rating/state lifecycle — system provisional, learner self, and final
  scheduler ratings flow correctly across FSRS states; invalid transitions
  fail closed.
- Case C: Migration 15 fresh path — a brand-new database reaches migration 15
  additively after Migration 14; schema and version contract consistent.
- Case D: Migration 15 existing Wave-2 path — a migration-14 database with
  real Wave-2 LearningItem/practice data upgrades additively with data
  preserved; migration idempotence verified.
- Case E: Shared SQLite close/reopen persistence — review/scheduling rows
  survive connection close/reopen from the same database file with stable
  LearningItem identity and separate ReviewEvent evidence.
- Case F: Three rating channels + provenance — system provisional, learner
  self, and final scheduler ratings recorded distinctly with versioned
  rating-rule/scheduler provenance.
- Case G: Evidence separation and semantics — PracticeActivity distinct from
  durable LearningItem; practice evidence distinct from authentic writing
  evidence; observed evidence != diagnostic inference != feedback
  recommendation != learning outcome; FSRS state is never proficiency/mastery/
  ability/learning gain.
- Case H: Fail-closed invalid inputs — invalid ratings, unknown item identity,
  invalid state transitions, and malformed provenance are rejected explicitly.
- Case I: Real composition + Wave-2 compatibility — one composition root / API
  namespace wires review router, repositories, and services; existing Wave-2
  endpoints and tests remain compatible; no second database/runtime/registry.

## 4. Objective liveness

- State: RUNNING — Phase 1 read-only decomposition, pre-dispatch.
- Product writes: none. Program Control writes: none. Git mutations: none.
- Protected state: full preserved partial diff intact (13 modified, 16
  untracked entries observed at dispatch check).
- Healthy-worker policy: bounded workers are allowed to finish; no wall-time
  kills; genuine failure reconciles only that slice with at most one retry.

## 5. Next evidence artifact

1. Four worker findings files (paths above) — durable structured audits.
2. `inventory/A-B-C-D-E-PARTIAL-DIFF-INVENTORY.md` — visible CORE WU1 partial-
   diff inventory with categories A COMPLETE/COHERENT, B IMPLEMENTED BUT
   UNVERIFIED, C INCOMPLETE, D INCORRECT/CONTRACT-INCOMPATIBLE, E OUT-OF-SCOPE
   DRIFT.
3. Only after the inventory: disjoint bounded repair packets, then an
   independent read-only verifier, then the canonical CORE handoff.

