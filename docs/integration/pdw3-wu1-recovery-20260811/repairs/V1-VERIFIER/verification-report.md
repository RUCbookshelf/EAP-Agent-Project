# V1 Verification Report — CORE WU1 decomposition recovery (independent, read-only)

- task_id: PDW3-WU1-DECOMP-RECOVERY__V1-VERIFIER
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 3
- role: independent verifier (deepseek/deepseek-v4-flash, ultra, PLANNING_DISABLED=1)
- worktree / branch / HEAD: A:\EAP Agent Project\worktrees\shared-core / dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae (verified before and after all runs)
- date: 2026-08-11
- verdict: PASS
- blocker: none

## 1. Scope and method

Read-only verification of the repaired CORE WU1 state against the acceptance
gate and the explicit Cases A-I (CHECKPOINT-001 section 3). No product file,
test file, Program Control file, or git state was changed. Writes are limited
to this report and evidence/ under repairs\V1-VERIFIER\. All commands ran
from the worktree root with PYTHONDONTWRITEBYTECODE=1, -p no:cacheprovider,
and --basetemp under the V1 evidence dir; probes used temp SQLite files under
evidence/ and TestClient with raise_server_exceptions=False.

Durable context read before verification: inventory, REPAIR-STATUS, workers
A-D findings, repairs R1-R3 findings, CHECKPOINT-001 (canonical Cases A-I).

## 2. Commands run (all evidence under repairs\V1-VERIFIER\evidence\)

1. pytest -q --basetemp <ev>\pytest-tmp-review tests/review -> 82 passed (49.32s); evidence v1-review-suite.log
2. pytest -q --basetemp <ev>\pytest-tmp-root <13 modified root tests + test_version_single_sourcing.py + test_v095f2_service_narrowing.py + test_migration_drop_column_rollback_note.py> -> 206 passed (199.10s); evidence v1-root-reconciled-suite.log
3. probe_fsrs_vectors.py -> 11/11, exit 0; evidence v1-probe-fsrs-vectors.log
4. probe_migration_persistence.py <ev> -> 15/15, exit 0; evidence v1-probe-migration-persistence.log
5. probe_failclosed_api.py <ev> -> 14/14, exit 0; evidence v1-probe-failclosed-api.log
6. probe_composition_semantics.py <ev> -> 10/10, exit 0; evidence v1-probe-composition-semantics.log
7. one-step rollback gate probe -> PASS; evidence v1-probe-rollback-gate.log
8. git status --porcelain before vs after all runs -> identical (35 entries); evidence git-status-initial.txt / git-status-final.txt

Note: the four probe scripts print third-party deprecation warnings to stderr;
PowerShell reported exit 1 on some runs while each probe's own SUMMARY line
printed all-PASS and SystemExit(0) was raised. Re-run with stderr discarded
confirmed $LASTEXITCODE = 0 for all four probes.

## 3. Per-item validation matrix

1. Real fsrs==6.3.2 behavior — PASS. importlib.metadata.version("fsrs") ==
   6.3.2; fsrs.__version__ does not exist in 6.3.2 (packet probe nuance
   confirmed). Adapter identity recorded: py-fsrs / 6.3.2 / FSRS with 21
   JSON-safe parameters incl. enable_fuzzing=False, desired_retention=0.9,
   learning_steps=[60,600], relearning_steps=[600], maximum_interval=36500.
   First-Good and second-Good (repeat) vectors computed through the app
   adapter match RAW py-fsrs 6.3.2 computation exactly
   (stability/difficulty/due/step; probe 1). Identity persisted per event
   (item 6). Tests: tests/review/test_scheduler_determinism.py:31,42,85,97,102.
2. Rating/state lifecycle — PASS. Three channels distinct
   (system_provisional_rating, learner_self_rating, final_scheduler_rating),
   conservative-minimum resolution never inflating and always one of the
   inputs (tests/review/test_rating_policy.py:9-45). Lifecycle New ->
   Learning -> Review -> Relearning -> Review executed through the real
   Scheduler.review_card (probe 1); invalid transition vectors (relearning
   step overflow, review-with-residual-step, review-without-history) fail
   closed via the real library (probe 1;
   tests/review/test_scheduler_invalid_transitions.py:106,116,123);
   impossible persisted state fails closed with no write
   (test_scheduler_invalid_transitions.py:193).
3. Migration 15 fresh path — PASS. Empty DB -> upgrade()==15; the 3 review
   tables created alongside Migration-14 tables; ledger exactly 1..15;
   version single-source LATEST_MIGRATION_VERSION ==
   PLATFORM_DATABASE_MIGRATION_VERSION == 15 (probe 2;
   tests/review/test_migration_15.py:20,39,94,99;
   tests/shared/test_version_single_sourcing.py).
