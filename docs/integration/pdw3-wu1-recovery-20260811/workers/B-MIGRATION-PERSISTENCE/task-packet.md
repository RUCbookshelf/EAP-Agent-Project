# Task Packet — Worker B: Migration 15 / persistence / repository audit (READ-ONLY)

- task_id: PDW3-WU1-DECOMP-RECOVERY__B-MIGRATION-PERSISTENCE
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 1
- task_class: REVIEW
- risk: MEDIUM
- role: nested read-only review worker
- model: deepseek/deepseek-v4-flash
- reasoning: ultra
- planning: PLANNING_DISABLED=1 (environment is set; do not create or edit any
  planning file, including .agent-workflow)
- worktree: A:\EAP Agent Project\worktrees\shared-core
- branch / HEAD: dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae

## Objective

Read-only audit of the preserved partial implementation for the additive
Migration 15 and shared SQLite review/scheduling persistence and repository
layer. Do NOT repair anything.

## Context

- Uncommitted partial WU1 diff includes app/database/migrations.py,
  app/version.py, app/database/repository.py,
  app/infrastructure/sqlite/repositories/__init__.py,
  app/infrastructure/sqlite/repositories/review.py, tests/review
  (test_migration_15.py, test_review_repository.py).
- Python runtime: A:\EAP Agent Project\worktrees\shared-core\.venv\Scripts\python.exe

## In scope

- app/database/migrations.py (Migration 15 only; Migration 14 read-only)
- app/version.py (migration version contract)
- app/database/repository.py (diff scope)
- app/infrastructure/sqlite/repositories/__init__.py and review.py
- app/infrastructure/sqlite/ connection/transaction helpers used by review
- tests/review/test_migration_15.py and test_review_repository.py
- Existing Wave-2 migration/schema behavior needed to judge the 14->15 path

## Out of scope

- Any file write outside your assigned evidence directory.
- Repairing, editing, staging, committing, or deleting product files.
- app/review logic and app/api (Worker A/C scope).
- Program Control files, other worktrees, raw SWECCL.

## Frozen contracts to verify

- Migration 15 is additive after Migration 14; Migration 14 and earlier are
  never modified.
- Fresh database path and existing Wave-2 (migration-14 with data) path both
  work; data preserved; idempotence verified.
- One SQLite database file only; no second database.
- Shared SQLite persistence survives close/reopen/reload with stable
  LearningItem identity and separate ReviewEvent evidence.
- Core services depend on Repository protocols, never directly on
  sqlite3.connect (AGENTS.md boundary).
- Version source is single-source: app/version.py matches migration version.
- No reset/clean/restore/rebase of the worktree.

## Review questions

1. What does Migration 15 add (tables/columns/indexes)? Is it strictly
   additive and ordered after Migration 14 in the migration list?
2. Does the fresh path (empty DB) reach migration 15? Does the existing path
   (DB at migration 14 with Wave-2 LearningItem/practice rows) reach 15
   without data loss? Is re-running idempotent?
3. Does app/version.py report the migration version consistently?
4. Does the review repository round-trip rows through the same SQLite file and
   survive close/reopen with stable LearningItem identity?
5. Are ReviewEvent rows distinct from LearningItem scheduling state?
6. Does any core service bypass Repository protocols and call sqlite3
   directly?
7. Is any second database, engine, or persistence authority introduced?

## Verification (read-only)

- Run the migration and repository tests with temp databases under your
  evidence dir:
  .venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <evidence>/pytest-tmp -q tests/review/test_migration_15.py tests/review/test_review_repository.py
- You may run short read-only Python probes with temp DB files under your
  evidence dir to prove fresh/existing/idempotent paths and close/reopen
  persistence. Record exact commands and outputs.
- Set PYTHONDONTWRITEBYTECODE=1. Save full logs to your evidence dir.

## Acceptance criteria for the audit artifact

findings.md must contain: scope; files inspected (path:line); tests/probes run
(command, result, evidence path); A/B/C/D/E findings; blocker (or None);
verdict (PASS / PASS_WITH_CONCERNS / FAIL).

## Protected files

- All pre-existing modified/untracked files in the worktree.
- Migration 14 and earlier (read-only).
- Program Control files (never write).

## Output

- Findings: docs/integration/pdw3-wu1-recovery-20260811/workers/B-MIGRATION-PERSISTENCE/findings.md
- Logs/evidence: docs/integration/pdw3-wu1-recovery-20260811/workers/B-MIGRATION-PERSISTENCE/evidence/
- You may create only these files (plus temp DBs/logs inside the evidence dir).

## Return contract

Return a compact final message: status (DONE / DONE_WITH_CONCERNS / BLOCKED);
final result; modified files (None); verification summary with evidence paths;
blockers/risks. Do not return full logs. Final message must also say:
返回内容必须包含：1.最终完成结果；2.修改的文件路径（无则写None）；
3.测试或验证结果；4.尚未解决的阻塞项或风险（没有则写“无”）。
不要返回完整日志；只返回最终结果与修改文件路径。

