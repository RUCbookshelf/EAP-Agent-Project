# Worker D Findings — tests / Cases A-I coverage audit (READ-ONLY)

- task_id: PDW3-WU1-DECOMP-RECOVERY__D-TESTS-CASES-AI
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 1
- worker: deepseek/deepseek-v4-flash, ultra, PLANNING_DISABLED=1
- date: 2026-08-11
- worktree: A:\EAP Agent Project\worktrees\shared-core
- branch / HEAD verified: dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
- git status re-verified after all runs: unchanged baseline (13 modified, 15
  untracked entries); no product/Program Control/git writes made by this worker.

## 1. Scope

- All files under `tests/review/` (9 test modules, 53 tests).
- The six modified root test files from git status:
  tests/test_analysis_runs_v04.py, tests/test_calf_v08.py,
  tests/test_composition_root.py, tests/test_diagnostic_calibration_v061.py,
  tests/test_learner_model_v07.py, tests/test_revision_v05.py.
- `app/review/`, `app/api/routers/review.py`, `app/api/main.py` (diff),
  `app/database/migrations.py` (Migration 15 + rollback), `app/version.py`,
  `app/infrastructure/sqlite/repositories/review.py` — read only as needed to
  judge test meaningfulness.
- Read-only probes: two additional root test files that hard-code migration
  version 14 (see section 5, finding D-2), plus stale-14 assertion inventory
  across the whole `tests/` tree.
- Acceptance gate for this epoch: the canonical Cases A-I defined in
  `docs/integration/pdw3-wu1-recovery-20260811/CHECKPOINT-001-PREDISPATCH.md`
  (section 3). The original WU1 goal acceptance list is not present in this
  worktree (Program Control, out of scope); Cases A-I are treated as the
  acceptance gate.

## 2. Files inspected (path:line)

### tests/review (all test modules)

- tests/review/test_migration_15.py:19,38,55,93,98 — fresh apply / idempotence /
  rollback / version single-sourcing / Database.initialize
- tests/review/test_models_and_boundaries.py:62,80,85,94,101,109,118,125,130,137
- tests/review/test_rating_policy.py:9,18,23,28,33,37,45
- tests/review/test_review_composition.py:44,52,100
- tests/review/test_review_repository.py:99,108,116,132,152
- tests/review/test_review_service.py:66,84,110,135,169,199,240,272
- tests/review/test_scheduler_determinism.py:31,42,53,65,76,85,97,102
- tests/review/test_semantic_boundaries.py:39,48,55,84,89
- tests/review/test_wave2_regression.py:36,137

### Modified root tests (diff inspected)

- tests/test_analysis_runs_v04.py:79 — `migration_version() ==
  LATEST_MIGRATION_VERSION`
- tests/test_calf_v08.py:177,188 — version constants; :183-185 — rollback
  chain (FAILING, see finding D-1)
- tests/test_composition_root.py:34 — adds `review_service`,
  `review_repository` to expected service keys
- tests/test_diagnostic_calibration_v061.py:308,329 — version constants
- tests/test_learner_model_v07.py:140 — drops literal `== 14` from the
  equality chain
- tests/test_revision_v05.py:257 — version constant

### Product surfaces (read-only, for meaningfulness)

- app/review/scheduler.py:23,77 — real `fsrs` imports and `Scheduler` use
- app/review/service.py:63-86,132-156,165-176 — fail-closed rating coercion,
  learning-item guard, atomic state-row build
- app/review/models.py:54-58,71-88,117-132,151-158,176-188 — model contracts
- app/review/rating_policy.py:9-38 — versioned conservative rule
- app/database/migrations.py:44 (`LATEST_MIGRATION_VERSION = 15`), 969
  (`_migration_15`), 1123-1132 (one-step rollback gate)
- app/version.py:47 — `PLATFORM_DATABASE_MIGRATION_VERSION = 15`
- app/api/main.py:187-190,225-226,248-250 — composition wiring
- app/infrastructure/sqlite/repositories/review.py:117-133 — ID allocation;
  :204-222 — atomic event+state write

