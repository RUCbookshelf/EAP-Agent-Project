# PDW2-D-UX-STUDENT REPAIR - Wave-2 Integration Wiring (UX)
Goal: PDW2-D-UX-STUDENT__REPAIR-INTEGRATION (REPAIR, dispatched by PROGRAM).
| Field | Value |
| --- | --- |
| Owner | UX |
| Worktree | A:\EAP Agent Project\worktrees\frontend |
| Branch | dept/frontend |
| Starting SHA (parent) | 1c89454e7f5a2c9b05138e1852320c0b01c578f2 |
| Verdict | GREEN |
| Promotion / push / PR | none (promotion authority false) |
## What was wired (INT steps 1-2 of PDW2-D-UX-STUDENT-20260810.md)
1. Pages mounted in the real Streamlit entry: app/ui/streamlit_app.py
   STUDENT_PAGES now contains student_wave2_studio ->
   student_wave2_studio_title and student_wave2_history ->
   student_wave2_history_title (appended after student_journey), and run()
   routes them to render_wave2_studio_page(gateway, lang) /
   render_wave2_history_page(gateway, lang).
2. Gateway built once per app with mode=auto: new cached factory
   get_wave2_gateway(base_url) constructs
   Wave2Gateway(Wave2ApiClient(base_url), WritingFeedbackApiClient(base_url),
   mode="auto"); the legacy client is the same cached
   WritingFeedbackApiClient the rest of the app uses. auto probes the
   Wave-2 namespace once: guided when the Wave-2 endpoints are available,
   graceful degradation to the existing writing/feedback flow otherwise
   (honest standard-mode notices, no fabricated Wave-2 features).
3. Wave-2 strings resolve through the additive runtime locale registration
   (app/ui/wave2/locale.py); the frozen locales/*.json files are untouched
   (INT step 3, optional, not applied).
4. Home entry card (INT step 4, optional) was not added, keeping the diff to
   wiring only.
## Test evidence (all GREEN)
- tests/wave2 74 passed (69 prior + 5 new wiring tests in
  tests/wave2/test_wave2_integration_wiring.py): navigation contract and
  locale resolution, gateway factory shape (Wave2ApiClient +
  WritingFeedbackApiClient + mode auto), studio page rendering through the
  real entry (standard-mode degradation), history page rendering through the
  real entry (honest standard note + empty state), and regression pass over
  the six pre-existing student pages.
- Affected Streamlit navigation/entry suites: test_streamlit.py 5 passed /
  1 skipped (pre-existing skip), test_hybrid_components_v094a.py 23 passed,
  test_v095c_feature_extraction.py 8 passed (pinned navigation contract
  updated to the new 8-page order), test_v097c_wu2_journey_navigation.py
  17 passed, test_v097c_wu3_journey_ui.py 21 passed,
  test_v097a_priority_revision_cycle.py 14 passed,
  test_student_experience_v094b.py 27 passed.
- test_v096c2_sidebar_control.py 18 passed (5 source-level + 13 Playwright
  browser tests, incl. the page-consistency checks, run with the headless
  browser outside the sandbox because the sandbox denies browser process
  spawn).
- Totals: 207 passed, 1 skipped, 0 failed.
## Scope / hygiene
- Changed files (commit scope): app/ui/streamlit_app.py (+28),
  tests/test_v095c_feature_extraction.py (+2, pinned navigation contract),
  tests/wave2/test_wave2_integration_wiring.py (new, 5 tests), this report.
- No backend module touched (app/api, app/services, app/learner, app/l2,
  app/corpus, app/database, app/infrastructure untouched); no
  reset/clean/rebase/push/PR/promotion; no raw SWECCL access; no network
  calls in tests (the wiring tests probe a dead port for graceful
  degradation, which fails closed locally).
- Pre-existing untracked evidence preserved byte-identically:
  docs/integration/PDW1-ALIGN-UX-B6FCE9-20260809.md,
  docs/integration/PDW2-ALIGN-UX-59500127-20260810.md,
  docs/integration/PDW2-D-UX-STUDENT-20260810.handoff.json,
  docs/integration/UX-V097-E-accessibility-refinement.md, handoff.json.
- Test artifacts (/pytest_cache, .cache/) are gitignored.
## Findings / limitations
- The studio/history session state (wave2_* keys) remains session-local and
  is not yet added to student_context.LEARNER_SCOPED_KEYS (recorded in the
  PDW2-D report as a follow-up; out of scope for this wiring repair).
- Wave-2 guided features activate only when the Wave-2 endpoints land at
  integration; until then the mounted pages render the standard flow with
  honest notices (verified by the AppTest wiring tests against a dead port).
