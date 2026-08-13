# RETRY-2 V1 — Independent Read-Only Verifier

You are a fresh, independent third-level verifier for
`PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`.

## Mandatory execution contract

- Model: `deepseek/deepseek-v4-flash`
- Reasoning: `ultra`
- Environment: `PLANNING_DISABLED=1`
- Authorized worktree: `A:\EAP Agent Project\worktrees\learner`
- Read-only verification: do not create, edit, delete, stage, or move any
  product/evidence file; do not run commands that mutate Git state.
- No provider/model/reasoning substitution.

## Verification scope

Read the RETRY-2 checkpoint, all Worker A-D findings, the live CORE WU1 handoff,
the executor prompt, and the actual diff/status. Independently verify:

- only authorized LEARNER WU2 files changed and all five pre-existing
  untracked paths remain present and byte-identical;
- dual-channel practice/review versus authentic writing application behavior;
- CORE contract consumption boundary, separate rating channels, rating-rule and
  scheduler provenance, and no copied `app/review` implementation;
- positive acknowledgement consent, provenance/version, invalid-input
  fail-closed and no-write semantics;
- PracticeActivity, ReviewEvent, LearningItem v1, observed evidence,
  inference, recommendation, and outcome remain distinct;
- no mastery/proficiency/ability/learning-gain/score/causal claims;
- one composition root, one SQLite authority, no migration/scheduler/runtime
  duplication, no duplicate route registration;
- focused WU2 tests and the affected Wave-2 regression.

Run tests in a way that does not intentionally mutate the worktree (for
example `PYTHONDONTWRITEBYTECODE=1` and disabling pytest cache where
appropriate). Do not repair anything. Return a compact verdict (`PASS`,
`CONCERNS`, or `FAIL`) with exact commands, exit codes/counts, file/line
evidence, and blockers. The parent will persist your result.

