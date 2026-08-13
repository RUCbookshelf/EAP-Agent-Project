# PDW3-WU2 LEARNER Migration 16 Option A - Changed Files

Goal: `PDW3-WU2-LEARNER-MIGRATION16-PINS-OPTION-A-20260812`
Run: `PDW3-WU2-LEARNER-MIGRATION16-PINS-OPTION-A-20260812__20260812T045022Z__d2c40f`
Worktree: `A:\EAP Agent Project\worktrees\learner` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`

## 1. Files changed for THIS goal (Option-A ledger, Migration 16, pin repairs)

- `app/database/migrations.py` - LEARNER acknowledgement persistence
  renumbered from the former 15 lane to global Migration 16; CORE-15 seam
  consumed (`GLOBAL_MIGRATION_LEDGER_OWNER` / `GLOBAL_MIGRATION_LEDGER_VERSION_15`
  / `GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME` plus
  `assert_global_migration_15_identity` and `assert_global_migration_16_identity`,
  lines 1177-1258); `LATEST_MIGRATION_VERSION = 16` (line 45); the
  `_migration_15` body is byte-identical to the accepted CORE candidate
  (SHA-256 `67a55c1708d8cccd5f98cffec932eb3649255ba4e6907c0295444528b447a08a`,
  5975 chars on both sides; hash includes the terminal newline).
- `app/version.py` - `PLATFORM_DATABASE_MIGRATION_VERSION: int = 16` (line 42).
- `tests/learner/test_migration_16_option_a_global_ledger.py` - NEW: seven
  Option-A composition tests (identities, uniqueness, fresh 14-15-16,
  genuine v14-era upgrade with Wave-2 row preservation, ledger-only rollback
  16-15-14 with idempotent re-apply, non-adjacent rollback rejection, guard
  drift rejection).
- `tests/test_wave2_migration_v14.py` - rewritten to LATEST=16 semantics:
  fresh-DB ledger rows at 14/15/16, v14-era one-step rollbacks 16-15-14 with
  data preservation, legacy-DB upgrade without history loss, DEFAULT
  coverage; post-rollback literals `== 14` / `== 13` retained (fixture-safe).
- `tests/test_analysis_runs_v04.py` - stale `migration_version() == 14` pin
  replaced with `== LATEST_MIGRATION_VERSION`.
- `tests/test_calf_v08.py` - two stale pins replaced; one-step
  `rollback(connection, 15)` / `rollback(connection, 14)` steps added (CORE
  WU1 R2 form).
- `tests/test_diagnostic_calibration_v061.py` - two stale pins replaced with
  `== LATEST_MIGRATION_VERSION`.
- `tests/test_revision_v05.py` - one stale pin replaced.
- `tests/test_v06_configuration_dashboard.py` - one stale pin replaced.
- `tests/test_v071_reliability_ui.py` - two stale pins replaced; one-step
  rollback steps added (CORE WU1 R2 form).
- `tests/test_v095g_facade_contraction.py` - stale
  `/api/v1/system/version` `database_migration_version == 14` pin replaced.
- `tests/test_v097b_wu3_target_creation.py` - two stale pins replaced;
  one-step rollback steps added (CORE WU1 R2 form).
- `tests/test_learner_model_v07.py` - `== LATEST_MIGRATION_VERSION == 14`
  chain simplified to `== LATEST_MIGRATION_VERSION`.
- `tests/test_snapshot_repository_v03.py` - both `== LATEST_MIGRATION_VERSION
  == 14` chains simplified.
- `docs/integration/pdw3-wu2-learner-migration16-pins-option-a-20260812/`
  - NEW: this handoff package (handoff JSON/MD, changed-files doc, probe
    script/log, three pytest logs).

## 2. Inherited WU2 candidate files preserved untouched by this goal

These pre-existing dirty/untracked files belong to the earlier LEARNER WU2
goals (PRACTICE-REVIEW-TRANSFER / ACK-ROUTES-PERSISTENCE-REPAIR). They were
present at session start, were NOT modified by this goal, and are preserved:

- `app/api/deps.py`, `app/api/main.py`, `app/api/routers/journey.py`,
  `app/api/routers/acknowledgement.py` (untracked)
- `app/infrastructure/sqlite/repositories/__init__.py`,
  `app/infrastructure/sqlite/repositories/acknowledgement.py` (untracked)
- `app/journey/service.py`, `app/journey/transfer.py` (untracked)
- `app/learner/acknowledgement.py`, `app/learner/acknowledgement_contracts.py`,
  `app/learner/review_bridge.py` (untracked), `app/practice/review_transfer.py`
  (untracked)
- `tests/test_composition_root.py` (WU2 service-graph keys, RETRY-2 Worker D)
- `tests/learner/` WU2 tests: acknowledgement, persistence evidence, journey
  routes/history transfer, api composition, practice/review evidence
  (untracked; `test_migration_16_option_a_global_ledger.py` is this goal's
  new file)
- `docs/integration/LEARNER-FOUNDATION-FREEZE-20260809.md`,
  `docs/integration/PDW1-ALIGN-LEARNER-B6FCE9-20260809.md`,
  `docs/integration/PDW2-ALIGN-LEARNER-59500127-20260810.md`,
  `docs/integration/PDW3-ALIGN-LEARNER-7A9E4B-20260811.md` (untracked,
  prior goals)
- `docs/integration/pdw3-wu2-ack-routes-repair-20260812/`,
  `docs/integration/pdw3-wu2-learner-20260812/` (untracked, prior goals)

## 3. Remaining literal ==14 / ==15 sites (intentional, historical-fixture-safe)

Audited live (2026-08-12 continuation run); none are current-version-stale:

- `tests/learner/test_wu2_persistence_evidence.py:348,598` - PRAGMA `== 14`
  after real ledger rollback to the v14 era, and the v14-era fixture built
  with migrations 1..14 only
- `tests/learner/test_migration_16_option_a_global_ledger.py:204-205` -
  `== 15` after real rollback 16-15 (rollback-target assertion)
- `tests/test_calf_v08.py:184`, `tests/test_v071_reliability_ui.py:279`,
  `tests/test_v097b_wu3_target_creation.py:333`,
  `tests/test_wave2_migration_v14.py:99` - `rollback(connection, 14) == 14`
  return-value assertions (v14-era target)
- `tests/test_wave2_migration_v14.py:100` - PRAGMA `== 14` after real
  rollback
- `tests/test_v095b_router_contract.py:270` - self-set manual lifecycle
  envelope (`lifecycle.migration_version = 14` set then asserted;
  fixture-safe per INT adjudication Section 5.2)
- `tests/test_calf_v08.py:59`, `tests/corpus/test_seccl_artifacts.py:96` -
  `== 14` counts of unrelated units/features, not migration assertions
