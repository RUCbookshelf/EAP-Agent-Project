# PDW3-WU2 LEARNER RETRY-2 - CHECKPOINT 008: Worker D Dispatch (durable)

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- goal_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`
- worktree: `A:\EAP Agent Project\worktrees\learner`
- branch: `dept/feedback-learner`
- baseline: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- state: A/B/C DONE and parent-verified; D RUNNING; regression/V1 pending

## A/B/C gate inherited

Checkpoint 007 records the accepted A/B/C terminal results and the parent
quiet-worktree gate (`109 passed, 1 warning`). Their actual source/findings
files were inspected before D dispatch. No out-of-scope CORE/L2/UX/INT/API
implementation or migration was detected; `app/api/main.py` and `app/api/deps.py`
remained untouched before this D packet.

## D exact dispatch

- CLI: `codex` 0.145.0 via local OpenCodex proxy
- model: `deepseek/deepseek-v4-flash`
- reasoning: `ultra` (`model_reasoning_effort="ultra"`)
- environment: `PLANNING_DISABLED=1`
- sandbox: `danger-full-access` after the documented child sandbox-helper
  recovery; writes remain bounded by the packet to the learner worktree and
  owned files
- session ID: `34645`
- packet: `packets/D-API-COMPOSITION-WAVE2.md`
- output: `workers/D/stdout.jsonl`, `workers/D/stderr.log`,
  `workers/D/last-message.txt`

## D owned scope

- `app/api/main.py`
- `app/api/deps.py`
- `tests/learner/test_wu2_api_composition.py`
- optional additive assertions in `tests/test_composition_root.py`
- `workers/D/findings.md`

D must wire A/B/C through the existing single composition root, expose the
acknowledgement router exactly once, expose B's additive Journey methods, and
preserve one application/process/SQLite/API namespace. It must not modify
Worker A/B/C source or focused tests, migrations, CORE, or Program Control.

## Next gate

Keep D running until terminal. Then inspect its actual diff/findings, run the
parent focused/API/Wave-2 regression in a quiet worktree, and dispatch a fresh
V1 read-only verifier with the same exact DeepSeek/ultra/PLANNING_DISABLED
contract. Promotion, merge, push, PR, and Program Control writes remain out of
scope.

