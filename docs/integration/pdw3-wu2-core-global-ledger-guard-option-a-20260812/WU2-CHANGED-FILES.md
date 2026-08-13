# Option A Global Ledger Guard - changed files

Goal: `PDW3-WU2-CORE-GLOBAL-LEDGER-GUARD-OPTION-A-20260812`
Worktree: `A:\EAP Agent Project\worktrees\shared-core`

## Goal-owned writes (delta over the preserved WU1/WU2 candidate)

1. `app/database/migrations.py` - added the CORE global ledger guard /
   consumer seam only (constants `GLOBAL_MIGRATION_LEDGER_OWNER`,
   `GLOBAL_MIGRATION_LEDGER_VERSION_15`,
   `GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME`,
   function `assert_global_migration_15_identity`) plus a one-paragraph
   Option-A note in the module migration-version docstring. The existing
   Migration 15 body, `LATEST_MIGRATION_VERSION = 15`, the `MIGRATIONS`
   registry entry, and the 15->14 rollback branch were NOT rewritten.
2. `tests/review/test_migration_15_global_ledger_guard.py` - 7 new focused
   tests (identity constants, unique ledger identity, fresh ledger row,
   guard negative probes for rename/latest-drift/duplicate, and the single
   runner/single database consumer seam).
3. `docs/integration/pdw3-wu2-core-global-ledger-guard-option-a-20260812/` -
   this report, the schema-valid handoff JSON, and the evidence directory.

## Pinned existing implementation (unchanged, used as evidence)

- `app/database/migrations.py`: `LATEST_MIGRATION_VERSION = 15`;
  `MIGRATIONS[15] = ("review_scheduling_foundation", _migration_15)`;
  `_migration_15` body creating `practice_activities`, `review_events`,
  `learning_item_scheduler_states`; ledger-only rollback (15,14).
- `app/version.py:47`: `PLATFORM_DATABASE_MIGRATION_VERSION: int = 15`.
- `tests/review/test_migration_15.py` and `tests/test_wave2_migration_v14.py`:
  pre-existing fresh/v14-era/idempotence/rollback coverage.

## Resource hygiene

- HEAD unchanged: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` (no commit,
  stage, push, PR, merge, promotion, reset, clean, restore, or rebase).
- No Program Control writes; no LEARNER/INT/master/other worktree mutation.
- Every pre-existing dirty/untracked file preserved (see
  `evidence/git-status-initial.txt` vs `evidence/git-status-final.txt`).
