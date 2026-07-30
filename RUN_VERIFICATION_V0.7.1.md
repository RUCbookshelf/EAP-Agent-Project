# v0.7.1 run verification

Date: 2026-07-30. Scope: Longitudinal Reliability & UI Polish only.

## Automated gates

- Starting baseline: 195 passed, 3 skipped.
- Focused reliability/router gate: 28 passed.
- Live DeepSeek A–C test: 1 passed; the test is opt-in with `RUN_LIVE_LLM_TESTS=1`.
- Final normal suite: 209 passed, 4 opt-in live tests skipped; two known dependency deprecation warnings.

## Live DeepSeek A–C

The sanitized verifier is `python -m scripts.verify_live_deepseek_v071`. It creates isolated temporary databases, uses LocalDemo only to seed prior records for B/C, makes one live final call per scenario, asserts the contract, emits no raw response or credential, and removes its temporary directory.

- **Live A:** external DeepSeek success, no fallback, status `unavailable`, zero History Evidence IDs.
- **Live B:** external DeepSeek success, no fallback, two linked drafts in one Revision Group, one independent task, revision feedback present, cross-task status remains `unavailable`, and no “single draft analysis” wording.
- **Live C:** external DeepSeek success, no fallback, three comparable independent tasks, `provisional_pattern`, at least one supplied History Evidence ID, no invented ID and no long-term-trend claim.

Final sanitized run (`deepseek-v4-flash`):

| Scenario | Initial validation | Corrections | Server repair | Fallback | Validation | Latency |
|---|---:|---:|---|---|---|---:|
| Live A | passed | 0 | none | false | passed | 14.100 s |
| Live B | failed | 1 | none | false | passed | 30.109 s |
| Live C | core_passed | 0 | `longitudinal_assessment.comment` | false | passed_with_server_repair | 11.851 s |

Live C cited supplied `HE000002`; A/B correctly cited none. All sanitized fallback reason codes were null.

## Rendered UI QA

The Browser plugin was unavailable, so the required fallback used bundled Playwright Chromium against real local FastAPI and Streamlit processes.

- Desktop 1440×1000: submission completed; all five tabs found; Student and Research audit views rendered.
- Mobile 390×844: form, mode switch and independent/revision controls rendered without horizontal overflow.
- Browser console/page errors: 0.
- Screenshots: `v071-desktop-student.png`, `v071-desktop-research.png`, `v071-mobile-form.png` in the Codex visualization output folder.

## Security and migration gates

- Migration 9 is additive; test coverage verifies saved provider status, preserved essay data, logical rollback to migration 8/config-v0.7.0, and re-upgrade to config-v0.7.1.
- Prompt manifest hashes are validated at startup and in tests.
- Tracked `.env`, database, log and archive count: 0. Tracked secret-pattern hits: 0. `.env` Git-history commits: 0. Repository log files: 0.
- All 13 local SQLite verification/demo databases scanned had 0 credential-pattern hits. Working database migration/config are 9/`config-v0.7.1`; retained row counts are essays 5, analysis runs 5, feedback 5, revision snapshots 3 and learner-profile snapshots 5.

## Final release gate

- `run.bat --verify`: PASS.
- FastAPI health: 200; API docs: 200; Streamlit: 200.
- Prompt: `feedback-prompt-v0.7.1`; schema: `structured-feedback-v0.7.1`; migration: 9; active configuration: `config-v0.7.1`.
- Required independent commit message: `fix(v0.7.1): harden longitudinal feedback and refine prototype UI`.
- v0.8 and every objective-listed out-of-scope item remain not started.
