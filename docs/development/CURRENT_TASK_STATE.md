# Current Task State

## Completed task

v0.7.1 Longitudinal Reliability & UI Polish — `completed`.

## Verified baseline — 2026-07-30

- Branch `master`; baseline commit `6e7835d`; clean worktree before v0.7.1 edits.
- Recovery tag `pre-v0.7.1-baseline-20260730`.
- Normal tests: `195 passed, 3 skipped`; two known deprecation warnings.
- Database migration 8; active `config-v0.7.0`; application 0.7.0; DeepSeek `deepseek-v4-flash` configured locally.
- FastAPI health 200; API docs 200; Streamlit 200; `run.bat --verify` PASS.
- Isolated live no-history call reproduced the exact first-response longitudinal wording failure. The broad correction succeeded with retry 1 and no fallback on this run, confirming an intermittent fallback risk rather than an API connection failure.
- Isolated four-draft task confirmed 4 drafts, 1 Revision Group, 1 independent task and 1 representative. It also reproduced zero priority/practice/previous-priority/uptake content that currently leaves empty UI headings.

## Completion gate — 2026-07-30

- Backend-owned longitudinal facts, conservative field repair, provider execution status, Positive Finding guardrails, Within-task Revision Trajectory, API fields, `config-v0.7.1`, and the five-tab Streamlit UI are implemented.
- Normal suite: `209 passed, 4 skipped`; skipped tests are explicit live-provider tests. Focused reliability/router gate: `28 passed`.
- DeepSeek Live A–C passed with `deepseek-v4-flash`; every scenario used fallback false. Live A passed directly, Live B passed after one correction, and Live C passed with server repair of only `longitudinal_assessment.comment`.
- Playwright desktop/mobile QA passed with zero browser-console/page errors. View rerender testing preserved feedback and Learner Profile Snapshot row counts.
- Migration 9 and active `config-v0.7.1` verified. Working database retained 5 essays, 5 analysis runs, 5 feedback rows, 3 revision snapshots and 5 learner-profile snapshots.
- `run.bat --verify` PASS; FastAPI health 200; API docs 200; Streamlit 200. Tracked-file, Git-history, log and database scans found no credential pattern.
- Required documentation is synchronized. The independent commit is the final action; v0.8, CALF and every other out-of-scope feature remain `not_started`.
