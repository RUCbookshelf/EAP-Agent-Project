# Task Packet — Worker D: tests / Cases A-I coverage audit (READ-ONLY)

- task_id: PDW3-WU1-DECOMP-RECOVERY__D-TESTS-CASES-AI
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

Read-only audit of test coverage for the preserved CORE WU1 partial
implementation against the explicit Cases A-I and the WU1 acceptance criteria.
Do NOT repair code or add tests.

## Context

- Partial WU1 implementation and tests are uncommitted in this worktree.
- Python runtime: A:\EAP Agent Project\worktrees\shared-core\.venv\Scripts\python.exe

## In scope

- All files under tests/review/
- Modified root tests from git status: tests/test_analysis_runs_v04.py,
  tests/test_calf_v08.py, tests/test_composition_root.py,
  tests/test_diagnostic_calibration_v061.py, tests/test_learner_model_v07.py,
  tests/test_revision_v05.py
- The app/review and app/api review surfaces only as needed to judge whether a
  test is meaningful (real behavior vs mock-only)

## Out of scope

- Any file write outside your assigned evidence directory.
- Adding, editing, deleting, staging, or committing tests or product code.
- Program Control files, other worktrees, raw SWECCL.

## Explicit Cases A-I (canonical for this epoch)

- Case A: Real installed fsrs==6.3.2 integration with version identity and
  deterministic vectors (next review, repeat review).
- Case B: Rating/state lifecycle — system provisional, learner self, final
  scheduler ratings across FSRS states; invalid transitions fail closed.
- Case C: Migration 15 fresh path (brand-new DB reaches 15 additively after
  Migration 14).
- Case D: Migration 15 existing Wave-2 path (migration-14 DB with data upgrades
  additively, data preserved, idempotent).
- Case E: Shared SQLite close/reopen persistence with stable LearningItem
  identity and separate ReviewEvent evidence.
- Case F: Three rating channels + versioned rating-rule/scheduler provenance.
- Case G: Evidence separation and semantics (PracticeActivity vs LearningItem
  vs ReviewEvent; practice vs authentic evidence; observed/inference/
  recommendation/outcome distinct; no ability/proficiency/learning-gain
  semantics).
- Case H: Fail-closed invalid inputs (ratings, identity, state, provenance).
- Case I: Real composition + Wave-2 compatibility (one composition root/API
  namespace; existing Wave-2 endpoints/tests compatible; no second
  database/runtime/registry).

## Review questions

1. Which Case A-I has explicit test coverage, and where (file:test:line)?
2. Which requirements from the acceptance gate are untested or only
   superficially tested?
3. Do tests exercise the real installed fsrs package (not a stub/mock)?
4. Do migration tests cover fresh, existing-data, and idempotence paths?
5. Do persistence tests prove close/reopen/reload on the same SQLite file?
6. Are negative/fail-closed paths tested for each invalid-input class?
7. Would each test fail if the corresponding behavior regressed (meaningfulness)?
8. Do modified root tests change Wave-2 expectations, and are those changes
   coherent or contract-incompatible?

## Verification (read-only)

- Run collection and focused execution:
  .venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <evidence>/pytest-tmp -q --collect-only tests/review
  then run the review suite and the six modified root test files if feasible.
- You may run read-only probes to confirm whether a test would detect a
  regression; do not modify tests.
- Set PYTHONDONTWRITEBYTECODE=1. Save full logs to your evidence dir.

## Acceptance criteria for the audit artifact

findings.md must contain: scope; files inspected (path:line); tests run
(command, result, evidence path); a per-Case A-I coverage matrix
(covered / partial / missing with file:test:line evidence); A/B/C/D/E findings
for the test layer; blocker (or None); verdict
(PASS / PASS_WITH_CONCERNS / FAIL).

## Protected files

- All pre-existing modified/untracked files in the worktree.
- Program Control files (never write).

## Output

- Findings: docs/integration/pdw3-wu1-recovery-20260811/workers/D-TESTS-CASES-AI/findings.md
- Logs/evidence: docs/integration/pdw3-wu1-recovery-20260811/workers/D-TESTS-CASES-AI/evidence/
- You may create only these files.

## Return contract

Return a compact final message: status (DONE / DONE_WITH_CONCERNS / BLOCKED);
final result; modified files (None); verification summary with evidence paths;
blockers/risks. Do not return full logs. Final message must also say:
返回内容必须包含：1.最终完成结果；2.修改的文件路径（无则写None）；
3.测试或验证结果；4.尚未解决的阻塞项或风险（没有则写“无”）。
不要返回完整日志；只返回最终结果与修改文件路径。

