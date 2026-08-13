# Task Packet — Repair R3: tests/review coverage + R1 regression tests

- task_id: PDW3-WU1-DECOMP-RECOVERY__R3-TESTS-REVIEW-COVERAGE
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 2
- task_class: ENGINEERING (bounded test-only repair slice)
- risk: MEDIUM
- role: repair worker (deepseek/deepseek-v4-flash, ultra, PLANNING_DISABLED=1)
- worktree: A:\EAP Agent Project\worktrees\shared-core
- branch / HEAD: dept/shared-core @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
- dispatch order: AFTER R1 completes (read R1's final result first)

## Objective

Close the Phase-1 test-coverage gaps (inventory C2-C5) and add regression
tests for R1's fail-closed behavior (D3-D5, C9). tests/review only; no
product changes.

## Context

Read first:
- inventory: docs/integration/pdw3-wu1-recovery-20260811/inventory/A-B-C-D-E-PARTIAL-DIFF-INVENTORY.md (C2-C5, D3-D5, C9)
- Worker D findings: docs/integration/pdw3-wu1-recovery-20260811/workers/D-TESTS-CASES-AI/findings.md (matrix + C items)
- R1 result: docs/integration/pdw3-wu1-recovery-20260811/repairs/R1-REVIEW-ROBUSTNESS/ (final message + evidence)

## In scope (write)

- tests/review/*.py only (add or update tests as needed).

## Out of scope

- Product code (app/**), root tests outside tests/review (owned by R2),
  Program Control, other worktrees, raw SWECCL.

## Frozen contracts

- Tests must exercise REAL behavior (real fsrs==6.3.2, real SQLite files,
  real composition root); no mocks/stubs/monkeypatch that fake scheduler,
  migration, or repository behavior.
- Existing 53 tests must remain green unless R1's intentional contract
  change makes an old expectation obsolete; if you must change an existing
  test, explain exactly which R1 behavior it now asserts and keep the
  original intent.
- Evidence/assertions stay source-bounded (no fabricated vectors).

## Implementation requirements

1. Case D: add a genuine migration-14-era Wave-2 data preservation test
   (seed learning_items/writing_tasks at 14, upgrade to 15, assert rows and
   review tables coexist).
2. Case B: add invalid-transition coverage through the real adapter —
   record what the real fsrs 6.3.2 library actually does for the probed
   state/rating vectors (pin identity/version) and assert fail-closed
   semantics where the product contract requires rejection.
3. Case H: add malformed-provenance rejection tests and API-layer 422
   negatives (invalid rating, invalid authentic_evidence_status, unknown
   fields) through TestClient.
4. Case G: assert four-way evidence-semantics distinction directly
   (ReviewEvent/PracticeActivity cannot carry inference/recommendation/
   outcome semantics) and extend the semantic AST scan to include "ability"
   tokens if app/review passes with that addition (verify first).
5. R1 regression tests: nonexistent practice_activity_id -> mapped 4xx and
   no write; duplicate PA/RE id -> 409 and original row intact; cross-student
   event/activity -> 403; naive/non-UTC reviewed_at -> 422; happy path
   unchanged.
6. Run the full tests/review suite; it must be green.

## Acceptance criteria

- Full tests/review suite passes with the new/updated tests (documented
  count).
- Each inventory C2-C5 item has an explicit test reference (file:test:line).
- No product file changed; git status delta limited to tests/review/** and
  your evidence directory.

## Verification

- .venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp
  <evidence>/pytest-tmp -q tests/review
- Save full logs under
  docs/integration/pdw3-wu1-recovery-20260811/repairs/R3-TESTS-REVIEW-COVERAGE/evidence/
- Set PYTHONDONTWRITEBYTECODE=1. Use command-scoped
  `git -c safe.directory='A:/EAP Agent Project/worktrees/shared-core'` only.

## Protected files

- All product files, root tests outside tests/review, Program Control
  files, other worktrees, raw SWECCL.

## Output

- findings/evidence: docs/integration/pdw3-wu1-recovery-20260811/repairs/R3-TESTS-REVIEW-COVERAGE/
  (write only under this directory)
- Modified/added test files as listed in your return.

## Return contract

Return: status (DONE / DONE_WITH_CONCERNS / BLOCKED); final result; modified
files (exact paths); verification results with evidence paths; blockers or
risks (or "无"). Do not return full logs.

