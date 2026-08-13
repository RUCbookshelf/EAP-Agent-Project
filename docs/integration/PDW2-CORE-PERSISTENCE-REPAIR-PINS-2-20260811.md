# CORE residual migration-14 pin refresh - PDW2-A-CORE-PERSISTENCE__REPAIR-PINS-2

- Goal: `PDW2-A-CORE-PERSISTENCE__REPAIR-PINS-2`
- Owner: CORE (fresh isolated executor; deepseek-v4-flash, ultra reasoning)
- Worktree: `A:\EAP Agent Project\worktrees\shared-core` (branch `dept/shared-core`)
- Starting SHA (parent): `606e557ca0940942a5c8023119ec8d3a42f72544`
- Final SHA: `3204b6afda3320d4c09e395994cdc9d0671f29cd`
- Verdict: **GREEN**
- Returned: 2026-08-11

## Scope executed

Refreshed the two residual migration-13 version pins to 14, following the exact convention of the prior 10-file refresh (commit `606e557`, Goal `PDW2-A-CORE-PERSISTENCE__REPAIR-INTEGRATION`): pinned `== 13`/`= 13` values become `14`, and rollback chains gain the intermediate one-step `rollback(connection, 13) == 13` step before the existing `rollback(..., 12)` step (the migration layer supports only one-step logical rollbacks, so a direct 14->12 chain would raise).

### tests/test_v095b_router_contract.py

- `test_health_contract_healthy_state`: `lifecycle.migration_version = 13` -> `14`; `assert body["database_migration_version"] == 13` -> `== 14`.

### tests/test_v097b_wu3_target_creation.py

- `TestMigration13.test_migration_preserves_existing_rows_and_rolls_back_non_destructively`:
  - `assert upgrade(connection) == 13` -> `== 14` (first upgrade)
  - inserted `assert rollback(connection, 13) == 13` before `assert rollback(connection, 12) == 12` (required 14->13 step in the chain)
  - `assert upgrade(connection) == 13` -> `== 14` (re-upgrade)
- Unchanged: `for version in range(1, 13)` seeding loop (seeds migrations 1..12 so the migration-13 uniqueness index under test is exercised through the upgrade path), class name/docstring (migration 13 remains the practice-target priority-key uniqueness migration).

## Verification evidence

Pre-commit run (`uv run python -m pytest ... -q`, worktree-local `.venv` via `pyproject.toml`/`uv.lock`):

- `tests/test_v095b_router_contract.py` + `tests/test_v097b_wu3_target_creation.py` + `tests/shared/test_version_single_sourcing.py` + `tests/test_migrations_v02.py`: **58 passed** in 64.11s (exit 0).

Post-commit rerun (same four modules): **58 passed** in 64.53s (exit 0).

Environment note: the sandbox cannot write uv cache under `%LOCALAPPDATA%` (recorded limitation `UV_CACHE_UNUSABLE`); runs therefore required escalated permissions, same as the ENV gate re-verification. The pytest cache warning (WinError 5 on `.pytest_cache`) is environmental and non-blocking.

## Git evidence

- `git show --stat HEAD`: `3204b6afda3320d4c09e395994cdc9d0671f29cd`, parent `606e557ca0940942a5c8023119ec8d3a42f72544`, exactly `tests/test_v095b_router_contract.py` (4 ++/--) and `tests/test_v097b_wu3_target_creation.py` (5 ++/--) - 2 files changed, 5 insertions(+), 4 deletions(-).
- Pre-existing untracked evidence preserved byte-identically (ADR and integration docs under `docs/architecture/` and `docs/integration/`).
- No `migrations.py`/`main.py` changes; no reset/clean/rebase/force update/push/PR/promotion; no writes outside the authorized worktree.
- Command-scoped `git -c safe.directory=...` used for the linked-worktree ownership quirk; no global config change.

## Artifacts

- Commit: `3204b6afda3320d4c09e395994cdc9d0671f29cd` on `dept/shared-core`
- This report: `docs/integration/PDW2-CORE-PERSISTENCE-REPAIR-PINS-2-20260811.md`

## Dependencies

- Unlocked: full-suite migration-14 drift guard GREEN for the WU2 INT gate.
- Remaining: INT WU2 integration gate; safe alignment of canonical worktrees remains a separate prior action for future department write Goals.