## 3. Tests run (read-only; PYTHONDONTWRITEBYTECODE=1; --basetemp to evidence)

| # | Command | Result | Evidence |
| --- | --- | --- | --- |
| 1 | `.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <ev>\pytest-tmp -q --collect-only tests/review` | 53 tests collected, 0 errors | evidence/collect-review.log |
| 2 | `.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <ev>\pytest-tmp -q tests/review` | **53 passed** in 45.27s | evidence/run-review-suite.log |
| 3 | `.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <ev>\pytest-tmp -q tests/test_analysis_runs_v04.py tests/test_calf_v08.py tests/test_composition_root.py tests/test_diagnostic_calibration_v061.py tests/test_learner_model_v07.py tests/test_revision_v05.py` | **1 failed, 84 passed** in 70.39s | evidence/run-modified-root-tests.log |
| 4 | Probe: `.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <ev>\pytest-tmp -q tests/test_wave2_migration_v14.py tests/test_v06_configuration_dashboard.py` | **4 failed, 18 passed** in 27.09s | evidence/run-stale-14-probes.log |

- Env check: installed `fsrs==6.3.2`, `pydantic==2.13.4` in
  `.venv\Lib\site-packages\fsrs` (verified via importlib.metadata).
- `<ev>` = `docs/integration/pdw3-wu1-recovery-20260811/workers/
  D-TESTS-CASES-AI/evidence/`

## 4. Per-Case A-I coverage matrix

