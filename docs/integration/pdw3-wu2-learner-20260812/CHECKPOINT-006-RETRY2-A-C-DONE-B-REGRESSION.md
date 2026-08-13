# PDW3-WU2 LEARNER RETRY-2 - CHECKPOINT 006: A/C Done, B Regression (durable)

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- goal_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`
- worktree: `A:\EAP Agent Project\worktrees\learner`
- branch: `dept/feedback-learner`
- starting_sha: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- state: A/C terminal DONE and process-clean; B active in final regression;
  D/V1 gated

## A terminal result

- Session `67614`: exit code `0`.
- Findings: `workers/A/findings.md`.
- Scope: `app/learner/review_bridge.py`,
  `app/practice/review_transfer.py`, focused test file, findings only;
  no infrastructure adapter was needed and no CORE code was copied.
- Verification reported: focused `40 passed`; learner suite `250 passed, 1
  warning`; repeated focused reruns stable.
- Boundary: structural consumption of the future injected CORE
  `ReviewService`; three rating channels remain separate; fail-closed
  provenance/time/identity/ownership/conflict behavior is delegated to or
  guarded before CORE writes; practice/authentic channels stay distinct.

## C terminal result

- Session `44393`: exit code `0`; clean shutdown verified.
- Findings: `workers/C/findings.md`.
- Scope: acknowledgement contracts/service/router and focused test file only;
  `main.py`/`deps.py` untouched for D.
- Verification reported: focused `51 passed`; learner suite `250 passed, 1
  warning`; adjacent `tests/shared tests/wave2` `265 passed, 2 warnings`;
  no-write assertions cover consent, evidence, provenance/version, ownership,
  semantic, duplicate/conflict, and malformed paths.

## B intermediate result

- Session `7417`: still RUNNING; no terminal findings or last-message file.
- Focused `tests/learner/test_wu2_journey_history_transfer.py`: `18 passed`
  after one assertion-only test correction.
- Affected Journey/Wave-2/learner regression command: `439 passed, 2
  warnings in 187.44s (0:03:07)`.
- B then began a second broader sweep covering practice WU2-WU6,
  composition-root, and service/port narrowing tests. It remains active.

## Current actual worktree signal

Untracked/new WU2 files include A/C source and tests plus B's
`app/journey/transfer.py`, additive `app/journey/service.py` change, and
`tests/learner/test_wu2_journey_history_transfer.py`. No D composition files
have been written. Parent-side verification is still pending and will run only
after B is terminal and the worktree is quiet.

## Next step

Let B finish its allowed retry and read its findings. Inspect all three
actual diffs and run parent-owned focused tests in a quiet worktree. Then
dispatch D through the exact DeepSeek/ultra/PLANNING_DISABLED route with
`danger-full-access`, using only `app/api/main.py`, `app/api/deps.py`, and its
own tests/findings. After D, run the affected full regression and dispatch a
fresh independent V1 read-only verifier. No promotion or Program Control
write is authorized.

