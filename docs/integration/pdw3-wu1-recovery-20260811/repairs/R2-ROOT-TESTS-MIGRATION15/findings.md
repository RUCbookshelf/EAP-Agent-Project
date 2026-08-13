# Repair R2 findings — root test migration-14 reconciliation

- task_id: PDW3-WU1-DECOMP-RECOVERY__R2-ROOT-TESTS-MIGRATION15
- worker: repair worker R2 (deepseek-v4-flash, PLANNING_DISABLED=1)
- date: 2026-08-11
- worktree: A:\EAP Agent Project\worktrees\shared-core
- branch / HEAD: dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
- findings addressed: inventory D1, D2, C1

## Status

DONE. All 8 in-scope root test files reconciled to LATEST=15 and green;
Worker D probe set green; no product, tests/review, Program Control, or git
state changes.

## Changes (test files only)

1. tests/test_calf_v08.py — `test_migration_10_is_additive_and_logical_rollback_preserves_rows`
   rollback chain extended with the one-step 15->14 step before 14->13->12->11
   (D1; intent preserved: additive tables, rollback to 11, config-v0.8.2
   active, re-upgrade to LATEST restores config-v0.9.0).
2. tests/test_wave2_migration_v14.py — fresh-DB test now asserts
   LATEST_MIGRATION_VERSION and both migration-14 and migration-15 ledger
   entries; rollback test constructs a genuine migration-14-era database
   (rollback 15->14, seed Wave-2 rows at 14), proves 14->13 one-step
   ledger-only rollback preserves tables/data, and re-applies 13->14->15 with
   data preserved; legacy test asserts LATEST with history preserved (D2).
3. tests/test_v06_configuration_dashboard.py — `migration_version() == 14`
   -> `== LATEST_MIGRATION_VERSION` (D2).
4. tests/test_snapshot_repository_v03.py — both
   `migration_version() == LATEST_MIGRATION_VERSION == 14` chains collapsed to
   `== LATEST_MIGRATION_VERSION` (D2).
5. tests/test_v071_reliability_ui.py — user_version assertion and final
   `upgrade(connection)` use LATEST_MIGRATION_VERSION; rollback chain gains
   the one-step 15->14 step (D2).
6. tests/test_v095b_router_contract.py — lifecycle.migration_version and
   health-body assertion use LATEST_MIGRATION_VERSION; pinned
   EXPECTED_ROUTE_CONTRACT extended with the five Wave-3 WU1 review routes
   present in create_app (secondary breakage found while running the file:
   route pin had not been refreshed for the preserved review router).
7. tests/test_v095g_facade_contraction.py — version-endpoint assertion uses
   LATEST_MIGRATION_VERSION (D2).
8. tests/test_v097b_wu3_target_creation.py — two `upgrade(connection)`
   assertions use LATEST_MIGRATION_VERSION; rollback chain gains the one-step
   15->14 step before 14->13->12 (D2).

No mocks of migration behavior; no assertions weakened. Latest-semantics
assertions use LATEST_MIGRATION_VERSION; v14-specific scenarios construct a
migration-14-era DB via the product one-step rollback (15->14), which is the
product-supported path.

## Verification

All runs use `.venv\Scripts\python.exe -m pytest -p no:cacheprovider`,
`PYTHONDONTWRITEBYTECODE=1`, basetemp under this repair directory.

| Run | Result | Evidence |
| --- | --- | --- |
| Baseline (3 failing files, pre-change) | 5 failed / 33 passed | evidence/baseline-targeted.log |
| All 8 touched files | 110 passed | evidence/run-targeted.log |
| Worker D stale-14 probe set (test_wave2_migration_v14.py + test_v06_configuration_dashboard.py) | 22 passed | evidence/run-stale-14-probes.log |
| Adjacent suites (six pre-updated root files + test_version_single_sourcing.py + test_v095f2_service_narrowing.py + test_migration_drop_column_rollback_note.py) | 96 passed | evidence/run-adjacent-suites.log |

## Stale-14 sweep

`rg` over tests/ (excluding tests/review/) finds no remaining hard-coded
migration-14 latest-semantics expectations. Remaining literal-14 hits are
intentional: one-step 15->14 rollback steps, the v14-era DB construction
assertions in test_wave2_migration_v14.py, the migration-14 ledger-name
checks, non-migration counts (CALF units, corpus features), and historical
documentation (test_migration_drop_column_rollback_note.py). tests/review/
keeps its own v14 rollback assertions (R3-owned, untouched).

## Scope integrity

`git status` delta vs. baseline: only the eight modified root test files plus
this evidence directory were added by this worker. No product file,
tests/review/**, Program Control, or git state was changed.
