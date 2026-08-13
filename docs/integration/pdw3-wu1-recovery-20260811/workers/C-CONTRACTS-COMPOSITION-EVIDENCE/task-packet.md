# Task Packet — Worker C: contracts / composition / evidence separation audit (READ-ONLY)

- task_id: PDW3-WU1-DECOMP-RECOVERY__C-CONTRACTS-COMPOSITION-EVIDENCE
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

Read-only audit of the preserved partial implementation for contract and
composition correctness and evidence-separation semantics: API/composition
wiring, LearningItem/PracticeActivity/ReviewEvent contracts, three rating
channels, provenance, fail-closed inputs, and Wave-2 compatibility. Do NOT
repair anything.

## Context

- Uncommitted partial WU1 diff includes app/api/main.py,
  app/api/routers/review.py, app/infrastructure/sqlite/repositories/__init__.py,
  app/review/*, tests/review (composition/semantic/wave2), and modifications to
  existing Wave-2 test files.
- Python runtime: A:\EAP Agent Project\worktrees\shared-core\.venv\Scripts\python.exe

## In scope

- app/api/main.py (diff scope) and app/api/routers/review.py
- app/infrastructure/sqlite/repositories/__init__.py (diff scope)
- app/learning_items/ and app/practice/ (contract surfaces used by review)
- app/review/service.py and protocols.py (contract surfaces)
- tests/review/test_review_composition.py, test_semantic_boundaries.py,
  test_wave2_regression.py
- Modified root tests: tests/test_composition_root.py and any other modified
  Wave-2 test listed in git status
- AGENTS.md architecture boundaries

## Out of scope

- Any file write outside your assigned evidence directory.
- Repairing, editing, staging, committing, or deleting product files.
- FSRS internals and migration internals (Worker A/B scope; read only as
  needed).
- Program Control files, other worktrees, raw SWECCL.

## Frozen contracts to verify

- One application, one process, one SQLite database, one API namespace, one
  composition root; additive domains only.
- LearningItem = durable scheduled object; PracticeActivity = activity/evidence
  history; ReviewEvent = durable review evidence.
- System provisional, learner self, and final scheduler ratings remain three
  separate channels with versioned provenance.
- Observed evidence != diagnostic inference != feedback recommendation !=
  learning outcome; practice evidence distinct from authentic writing
  evidence; scheduling state is not ability/proficiency/learning gain.
- API routes validate/translate; application services own workflows; core
  services depend on Repository protocols.
- Fail-closed invalid rating/state/identity/provenance inputs.
- Wave-2 LearningItem/practice records and contracts preserved; existing
  Wave-2 endpoints remain compatible.
- No second runtime, event bus, registry authority, or composition root.

## Review questions

1. Is the review router registered in the real composition root/API namespace
   with its repository and service dependencies?
2. Are the three rating channels (system provisional, learner self, final
   scheduler) exposed and kept distinct at the contract boundary?
3. Is provenance versioned (rating rule + scheduler version) on review
   records?
4. Is evidence separation maintained in models/contracts (PracticeActivity vs
   LearningItem vs ReviewEvent; practice vs authentic evidence)?
5. Do invalid inputs fail closed at the API/service boundary?
6. Is any semantic leak present (scheduling state as ability, score,
   percentage, CEFR/CET, learning gain)?
7. Does Wave-2 compatibility hold (existing routes, imports, contracts)?

## Verification (read-only)

- Run targeted tests, e.g.:
  .venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <evidence>/pytest-tmp -q tests/review/test_review_composition.py tests/review/test_semantic_boundaries.py tests/review/test_wave2_regression.py
- You may also run a read-only import/composition probe with FastAPI TestClient
  if tests do not cover it; record exact commands and outputs.
- Set PYTHONDONTWRITEBYTECODE=1. Save full logs to your evidence dir.

## Acceptance criteria for the audit artifact

findings.md must contain: scope; files inspected (path:line); tests/probes run
(command, result, evidence path); A/B/C/D/E findings; blocker (or None);
verdict (PASS / PASS_WITH_CONCERNS / FAIL).

## Protected files

- All pre-existing modified/untracked files in the worktree.
- Program Control files (never write).

## Output

- Findings: docs/integration/pdw3-wu1-recovery-20260811/workers/C-CONTRACTS-COMPOSITION-EVIDENCE/findings.md
- Logs/evidence: docs/integration/pdw3-wu1-recovery-20260811/workers/C-CONTRACTS-COMPOSITION-EVIDENCE/evidence/
- You may create only these files.

## Return contract

Return a compact final message: status (DONE / DONE_WITH_CONCERNS / BLOCKED);
final result; modified files (None); verification summary with evidence paths;
blockers/risks. Do not return full logs. Final message must also say:
返回内容必须包含：1.最终完成结果；2.修改的文件路径（无则写None）；
3.测试或验证结果；4.尚未解决的阻塞项或风险（没有则写“无”）。
不要返回完整日志；只返回最终结果与修改文件路径。

