# Current Task State

## Active task

v0.8 CALF Measurement Foundation — `completed` on 2026-07-30. v0.9 is `not_started`.

The authorized scope is frozen in `docs/development/v0.8_SPEC.md`. Every excluded scoring, CEFR, model-training, full teacher-platform, paid-service, cloud, WeChat, and v0.9 item remains `not_started`.

## Verified pre-coding baseline

- Branch `master`; clean starting commit `168d723`; annotated recovery tag `pre-v0.8-baseline-20260730`.
- Baseline suite: 209 passed, 4 skipped. Baseline `run.bat --verify` passed FastAPI, docs, and Streamlit.
- Working database began at migration 9 / `config-v0.7.1`; historical essays, AnalysisRuns, MetricResults, snapshots, revisions, and feedback parsed successfully.
- `.env` and the database were ignored; Git history contained no `.env`; no credential was printed or recorded.
- Existing timed-writing data provided a limit but no actual duration, so the limit was explicitly barred from WPM.

## Completed v0.8 implementation

- Registered 4 constructs, 22 measurement specifications, and 14 analysis units.
- Implemented deterministic MTLD/HD-D with inspectable intermediates and short-text policies; preserved TTR/MATTR/density protocols.
- Added research-only syntactic candidates, explicit human promotion, append-only error annotations, and unavailable Accuracy/sophistication states without fake zeros.
- Added actual-duration-only writing output rate, timing provenance, and a descriptive-proxy boundary.
- Added migration 10, immutable child `config-v0.8.0`, new provenance columns/tables, logical rollback/re-upgrade, CALF APIs, local reanalysis, exact-version/task-condition trajectories, and a research-only Streamlit tab.
- Kept CALF-only data outside Diagnostic Gate priorities, exercises, student totals, and default feedback prompts.

## Verification gates

- Full automated suite passed: 225 passed, 5 skipped; Cases A–M cover the CALF contracts and isolation rules.
- Live A–D passed: real DeepSeek A/B had first-pass structured validation, no correction, no server repair, and no fallback; controlled C/D proved missing-duration null behavior and reproducible 13.8 WPM.
- `run.bat --verify` passed migration 10, initialization, FastAPI health 200, docs 200, and Streamlit 200.
- Browser plugin was unavailable. Playwright 1.62 with installed Microsoft Edge passed the submission → research view → CALF tab flow on desktop and 390×844 mobile with no console errors. This check found and corrected the stale v0.7.1 page title. On mobile, long tab labels truncate at the right edge but remain operable after closing the sidebar.
- Documentation, references, human-review guidance, security boundaries, and the v0.8 verification report were completed.

The v0.8 release is finalized by the isolated Git commit containing this state record. Work stops there; v0.9 is not authorized.
