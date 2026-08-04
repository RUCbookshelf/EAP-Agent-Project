# v0.9.7-A Run Verification - Priority-Guided Learning Cycle Completion

**Date:** 2026-08-04
**Run ID:** `v0.9.7-a-20260804-r1`
**Status:** COMPLETE - all acceptance criteria satisfied (see matrix below)
**Implementation + verification commits:** this phase's focused commit

## Baseline

- Branch `master`; pre-change HEAD `41a5ca2` (SPEC baseline `cd62a82`
  legitimately advanced by the frozen priority-path audit closure; not
  force-reset).
- Database migration version: `12`; active configuration: `config-v0.9.0`;
  prompt: `feedback-prompt-v0.7.1`; locale parity before: 540/540.
- Preserved pre-existing user-owned worktree changes (never committed):
  modified `AGENTS.md`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`;
  untracked `.claude/`, `CLAUDE.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`.
- Workflow audit and frozen protocol: `docs/development/V0.9.7_A_WORKFLOW_AUDIT.md`
  (current-workflow reconstruction with `file:line` evidence, G1-G6 gaps,
  UI-only change scope, acceptance/verification matrix); owner spec preserved
  at `docs/development/V0.9.7_A_SPEC.md`.

## Implementation (UI + session state only; zero schema/API/domain/service change)

- `app/ui/features/student/navigation.py`: `_navigate_priority_revision`
  (Feedback -> Revision transfer via `revision_source_preset`) and
  `_finish_revision_cycle` (safe end-of-cycle acknowledgement, clears the
  session saved panel/presets, returns Home).
- `app/ui/features/student/feedback.py`: priority branch now offers primary
  "Open Revision" plus secondary "Open Practice" with an accurate note that
  practice targets are not auto-created from a priority; the old
  "use the selected priority on Practice" copy is no longer used.
- `app/ui/features/student/revision.py`:
  - active-priority task context from the persisted source
    `feedback.priority_feedback` (`_source_priorities` validation);
  - one-active-priority selection (radio when several exist, session-carried
    `revision_priority_selection`, revalidated per render; invalid/stale
    selections fall back to the first priority with an explanatory note);
  - preset consumption (`revision_source_preset`, validated against the
    current learner's candidates);
  - re-entry detection (`_latest_revision_of_source`): a saved revision of
    the selected source renders a completed state instead of a form, so a
    revision is never treated as unsubmitted and no uncontrolled duplicate
    can be created from the page;
  - completion state: revision saved + priority addressed (from the
    submission response trajectory) + record reference + "current revision
    step complete" + next steps (Finish This Revision Cycle -> Home;
    Open Practice with the accurate no-auto-target note; Open Learning
    Journey).
- `locales/en.json`, `locales/zh_CN.json`: 15 new keys, 1:1 parity (555/555).

## Automated verification (exact commands)

1. New focused suite (14 tests):
   `pytest -q -p no:cacheprovider tests\test_v097a_priority_revision_cycle.py`
   -> 14 passed, exit 0.
2. Affected regression (16 suites incl. v0.9.6-C1 no-priority workflow,
   v0.9.6-A linked revision, v0.9.4-B student experience, sidebar, revision,
   practice, UI boundary/parity/port contracts, hybrid components, design
   tokens): 293 passed (14 new + 279 regression), exit 0.
3. Full non-live core (canonical DP0-V1 environment: `PYTHONUTF8=1`,
   `PYTHON_DOTENV_DISABLED=1`, `LLM_PROVIDER=local`, fresh isolated
   `DATABASE_PATH`, `SERVICE_API_DIFF_ALLOWLIST` 26-entry, `DATABASE_URL`
   removed; `--ignore=tests/live`):
   `pytest -q -p no:cacheprovider --ignore=tests/live tests`
   -> 860 passed, 8 skipped, 0 failed, exit 0 (baseline 824/8 preserved;
   +36 = 14 new v0.9.7-A tests and other accumulated regression tests).
4. `run.bat --verify` (exact command, twice): exit 0 both times; launcher
   guard auto-provisioned a temporary isolated database
   (`C:\Users\16073\AppData\Local\Temp\wfm-verify-*.db`), health/docs/
   Streamlit 200/200/200, migration 12, 33 tables, `config-v0.9.0`,
   `feedback-prompt-v0.7.1`; no live provider call.
5. Static gates: `compileall` OK for app/tests/scripts;
   `scripts/pixel_art_style_audit.py` PASS (0 violations); locale parity
   tests PASS (555/555).

## Rendered-page matrix (browser, isolated DB, LLM_PROVIDER=local)

Script: `verification/v0.9.7-a/v0.9.7-a-20260804-r1/v097a_browser_matrix.py`
(harness extension `v097a_harness.py`; stack controller reused from the
v0.9.4-A verification harness). Two full production-path cycles through
Writing -> Feedback -> Open Revision -> priority task -> empty-text
validation -> revision submission -> completion -> Open Practice -> reload
re-entry -> Finish cycle -> Home.

| Combination | Feedback priority | Revision priority task | Completion state | Practice entry (accurate no-target) | Re-entry (no form) | Home after finish |
|---|---|---|---|---|---|---|
| en 1280x900 | PASS | PASS | PASS | PASS | PASS | PASS |
| zh_CN 390x844 | PASS | PASS | PASS | PASS | PASS | PASS |

- Persisted after each cycle (direct SQLite evidence): essays 2,
  linked revisions 1, revision groups 1, revision snapshots 1.
- Zero-write renders: priority task render and empty-text validation added
  no records.
- Console errors 0, page errors 0, uncaught exceptions 0, remote-resource
  requests 0 in both combinations.
- No horizontal overflow, no raw locale keys, main content width 720px;
  mobile primary controls measured >= 44px; mobile sidebar closed before
  each interaction (Streamlit 1.60 header-expand helper).
- Screenshots (12 meaningful): `verification/v0.9.7-a/v0.9.7-a-20260804-r1/screenshots/`
  (feedback priority, revision priority task, revision completed, practice
  no-target, re-entry completed, home after finish x en desktop/zh mobile).
- Evidence JSON: `rendered_page_matrix_evidence.json`; run logs under
  `logs/` (file-backed, gitignored).

## Acceptance criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Priority moves Feedback -> Revision | PASS | AppTest + browser EN/ZH click-through |
| 2 | Revision displays active priority + task | PASS | Page tests + screenshots + DOM asserts |
| 3 | Revision submission associated with priority | PASS | submit carries `revision_of_submission_id`; trajectory shows source priorities |
| 4 | Revision genuinely persisted | PASS | DB counts 2/1/1/1 after each cycle |
| 5 | Explicit completion state | PASS | Completion assertions EN + ZH |
| 6 | Safe end of cycle | PASS | Finish cycle -> Home; session cleared |
| 7 | Accurate next step | PASS | Practice note + Home CTA copy |
| 8 | No implied auto Priority-to-Practice | PASS | Old copy removed; practice note asserted in tests + browser |
| 9 | Refresh/rerun/locale/clicks safe | PASS | AppTest rerun/locale tests; browser reload re-entry; 555/555 parity |
| 10 | No cross-student/essay/feedback/priority associations | PASS | Server guards unchanged (v0.9.6-A suite green); page-level learner guards + preset validation |
| 11 | Baseline behavior intact | PASS | Full core 859/8 exit 0; affected regressions green; run.bat --verify PASS |
| 12 | Automated + rendered verification passes | PASS | See above |
| 13 | User-owned files unchanged | PASS | Final `git status` (see below) |
| 14 | `detect_changes` review | PASS | GitNexus detect_changes: 8 changed files; changed symbols limited to feedback/revision renderers (+ docs/tests/locales); risk medium, no unexpected flows |
| 15 | Reproducible evidence | PASS | file:line, test counts, logs, screenshots, evidence JSON |

## Known limitations

- CRG MCP `get_minimal_context`/`list_graph_stats` timed out on the sandbox
  permission review (tooling limitation); GitNexus MCP was used instead for
  impact analysis and the final `detect_changes` review (index 6 commits
  behind HEAD; affected symbols unchanged since the indexed commit).
- The local image-viewer could not open the preserved PNGs in this
  environment; screenshots are retained for the owner, and all content
  assertions were verified at the DOM/text level.
- apply_patch's filesystem helper failed mid-session
  (`helper_unknown_error`); file edits were applied with deterministic
  UTF-8 PowerShell/Python writes and verified by compile/import checks and
  the full test suite.
- The isolated verification database copy remains under the run directory
  (synthetic learners only; policy blocked automated deletion).

## Final Git state

- Focused commit(s) for this phase contain only: app UI changes, locales,
  new tests, phase docs, and verification evidence. Pre-existing user-owned
  modifications and untracked files remain uncommitted and unchanged.
- `git status --short` at closure reports the preserved user-owned entries
  separately from the committed project changes.