| Case | Status | Evidence (file:test:line) | Notes |
| --- | --- | --- | --- |
| A — real fsrs==6.3.2 integration, version identity, deterministic vectors (next + repeat review) | **Covered** | test_scheduler_determinism.py:31,42,53,65,76 (exact vectors incl. second/repeat review), :85 (identity `library_version == "6.3.2"` from importlib.metadata), :97 (fuzzing rejected), :102 (real Card round trip); test_review_service.py:135 (reconstruction replay through real adapter) | No stubs/mocks anywhere in tests/review (grep confirmed). Adapter imports real `fsrs` (app/review/scheduler.py:23,77) |
| B — rating/state lifecycle across FSRS states; invalid transitions fail closed | **Partial** | test_review_service.py:84 (state advance, `state_before == prior state_after`, next_due change, 2 events); :110 (channels persist, raw SQL `("good","hard","hard")`); test_rating_policy.py:9-45 (resolution incl. tie/never-inflate); test_models_and_boundaries.py:118 (invalid state strings/negative step rejected) | Invalid *transition sequence* through the scheduler is NOT tested (only invalid state values at the model boundary). No test forces e.g. an impossible state/step combination through `adapter.review` |
| C — Migration 15 fresh path | **Covered** | test_migration_15.py:19 (user_version 15, 3 new tables, Migration-14 tables intact), :93 (LATEST==PLATFORM==15), :98 (Database.initialize lands on 15) | Also exercised implicitly by all fresh-DB review fixtures |
| D — Migration 15 existing Wave-2 path (migration-14 DB with data, additive, preserved, idempotent) | **Partial** | test_migration_15.py:38 (idempotent reapply on fresh), :55 (data preserved across rollback 15→14 and reapply — but data inserted *after* reaching 15) | No test seeds a genuine migration-14 DB containing Wave-2 rows (learning_items/writing_tasks with data) and then upgrades to 15 asserting those rows survive. Indirect partial evidence: modified root tests upgrade older-era DBs with data to 15 (test_calf_v08.py:188, test_diagnostic_calibration_v061.py:329) — but that is config/essay data, not Wave-2-era data |
| E — shared SQLite close/reopen persistence, stable identity, separate ReviewEvent evidence | **Covered** | test_review_repository.py:152 (`del` refs, reopen `Database(path)` on same file, events + scheduler state + identity survive) | Real file-backed round trip through the real connection manager |
| F — three rating channels + versioned rating-rule/scheduler provenance | **Covered** | test_review_service.py:110 (distinct raw columns), :135 (rule version, `py-fsrs`/`6.3.2`, parameters, deterministic reconstruction equality); test_models_and_boundaries.py:85; test_rating_policy.py:45 | Provenance includes scheduler parameters + state_before/state_after + scheduling_result (schema at migrations.py:1000-1040) |
| G — evidence separation and semantics (PracticeActivity vs LearningItem vs ReviewEvent; practice vs authentic; observed/inference/recommendation/outcome; no ability/proficiency/learning-gain) | **Partial** | test_models_and_boundaries.py:62,80; test_review_service.py:199 (practice vs authentic statuses distinct on same item); test_semantic_boundaries.py:39,48,55,84,89 (AST scan forbids mastery/proficiency/learning-gain identifiers); test_wave2_regression.py:137 (LearningItem has no FSRS columns) | Four-way observed/inference/recommendation/outcome distinction is only enforced by `extra="forbid"` + absence of such fields; no direct test asserts ReviewEvent/PracticeActivity cannot carry inference/recommendation/outcome semantics. "Ability" tokens are not in the AST scan list (only mastery/proficiency/validated_acquisition/learning_gain) |
| H — fail-closed invalid inputs (ratings, identity, state, provenance) | **Partial** | ratings: test_models_and_boundaries.py:109, test_review_service.py:240-270 (nothing silently written); identity: test_review_service.py:240,272, test_review_composition.py:100 (404); state values: test_models_and_boundaries.py:118; unknown fields: test_models_and_boundaries.py:130 | Missing: malformed provenance is never tested at any layer; invalid state *transitions* untested (see B); no API-layer 422 test for invalid rating/status/provenance (router error mapping at app/api/routers/review.py:127-139, 151-164 is only exercised for the 404 path) |
| I — real composition + Wave-2 compatibility (one root/namespace; no second DB/runtime/registry) | **Covered** | test_review_composition.py:44,52,100 (create_app → same TestClient → /api/v1/review/* round trip; 404 paths); tests/test_composition_root.py:34 (service keys); test_wave2_regression.py:36 (Wave-2 families + review flow on same DB), :137 | Single `Database`, single FastAPI app, review router in `_BUSINESS_ROUTERS` (app/api/main.py:81) |

## 5. A/B/C/D/E findings for the test layer

- **A (complete/coherent):** The tests/review suite is internally coherent and
  green — 53/53 pass. Cases A, C, E, F, I have explicit, meaningful coverage.
  Determinism vectors are exact float/datetime pins recorded from the real
  library, and the identity test asserts the installed version string.
- **B (implemented but unverified):** The full root test suite was NOT run
  (only the six modified files + two probe files); the version gate ("every
  version must run all tests") is therefore unverified for the full suite in
  this audit. Static inventory shows this matters — see D-2.
- **C (incomplete):**
  - Case D: no direct "migration-14 DB with real Wave-2 data → upgrade to 15,
    data preserved" test.
  - Case B: no invalid-transition-sequence test through the scheduler.
  - Case H: malformed-provenance input class untested; no API-level 422
    negative tests for invalid rating/status.
  - Case G: four-way evidence-semantics distinction not asserted directly.
- **D (incorrect / contract-incompatible):**
  - **D-1 (confirmed):** Modified root test
    `tests/test_calf_v08.py::test_migration_10_is_additive_and_logical_rollback_preserves_rows`
    **FAILS** on the preserved partial diff: line 183 `rollback(connection, 13)`
    now starts from user_version 15 (LATEST), and
    `app/database/migrations.py:1123-1132` permits only one-step rollback, so
    the call raises `ValueError: Only non-destructive one-step rollback is
    supported.` The file was updated for LATEST=15 (lines 177, 188) but the
    rollback chain (183-185) was not. On HEAD (LATEST=14) this test passed, so
    the failure is introduced by the partial diff. The change pattern is
    otherwise coherent (constant substitution, additive service keys).
  - **D-2 (confirmed by probe):** Unmodified root tests hard-coding migration
    version 14 now fail against LATEST=15. Probe run: 4 failed / 18 passed in
    `tests/test_wave2_migration_v14.py` (lines 53, 54, 94, 130) and
    `tests/test_v06_configuration_dashboard.py` (line 87). Static inventory of
    at least 5 further affected files: tests/test_snapshot_repository_v03.py:17,32;
    tests/test_v071_reliability_ui.py:272,285; tests/test_v095b_router_contract.py:270;
    tests/test_v095g_facade_contraction.py:228; tests/test_v097b_wu3_target_creation.py:327,341.
    The six-file root-test update was therefore incomplete: the preserved
    partial diff leaves the wider root suite red, which violates the version
    gate ("Every version must run all tests") until the remaining v14
    assertions are reconciled.
- **E (out-of-scope drift):** None identified in the test layer. All
  tests/review files are additive to the preserved WU1 diff; no test touches
  Program Control, other worktrees, or raw SWECCL.

## 6. Answers to the review questions

1. **Which Case A-I has explicit coverage, and where?** See matrix (section 4).
   A/C/E/F/I covered; B/D/G/H partial.
2. **Acceptance-gate requirements untested or superficial?** Case D existing
   Wave-2 data path (no v14→15 data-preservation fixture); Case B invalid
   transitions; Case H malformed provenance + API 422 negatives; Case G
   four-way evidence semantics (superficial — field absence + AST scan only).
3. **Real installed fsrs exercised?** Yes. `app/review/scheduler.py:23,77`
   imports and constructs the real `fsrs` package; venv has `fsrs==6.3.2`;
   tests/review contains no mocks/stubs/monkeypatch; exact vectors and the
   `library_version == "6.3.2"` identity assertion are recorded from the real
   library.
4. **Migration tests: fresh / existing-data / idempotence?** Fresh: yes
   (test_migration_15.py:19,98). Idempotence: yes (:38, and rollback/reapply
   :55). Existing-data: only partially — older-era data via modified root tests,
   not a Wave-2-era (v14) data fixture; the dedicated v14 legacy-upgrade test
   now fails (D-2).
5. **Persistence tests prove close/reopen on the same SQLite file?** Yes —
   test_review_repository.py:152 drops all references, reopens the same path,
   and verifies events, scheduler state, and identity survive.
6. **Negative/fail-closed paths per invalid-input class?** Ratings: model +
   service (H). Identity: service + API 404. State values: model. Unknown
   fields: model. Missing: malformed provenance (all layers), invalid state
   transitions, API-level 422 for invalid rating/status.
7. **Would each test fail if the behavior regressed?** Yes, statically — exact
   vectors, raw-column assertions, schema/table assertions, AST scans, and
   close/reopen checks are all behavior-sensitive. No mutation probes were run
   because product code is protected; meaningfulness was assessed from source.
   Caveat: tests couple to private members (`database._review_repository`,
   `_connection_manager`) — meaningful, but refactor-sensitive.
8. **Do modified root tests change Wave-2 expectations — coherent or
   contract-incompatible?** Pattern is coherent (replace literal 14 with
   LATEST_MIGRATION_VERSION; add review service keys; keep Wave-2 assertions
   intact). One contract-incompatible edit: test_calf_v08.py rollback chain
   (D-1) — the test fails under the preserved one-step rollback rule. The
   broader v14 assertion inventory (D-2) remains unreconciled in unmodified
   root tests.

## 7. Blocker

None for this worker's own delivery (findings + evidence written; no product
files touched). However, the preserved partial diff has a confirmed red test
layer outside tests/review: modified test_calf_v08.py fails (D-1), and at
least 7 unmodified root test files still hard-code migration version 14
(D-2, 4 failures confirmed by probe). This must be reconciled before any
version-gate ("all tests run") claim for the WU1 partial implementation.

## 8. Verdict

**FAIL** (test layer of the preserved partial implementation, as scoped).

Rationale: tests/review itself is complete and green (53/53, strong coverage
for Cases A, C, E, F, I and meaningful partial coverage for B, D, G, H), but
the audit's second requirement — modified/root Wave-2 tests remain coherent —
fails: the six-file root-test update is internally inconsistent
(test_calf_v08.py) and incomplete (at least 7 further root test files
hard-code migration version 14 and now fail). The partial diff does not
satisfy the "every version must run all tests" gate as preserved.
