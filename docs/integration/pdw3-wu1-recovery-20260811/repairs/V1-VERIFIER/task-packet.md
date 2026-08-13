# Task Packet — V1: independent read-only verification

- task_id: PDW3-WU1-DECOMP-RECOVERY__V1-VERIFIER
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 3
- task_class: REVIEW (independent, read-only verifier)
- risk: HIGH (gate evidence)
- role: verifier worker (deepseek/deepseek-v4-flash, ultra,
  PLANNING_DISABLED=1) — NOT an implementation worker
- worktree: A:\EAP Agent Project\worktrees\shared-core
- branch / HEAD: dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
- dispatch order: AFTER R3 completes

## Objective

Independently validate the repaired CORE WU1 state against the acceptance
gate and the explicit Cases A-I. You may inspect and run tests/probes, but
you must not change any product or test file. Worker/repair claims alone are
not evidence.

## Context

Read first (all durable artifacts):
- inventory: docs/integration/pdw3-wu1-recovery-20260811/inventory/A-B-C-D-E-PARTIAL-DIFF-INVENTORY.md
- repair status: docs/integration/pdw3-wu1-recovery-20260811/inventory/REPAIR-STATUS.md
- Phase-1 findings: docs/integration/pdw3-wu1-recovery-20260811/workers/{A,B,C,D}-*/findings.md
- Repair findings: docs/integration/pdw3-wu1-recovery-20260811/repairs/R1-REVIEW-ROBUSTNESS/findings.md,
  repairs/R2-ROOT-TESTS-MIGRATION15/findings.md,
  repairs/R3-TESTS-REVIEW-COVERAGE/findings.md
- Explicit Cases A-I: inventory/A-B-C-D-E-PARTIAL-DIFF-INVENTORY.md section 3

## In scope (read/run only)

- app/review/**, app/api/routers/review.py, app/api/main.py (diff),
  app/infrastructure/sqlite/repositories/review.py,
  app/database/migrations.py (Migration 15), app/version.py,
  pyproject.toml/uv.lock (fsrs==6.3.2), tests/review/**,
  R2-reconciled root test files, modified root test files

## Out of scope (never write)

- Any product or test file, Program Control, other worktrees, raw SWECCL,
  git mutations. Evidence writes only under your own directory
  (repairs/V1-VERIFIER/evidence/).

## Validation matrix (each item needs direct evidence)

1. Real fsrs==6.3.2 behavior: installed version via importlib.metadata;
   deterministic next/repeat-review vectors match raw library computation;
   identity recorded.
2. Rating/state lifecycle: three channels distinct; conservative final
   resolution; transitions through real scheduler; invalid inputs fail
   closed.
3. Migration 15 fresh path: empty DB -> 15; tables/ledger/version
   single-source.
4. Migration 15 existing path: genuine migration-14 DB with Wave-2 data ->
   15, rows preserved, idempotent, one-step rollback semantics honored.
5. Shared SQLite close/reopen persistence on the same file; LearningItem
   identity stable; ReviewEvent rows separate.
6. Provenance: rating-rule version + scheduler identity/parameters +
   state_before/after persisted; deterministic reconstruction.
7. Evidence separation: PracticeActivity vs LearningItem vs ReviewEvent;
   practice vs authentic evidence; observed/inference/recommendation/outcome
   distinction; no mastery/proficiency/ability/learning-gain semantics in
   review surfaces or API responses.
8. Fail-closed inputs: invalid ratings, unknown fields, malformed
   provenance, nonexistent activity (4xx), duplicate PA/RE IDs (409,
   original intact), cross-student event/activity (403), naive/non-UTC
   datetime (422) — with no writes on rejection.
9. Real composition: one composition root/API namespace; review router once;
   one Database/SQLite file; no second runtime/registry/event bus.
10. Wave-2 compatibility: R2-reconciled root tests and affected Wave-2
    suites pass; route contract pin includes the 5 review routes; LearningItem
    v1 contract untouched.
11. Explicit Cases A-I: per canonical definitions, cite test:file:line or
    probe evidence for each; note any gap.
12. Resource/scope hygiene: git status shows only authorized changes
    (product repair files + test reconciliations + docs/integration evidence);
    no stray processes/servers; evidence paths listed.

## Verification (read-only)

- Full tests/review suite.
- R2 targeted set + stale-14 probe set + adjacent suites (use the same file
  lists as R2/R3 evidence).
- Independent probes for items 1-10 where the suites do not already prove
  them (temp DBs under your evidence dir, TestClient
  raise_server_exceptions=False, PYTHONDONTWRITEBYTECODE=1, --basetemp under
  evidence).
- Semantic scans (field/AST/API response keys).
- git -c safe.directory=... status/diff read-only checks.

## Output

- Verification report:
  docs/integration/pdw3-wu1-recovery-20260811/repairs/V1-VERIFIER/verification-report.md
  with: scope; commands; per-item PASS/FAIL evidence; Cases A-I matrix;
  worktree-hygiene check; blocker; overall verdict
  (PASS / PASS_WITH_CONCERNS / FAIL).
- Evidence/logs under repairs/V1-VERIFIER/evidence/.
- You may create ONLY these files.

## Return contract

Return: status (DONE / DONE_WITH_CONCERNS / BLOCKED); overall verdict;
per-item PASS/FAIL summary; evidence paths; blockers or risks (or "无").
Do not return full logs. Do NOT repair anything you find; report it.

