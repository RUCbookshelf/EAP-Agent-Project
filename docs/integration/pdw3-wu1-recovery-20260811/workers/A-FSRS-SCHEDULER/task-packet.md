# Task Packet — Worker A: FSRS/scheduler audit (READ-ONLY)

- task_id: PDW3-WU1-DECOMP-RECOVERY__A-FSRS-SCHEDULER
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

Read-only audit of the preserved CORE WU1 partial implementation for FSRS
scheduler correctness against the real installed fsrs==6.3.2 API and the
rating/state lifecycle. Do NOT repair anything.

## Context

- The worktree contains an uncommitted partial WU1 implementation:
  app/review/*, app/api/routers/review.py, app/infrastructure/sqlite/repositories/review.py,
  Migration 15 additions in app/database/migrations.py, app/version.py,
  pyproject.toml (fsrs==6.3.2), uv.lock, tests/review/*, plus pre-existing
  untracked docs. Preserve all of it.
- Python runtime: A:\EAP Agent Project\worktrees\shared-core\.venv\Scripts\python.exe
- The installed fsrs package version is expected to be 6.3.2.

## In scope

- app/review/models.py, protocols.py, rating_policy.py, scheduler.py,
  service.py, __init__.py
- app/learning_items/ (scheduling-relevant contracts only)
- pyproject.toml fsrs entry and uv.lock fsrs entry
- tests/review/test_scheduler_determinism.py, test_rating_policy.py,
  test_review_service.py
- Real fsrs package API installed in the worktree .venv

## Out of scope

- Any file write outside your assigned evidence directory (see Output).
- Repairing, editing, staging, committing, or deleting product files.
- app/database, app/api, app/infrastructure/sqlite (those belong to Worker B/C
  audits; read only if directly needed to judge scheduler wiring).
- Program Control files, other worktrees, raw SWECCL.

## Frozen contracts to verify

- fsrs==6.3.2 must be the real installed package used by the scheduler.
- FSRS state is scheduling state only; never mastery, proficiency, ability,
  learning gain, scores, percentages, CEFR, or CET.
- System provisional, learner self, and final scheduler ratings remain three
  separate channels.
- Versioned rating-rule/scheduler provenance must exist.
- Deterministic next-review and repeat-review behavior.
- Invalid rating/state inputs fail closed.
- One application/process/database/API namespace/composition root; no second
  scheduler service or runtime.

## Review questions

1. Does the scheduler call the real fsrs 6.3.2 API (FSRS/Card/ReviewLog/Rating/
   State classes and methods) with correct signatures? Compare against the
   installed package (inspect module members and signatures; record exact
   evidence).
2. Are state transitions and rating mappings correct for New -> Learning ->
   Review and repeats?
3. Are the three rating channels distinct and correctly mapped to fsrs ratings?
4. Is provenance versioned (rating rule + scheduler version) and persisted on
   review records?
5. Do deterministic vectors exist and do they match real fsrs computations?
6. Do invalid ratings/states/identities fail closed instead of being coerced?
7. Is any semantic leakage present (scheduling state described as ability,
   learning gain, score, percentage)?

## Verification (read-only)

- Run: .venv\Scripts\python.exe -c "import fsrs; print(fsrs.__version__)"
- Inspect the installed fsrs API signatures and compare with app/review code.
- Run targeted tests, e.g.:
  .venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <your evidence dir>/pytest-tmp -q tests/review/test_scheduler_determinism.py tests/review/test_rating_policy.py tests/review/test_review_service.py
- Set PYTHONDONTWRITEBYTECODE=1. Save full logs to your evidence dir.
- Do not run any command that mutates the repository, database outside temp
  dirs, or Program Control.

## Acceptance criteria for the audit artifact

findings.md must contain: scope; files inspected (path:line); tests run
(command, result, evidence path); A/B/C/D/E findings (A complete/coherent,
B implemented but unverified, C incomplete, D incorrect/contract-incompatible,
E out-of-scope drift); blocker (or None); verdict
(PASS / PASS_WITH_CONCERNS / FAIL).

## Protected files

- All pre-existing modified/untracked files in the worktree (never touch).
- app/database/migrations.py Migration 14 and earlier (read-only).
- Program Control files (never write).

## Output

- Findings: docs/integration/pdw3-wu1-recovery-20260811/workers/A-FSRS-SCHEDULER/findings.md
- Logs/evidence: docs/integration/pdw3-wu1-recovery-20260811/workers/A-FSRS-SCHEDULER/evidence/
- You may create only these files.

## Return contract

Return a compact final message: status (DONE / DONE_WITH_CONCERNS / BLOCKED);
final result; modified files (None); verification summary with evidence paths;
blockers/risks. Do not return full logs. Final message must also say:
返回内容必须包含：1.最终完成结果；2.修改的文件路径（无则写None）；
3.测试或验证结果；4.尚未解决的阻塞项或风险（没有则写“无”）。
不要返回完整日志；只返回最终结果与修改文件路径。