4. Migration 15 existing path — PASS. Genuine migration-14 DB built from the
   real MIGRATIONS 1..14 with seeded Wave-2 learning_items / writing_tasks
   rows upgraded via the real upgrade driver: rows byte-identical after
   upgrade (incl. no_fsrs_note / no_practice_note), review tables coexist,
   ledger 1..15, re-upgrade idempotent and data-preserving (probe 2;
   tests/review/test_migration_15.py:130; tests/test_wave2_migration_v14.py:74-110).
   One-step rollback semantics honored: 15->14 ledger-only with tables/data
   preserved; non-adjacent 15->13 raises the documented ValueError
   (rollback-gate probe; tests/test_calf_v08.py:174-189;
   tests/test_v071_reliability_ui.py; tests/test_v097b_wu3_target_creation.py).
5. Shared SQLite close/reopen persistence — PASS. Practice activity, review
   event, and scheduler state written through Database A survive close +
   reopen of the SAME file via Database B; LearningItem identity stable;
   ReviewEvent rows separate from scheduler-state rows (probe 2;
   tests/review/test_review_repository.py:152).
6. Provenance — PASS. Every ReviewEvent persists rating_rule_version
   (rating-rule-v1.0.0), scheduler implementation/version/parameters, and
   state_before/state_after/scheduling_result. Deterministic reconstruction
   proven: replaying the real scheduler on (state_before,
   final_scheduler_rating, reviewed_at) reproduces state_after exactly
   (probe 2; tests/review/test_review_service.py:135).
7. Evidence separation — PASS. PracticeActivity (evidence_kind literal
   "practice", cannot be spoofed) distinct from durable LearningItem v1 (no
   FSRS columns; no_fsrs_note/no_practice_note preserved) and from
   ReviewEvent (durable evidence rows) — probe 2 row inspection;
   tests/review/test_models_and_boundaries.py:62,80;
   tests/review/test_wave2_regression.py:137. Practice vs authentic
   evidence distinguished via authentic_evidence_status
   (test_review_service.py:199; test_semantic_boundaries.py:100).
   observed/inference/recommendation/outcome distinction asserted directly
   (test_models_and_boundaries.py:145,172). No mastery/proficiency/ability/
   learning-gain/score/percentage/CEFR tokens in app/review AST or in live
   API response keys (probe 4 word-boundary scan;
   tests/review/test_semantic_boundaries.py:40,56,86).
8. Fail-closed inputs — PASS. API layer: invalid rating, unknown fields,
   malformed provenance (list), naive and non-UTC reviewed_at, invalid
   authentic_evidence_status -> all 422 with zero writes; nonexistent
   LearningItem -> 404; nonexistent practice_activity_id -> 404 (stable
   service kind practice_activity_not_found) with zero writes; duplicate
   client-supplied PA id -> 409 with the original row intact (provenance
   {batch:1} preserved); duplicate RE id -> stable
   review_event_already_exists conflict with original row intact;
   cross-student event / event linking another student's activity /
   mismatched activity owner -> 403 with no writes (probe 3;
   tests/review/test_review_fail_closed_api.py:118-465;
   test_models_and_boundaries.py:109,118,130,193). No 500/traceback on any
   of these paths.
9. Real composition — PASS. Exactly one ReviewService and one
   FSRSSchedulerAdapter() in the single _build_services builder
   (app/api/main.py:187-190); review router registered exactly once
   (_BUSINESS_ROUTERS); OpenAPI shows exactly 5 review routes and 18 Wave-2
   routes; fsrs imported only in app/review/scheduler.py; no
   threading/socket/uvicorn/event-bus markers in app/review; one SQLite file
   with no ATTACH (probe 4 + probe 2;
   tests/review/test_review_composition.py:44,52,100).
10. Wave-2 compatibility — PASS. R2-reconciled root surface green (206
    passed across the 13 modified root test files + version-single-sourcing
    + adjacent extras; superset of R2's 110 targeted / 22 stale-14 / 96
    adjacent sets); tests/test_v095b_router_contract.py route pin includes
    the 5 review routes (lines 121-123, 195-196); LearningItem v1 contract
    untouched (git diff empty for app/l2, app/learner, app/practice,
    app/feedback, app/api/routers/wave2_modules); no remaining stale
    latest-semantics ==14 assertions in root tests (rg sweep; remaining
    literal-14 hits are intentional one-step-rollback / v14-era
    constructions).
11. Explicit Cases A-I — all covered (matrix in section 4).
12. Resource/scope hygiene — PASS. git status identical before and after all
    runs (35 entries: 20 tracked-modified = 7 product/config + 13 root
    tests, 15 untracked = WU1 review product files, tests/review,
    docs/integration evidence). Product diff limited to the 7 authorized
    files; _migration_14 body untouched in the migrations.py diff (all hunks
    additive). No stray server from this work: the only listening python
    process (127.0.0.1:8766) is the pre-existing codex-dashboard server from
    another workstream; no process references this
    worktree/uvicorn/streamlit/run.bat.

