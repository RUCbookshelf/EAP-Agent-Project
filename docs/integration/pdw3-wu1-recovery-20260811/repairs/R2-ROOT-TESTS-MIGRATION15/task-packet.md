# Task Packet — Repair R2: root test migration-14 reconciliation

- task_id: PDW3-WU1-DECOMP-RECOVERY__R2-ROOT-TESTS-MIGRATION15
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 2
- task_class: ENGINEERING (bounded test-only repair slice)
- risk: MEDIUM
- role: repair worker (deepseek/deepseek-v4-flash, ultra, PLANNING_DISABLED=1)
- worktree: A:\EAP Agent Project\worktrees\shared-core
- branch / HEAD: dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae

## Objective

Reconcile root tests (outside tests/review/) with migration version 15 so the
Wave-2 regression is green, addressing inventory findings D1, D2, C1. Test
files only; no product changes.

## Context

Read first:
- inventory: docs/integration/pdw3-wu1-recovery-20260811/inventory/A-B-C-D-E-PARTIAL-DIFF-INVENTORY.md (D1, D2, C1)
- Worker D findings: docs/integration/pdw3-wu1-recovery-20260811/workers/D-TESTS-CASES-AI/findings.md
- Evidence: workers/D-TESTS-CASES-AI/evidence/run-modified-root-tests.log,
  run-stale-14-probes.log

## In scope (write)

- tests/test_calf_v08.py (rollback chain at ~lines 177-188)
- tests/test_wave2_migration_v14.py
- tests/test_v06_configuration_dashboard.py
- tests/test_snapshot_repository_v03.py
- tests/test_v071_reliability_ui.py
- tests/test_v095b_router_contract.py
- tests/test_v095g_facade_contraction.py
- tests/test_v097b_wu3_target_creation.py
- Any ADDITIONAL root test file under tests/ (excluding tests/review/) that
  you verify with `rg` still hard-codes migration version 14 semantics
  (e.g., `migration_version() == 14`, `user_version = 14`, literal `14`
  migration assertions, rollback chains to 13 that assume LATEST=14).

## Out of scope

- tests/review/** (owned by R3), product code (app/**, pyproject.toml,
  uv.lock, run.bat), Program Control, other worktrees, raw SWECCL.

## Frozen contracts

- Migration 15 is the new LATEST; Migration 14 remains untouched and
  historical tests keep their intent (legacy upgrade paths must still prove
  data preservation).
- Rollback is one-step and ledger-only by design
  (`app/database/migrations.py:1123-1132`); tests must not weaken this rule
  or bypass it with product changes.
- Do not weaken existing assertions (no replacing meaningful checks with
  vacuous ones). Prefer `LATEST_MIGRATION_VERSION` constants for
  latest-semantics assertions; for v14-specific scenarios, construct a
  migration-14-era database in a valid way (e.g., upgrade to 15, rollback
  one step to 14, seed data, then upgrade to 15 and assert preservation;
  or drive the migration list up to 14 explicitly if the product API
  supports it — verify before using).
- No mocks that fake migration behavior.

## Implementation requirements

1. Fix `test_calf_v08.py` rollback chain so it passes under LATEST=15
   without weakening intent (one-step rollback from 15 -> 14, then 14 -> 13,
   re-apply; or assert the one-step ValueError where that is the tested
   contract).
2. Update `test_wave2_migration_v14.py` so fresh-DB, legacy-upgrade, and
   rollback tests reflect LATEST=15 while still proving the v14-era
   Wave-2 upgrade path preserves data.
3. Update `test_v06_configuration_dashboard.py` and all other verified
   hard-coded-14 files to LATEST-aware assertions.
4. Run the targeted files; then run any adjacent suites you changed to
   confirm no secondary breakage.

## Acceptance criteria

- Every file you touched passes (0 failures).
- The stale-14 probe set from Worker D is fully green
  (tests/test_wave2_migration_v14.py + tests/test_v06_configuration_dashboard.py).
- `rg` shows no remaining hard-coded migration-14 expectations in root tests
  except intentional historical-documentation strings.
- No product file changed; git status delta limited to tests/** and your
  evidence directory.

## Verification

- Commands (basetemp under your evidence dir):
  .venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp
  <evidence>/pytest-tmp -q <all touched files>
  plus the Worker D probe set. Save full logs under
  docs/integration/pdw3-wu1-recovery-20260811/repairs/R2-ROOT-TESTS-MIGRATION15/evidence/
- Set PYTHONDONTWRITEBYTECODE=1. Use command-scoped
  `git -c safe.directory='A:/EAP Agent Project/worktrees/shared-core'` only.

## Protected files

- All product files, tests/review/**, Program Control files, other
  worktrees, raw SWECCL.

## Output

- findings/evidence: docs/integration/pdw3-wu1-recovery-20260811/repairs/R2-ROOT-TESTS-MIGRATION15/
  (write only under this directory)
- Modified test files as listed in your return.

## Return contract

Return: status (DONE / DONE_WITH_CONCERNS / BLOCKED); final result; modified
files (exact paths); verification results with evidence paths; blockers or
risks (or "无"). Do not return full logs.

