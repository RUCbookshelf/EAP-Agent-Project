# Repair R3 findings — tests/review coverage + R1 regression tests

- task_id: PDW3-WU1-DECOMP-RECOVERY__R3-TESTS-REVIEW-COVERAGE
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 2
- status: DONE
- worktree / branch / HEAD: `A:\EAP Agent Project\worktrees\shared-core` / `dept/shared-core` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- date: 2026-08-11
- R1 dependency: read first (final-message.txt + findings.md + probe evidence); all regression tests assert the R1 final behavior (404/409/403/422 kinds, append-only evidence, owner binding, UTC boundary).

## Changes (tests/review only; no product code, no Program Control, no git state, no files outside the repair boundary)

### Added

1. `tests/review/test_scheduler_invalid_transitions.py` — Case B coverage (inventory C3). Real-library vectors recorded from `fsrs==6.3.2` (see `evidence/probe-real-fsrs-transitions.log`), identity pinned in `test_scheduler_identity_is_pinned` (:66), tolerated vectors pinned exactly, scheduler-impossible vectors (relearning step overflow, review state with residual step, review state without history) asserted to fail closed via the real library, plus one end-to-end no-write test through a corrupted persisted state row (:193).
2. `tests/review/test_review_fail_closed_api.py` — R1 regression tests for D3/D4/D5/C9 plus Case H API-layer 422 negatives, all through the real composition (TestClient, `raise_server_exceptions=False`, real SQLite).

### Modified

3. `tests/review/test_migration_15.py` — added `test_v14_era_wave2_data_survives_upgrade_to_15` (:130, Case D / C2): a genuine migration-14 database (real `MIGRATIONS` 1..14 applied, no review tables yet) is seeded with `learning_items` / `writing_tasks` rows, then upgraded through the real `upgrade` driver; rows and review table families coexist, ledger covers 1..15, re-upgrade idempotent.
4. `tests/review/test_semantic_boundaries.py` — AST scan extended with the `ability` exact token (verified first: no identifier in `app/review` carries it; the only substring hits are `stability`, so the new `test_no_ability_word_in_model_field_names` (:86) uses word-boundary matching, never substring). Case G / C5.
5. `tests/review/test_models_and_boundaries.py` — four-way evidence-semantics distinction asserted directly for ReviewEvent (:145) and PracticeActivity (:172) (no inference/recommendation/outcome fields; `extra="forbid"` rejects payload fields), and malformed-provenance rejection at the model boundary (:193). Case G + Case H / C4-C5.

## Inventory C2-C5 coverage map (file:test:line)

| Inventory item | Coverage | Reference |
| --- | --- | --- |
| C2 Case D v14-era Wave-2 data preservation | genuine v14 DB (real migrations 1-14) + seeded learning_items/writing_tasks + real upgrade to 15; rows and review tables coexist | test_migration_15.py::test_v14_era_wave2_data_survives_upgrade_to_15:130 |
| C3 Case B invalid transitions through real scheduler | 9 real-library vector tests + model-boundary rejection + no-write corrupted-state path; identity/version pinned | test_scheduler_invalid_transitions.py:66,77,91,106,116,123,131,146,183,193 |
| C4 Case H malformed provenance + API 422 negatives | provenance list/string rejected at model + API (no write); invalid rating, invalid authentic_evidence_status, unknown fields, garbage/naive/non-UTC datetimes -> 422 no write | test_models_and_boundaries.py:193; test_review_fail_closed_api.py:352,364,376,394,406,432 |
| C5 Case G four-way semantics + ability tokens | direct field-set + rejection assertions; AST scan includes `ability`; word-boundary field check | test_models_and_boundaries.py:145,172; test_semantic_boundaries.py:56,86 |

## R1 regression coverage (D3-D5, C9) — asserts the real final behavior

- D3 nonexistent `practice_activity_id` -> 404 `practice_activity_not_found`, zero rows written: test_review_fail_closed_api.py:145.
- D4 duplicate PA id -> 409 `practice_activity_already_exists`, original row intact (provenance batch 1): :175; duplicate RE id -> stable `review_event_already_exists` conflict, original row intact: :216.
- D5 cross-student event -> 403 `learning_item_owner_mismatch`, no write: :242; event linking another student's activity -> 403 `practice_activity_owner_mismatch`, no write: :268; mismatched activity owner -> 403, no write: :308.
- C9 naive / non-UTC `reviewed_at` -> 422, no write (router boundary): :352, :364; service-level stable kind `invalid_reviewed_at`: :465.
- Happy path unchanged (200, three rating channels, provenance, one row in each table): :118.

## Verification

- Packet command (cwd = worktree root, `PYTHONDONTWRITEBYTECODE=1`): `.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <evidence>\pytest-tmp -q tests/review` -> **82 passed, 0 failed** (53 pre-existing + 29 added; 2 third-party warnings). Log: `evidence/pytest-review-suite.log`.
- Real-fsrs transition probe (source of pinned vectors): `evidence/probe-real-fsrs-transitions.py` / `.log` — exit 0; records `library_version=6.3.2`, learning_steps [60,600], relearning_steps [600], 9 accepted/rejected vectors, 3 model rejections, adapter KeyError misuse path.
- Ability AST-scan verification (before adding the token): `evidence/probe-ability-ast.log` — PASS with `ability` in the forbidden set; only substring hits are `stability` (word-boundary matching used in the committed test).
- Pydantic/API behavior probes (model provenance list/str -> ValidationError; API provenance list, rating excellent, status proven, unknown fields, garbage/naive datetimes, PA status done -> all 422) confirmed before writing the assertions.
- git status re-verified after all runs: identical to the pre-dispatch baseline (13 modified + untracked entries unchanged); delta limited to `tests/review/**` and this repair directory; HEAD unchanged.

## Blockers or risks

- 无 (no product files touched; no test asserted the old permissive behavior, so no existing test had to change; R1's contract changes are asserted as the new final behavior).
- Observation (not a blocker): scheduler-impossible persisted state vectors raise the real library's `AssertionError` through the service and write nothing, but that raw error is not a stable `ReviewError` kind at the API boundary (would surface as 500 if it ever reached a router). R3 is test-only and records the behavior (`test_impossible_persisted_state_fails_closed_with_no_write`); converting it to a stable 4xx would be a product change for a later slice/INT gate decision.
- Observation: `card_id=None` is assigned a wall-clock-derived id by the real library, so it is non-deterministic; it is documented in the probe but intentionally not pinned in the committed tests.