## 4. Cases A-I matrix

| Case | Verdict | Direct evidence (test:file:line / probe) |
| --- | --- | --- |
| A real fsrs==6.3.2, identity, deterministic vectors | PASS | test_scheduler_determinism.py:31,42,53,65,76,85,97,102; probe 1 raw cross-check |
| B rating/state lifecycle; invalid transitions fail closed | PASS | test_review_service.py:66,84,110; test_rating_policy.py:9-45; test_scheduler_invalid_transitions.py:77,91,106,116,123,131,183,193; probe 1 |
| C migration 15 fresh path | PASS | test_migration_15.py:20,39,94,99; probe 2 fresh |
| D migration 15 existing Wave-2 path, preserved, idempotent | PASS | test_migration_15.py:130; test_wave2_migration_v14.py:74-110; probe 2 existing; rollback-gate probe |
| E close/reopen persistence, stable identity, separate events | PASS | test_review_repository.py:152; probe 2 reopen |
| F three rating channels + versioned provenance | PASS | test_review_service.py:110,135; test_rating_policy.py:45; probe 2 reconstruction replay |
| G evidence separation + no mastery/proficiency/ability semantics | PASS | test_models_and_boundaries.py:62,80,145,172; test_semantic_boundaries.py:40,49,56,86,100,105; test_wave2_regression.py:137; probe 2 distinct rows; probe 4 AST + response keys |
| H fail-closed invalid inputs (ratings, identity, state, provenance) | PASS | test_models_and_boundaries.py:109,118,130,193; test_review_fail_closed_api.py:145-465; probe 3 |
| I real composition + Wave-2 compatibility, no second DB/runtime | PASS | test_review_composition.py:44,52,100; tests/test_composition_root.py:34; test_wave2_regression.py:36,137; probe 4 |

## 5. Worktree-hygiene check

- Branch/HEAD verified before and after all runs: dept/shared-core @
  7a9e4b470c41c0453a3795233f1bdd5c483d80ae (matches packet).
- git status --porcelain byte-identical before/after this verification
  (35 entries); the only writes this verifier made are under
  repairs\V1-VERIFIER\ (this report + evidence/).
- No git mutations, no Program Control writes, no product/test edits.
- No stray processes/servers attributable to this work; evidence paths in
  section 6.

## 6. Evidence paths

docs/integration/pdw3-wu1-recovery-20260811/repairs/V1-VERIFIER/evidence/:
v1-review-suite.log; v1-root-reconciled-suite.log; v1-probe-fsrs-vectors.log
(+ probe_fsrs_vectors.py); v1-probe-migration-persistence.log (+
probe_migration_persistence.py); v1-probe-failclosed-api.log (+
probe_failclosed_api.py); v1-probe-composition-semantics.log (+
probe_composition_semantics.py); v1-probe-rollback-gate.log;
git-status-initial.txt; git-status-final.txt; plus probe temp DBs
(fresh15.db, existing14to15.db, reopen.db, failclosed.db, compose.db) and
pytest-tmp-* dirs.

## 7. Blockers / risks

- Blocker: none.
- Risks / observations (non-blocking, behavior confirmed as-is):
  1. An impossible persisted scheduler state (never written by the product
     path, which only persists scheduler-produced states) would surface as a
     raw 500 at the API boundary; behavior documented and asserted
     fail-closed-with-no-write at service level
     (test_scheduler_invalid_transitions.py:193). Later slice/INT gate may
     map it to a stable 4xx (R3 observation, unchanged).
  2. card_id=None (unreachable through ReviewService, which always passes
     the deterministic _stable_card_id) would get a wall-clock id from the
     library; documented, intentionally not pinned (R3 observation,
     unchanged).
  3. The platform error envelope exposes message text rather than the stable
     ReviewError kind string; stable kinds are asserted at service level
     (probe 3; R3 tests). API consumers rely on status codes + message text.
     Not a regression; noted for the INT gate.

## 8. Overall verdict

PASS. All 12 validation-matrix items and all explicit Cases A-I verified
with direct evidence: 82/82 review tests, 206/206 reconciled root/shared
tests, and 50 independent probe checks (11+15+14+10) plus the rollback-gate
probe all green. Fail-closed boundaries (404/409/403/422 with no writes),
migration 15 fresh/existing/idempotent/one-step-rollback paths, close/reopen
persistence, deterministic provenance reconstruction, single composition
root, semantic separation, and worktree hygiene all confirmed. Worker/repair
claims (R1-R3, inventory A-E) match observed behavior; no discrepancy found.
No repair performed.
