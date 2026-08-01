# RUN VERIFICATION v0.9.3-C

Date: 2026-08-01
Version: v0.9.3-C — Product Journey Hardening and Final v0.9.3 Closure
Spec: docs/development/V0.9.3_C_SPEC.md

## 1. Prerequisite baseline

- v0.9.3-A commits d128734, 2fd768f, f03dcbb; v0.9.3-B commits 5154749,
  f4aa30c; pre-v0.9.4 documentation-only commit b8f1e95 — all present in
  branch history.
- Migration 12; active configuration config-v0.9.0.
- `cmd /c "run.bat --verify"`: PASS (re-run 3 times in this closure).
- No v0.9.4 UI implementation present (verified by git diff scope).

## 2. Confirmed cause of empty Learning Journeys (UX-001)

The Student Journey page rendered events only from `feedback_engagement_traces`
and `transfer_evidence_candidates`. Direct code + database inspection found:

- `PracticeService.create_engagement_trace()` and the repository persistence
  exist but have **zero callers**; the traces table is empty for every learner.
- Transfer evidence, practice targets/exercises/attempts/evaluations and
  within-task response candidates are also empty; the Practice Evaluation,
  within-task response, and transfer flows had **no API or UI wiring**.
- The old empty message ("Submit an essay") contradicted existing data
  (S02 has 10 essays) — DATA-001.

Root cause: **missing event creation after valid actions** (taxonomy cause 3),
plus an unsupported page-view/engagement assumption in the old page (cause 9).
S02's feedback records legitimately contain zero selected priorities
(Diagnostic Gate prompt-term penalty, e.g. essay 13 "parks" matches its
prompt) — represented accurately, not as a defect.

## 3. Journey event semantic contract (implemented)

- Read-time derivation (`app/journey/service.py`) from authoritative source
  records only. Every event carries: event_type, title/description keys +
  params, source_record_type/id, learner_id, task_id, submission_id,
  occurred_at, event_version (`journey-event-v0.9.3-c`), evidence_status
  (confirmed_record | derived_state), limitations, deduplication_key,
  student_visible, research_detail.
- Event types: writing_submitted, revision_submitted, analysis_completed,
  feedback_available, feedback_priority_available, feedback_without_priority,
  insufficient_evidence, practice_available, exercise_attempted,
  practice_evaluation_recorded, within_task_response_observed,
  later_task_evidence.
- No event is created by page rendering, navigation, locale switching, or
  refresh (`get_journey` is strictly read-only; tests assert record counts
  unchanged and zero engagement traces after repeated reads).
- FeedbackEngagementTrace decision: existing model retained; journey does not
  depend on it; page display is never engagement (documented in the Spec and
  Decision Log).

## 4. Deterministic demo workflow

- Learner: `DEMO-001` (is_synthetic=1, namespaced demo ID).
- Commands: `python scripts/demo_journey.py --setup|--status|--cleanup`;
  never runs at startup; local deterministic provider only; prints no secrets.
- Created records (manifest: data/demo_journey_manifest.json, gitignored):
  original essay 18 -> AnalysisRun AR000018 -> feedback with 1 selected
  priority (lexical_repetition, gate-selected) -> Practice Target PT000001
  -> Exercise EX000001 -> Attempt EA000001 -> Evaluation PE000001 -> revised
  essay 19 (linked, Revision Group RG000004) -> Within-task response WTR000001.
- Idempotent: second `--setup` skips (verified; journey counts unchanged).
- Cleanup scope: deletes only DEMO-001 records across all linked tables
  (FK-safe order verified); non-demo rows untouched (tested).
- Backups: data/writing_feedback.pre-v0.9.3c-*.db (4 snapshot files from the
  setup runs; latest 20260801-120153.db).

## 5. Empty-state taxonomy (implemented)

Student Journey now renders accurate classified states: learner not found
(404 -> localized state), no_submissions, submission_without_analysis,
analysis_without_priority (gate suppression), feedback_no_practice_target,
target_no_attempt, attempt_no_evaluation, revision_no_response,
later_task_evidence_none, backend request failed (classified error), and
API starting/degraded/unavailable (existing taxonomy). Every state explains
what is known, what is missing, and one safe next action. Errors are never
shown as empty states.

## 6. Student ID and state consistency

- `app/ui/student_context.py`: normalization (trim whitespace, preserve case,
  reject blank, no silent fallback, no auto-creation) and a shared selected
  learner; switching learners clears learner-scoped session state.
- Verified in browser: learner persists across Student pages; refresh,
  locale switch, and API restart produce no duplicate writes and no stale
  cross-learner data.

## 7. Practice and revision idempotency

- Practice page reuses the existing exercise instance for an active target
  (browser evidence: instances 1 -> 1 after revisit; no duplicate instance).
- Exercise attempts are saved only for valid submissions; empty responses are
  rejected as invalid_input and never persisted.
- Valid attempts are now evaluated with the existing conservative rule-based
  evaluator and persisted (attempt response includes the evaluation);
  revision submissions are linked to the original and Journey shows
  revision_submitted events.
- No automatic retry of state-changing requests (v0.9.3-B policy retained).

## 8. Revision-response semantics

- Within-task response observations use conservative statuses
  (response_candidate_detected / major_rewrite_limits_attribution) and
  limitations that explicitly deny mastery, learning gain, causation, and
  transfer (tests assert the disclaimers and forbid claim language).

## 9. Computer-control verification (real browser)

Evidence: verification/v0.9.3-c/journey_evidence.json,
recovery_evidence.json, api_request_log.txt, 54 screenshots
(verification/v0.9.3-c/screenshots/).

### Complete Student journey (English desktop)

| Step | Result |
|---|---|
| DEMO-001 Home | journey counts + latest event rendered |
| Writing submission (synthetic) | success, visible 1031 ms |
| Feedback | strengths + priorities sections rendered |
| Practice (existing exercise) | instances 1 -> 1 (no duplicate); attempt submitted; evaluation shown |
| Revision (linked draft) | settled, no error |
| Learning Journey | chronological events incl. writing/analysis/feedback/priority/practice/attempt/evaluation/revision/within-task |
| Refresh / leave-return | Journey re-renders (read-only) |
| Chinese locale | Journey renders in Chinese, zero raw keys |
| Locale-switch side effects | no write endpoints invoked (before == after) |

### S02 regression (original user scenario)

- GET /api/v1/students/S02/journey: HTTP 200, request id fa679e6f118f44d1,
  API duration 16 ms, visible ~5 s (bounded), no generic API-unavailable
  message, events rendered, gate note ("no eligible priority") rendered.
- S01 / S999: localized learner-not-found state.
- EMPTY01 (no records): accurate "No submissions yet" empty state with next
  action.

### Researcher journey (English desktop)

Overview (health/counts) -> Evidence (submission 1 audit) -> CALF Measures ->
Learning Process (journey trace with source IDs + counts) -> Research Data
(all 8 tabs) -> System Audit. Student and Research views reconcile on the
same records (counts and source IDs).

### API restart recovery (computer control)

- API killed while Streamlit stays open: Journey shows a classified localized
  error (request_timeout text + Retry action); no hang, no empty state, no
  generic message.
- API restarted: next interaction recovers; no duplicate writes
  (record counts identical before/after).
- Fresh browser session: Journey renders again.

## 10. Four locale/viewport combinations

For en/zh_CN x 1280x900/390x844, ten critical pages each (Home, Writing,
Feedback, Practice, Revision, Learning Journey, Research Overview, Evidence,
Learning Process, System Audit): all rendered, zero console errors, zero page
exceptions, zero page-level overflow, zero raw localization keys.

## 11. Response-time observations

All API calls under the deterministic dataset were below 2 seconds
(responsive category): slowest was POST /api/v1/submissions at 203 ms; journey
retrieval 15-16 ms. No blocking, severe, redundant, or N+1 behavior observed.

## 12. Test results

- Core pytest: 324 passed, 8 skipped (296 baseline + 28 new journey tests).
- Journey suite (tests/test_journey_v093c.py): 28 passed — semantic contract,
  source-record traceability, ordering, deduplication, versioning,
  limitations, read-only/no-render-events/no-engagement-trace, all empty-state
  taxonomy branches, practice idempotency, revision linkage, conservative
  response language, Student ID normalization, demo setup/status/cleanup
  scope, localization parity, S02-pattern regression.
- Cases A-R + live A-G validation: 130 passed (110 + 20).
- Research reliability/integration suites: 45 passed.
- Legacy Playwright harnesses: test_v09_playwright.py 6/6 PASS;
  test_v0921_playwright.py PASS (13 screenshots).
- Pixel Art static style audit: PASS (0 violations).

## 13. Integrated checks (see RUN_VERIFICATION_V0.9.3.md)

- `run.bat --verify`: PASS (3 cold starts).
- Lifecycle: /live 200 (ready), /ready 200 (ready=true), /health 200
  (migration 12); warm restart ready in 1.88 s.
- Research endpoints, error taxonomy, timeout profiles, GET-only retry,
  no-write-retry, request-ID propagation, sanitized logging: PASS (from
  v0.9.3-B suites + API request log evidence in this closure).
- Credential scan on all changed/new files: PASS.
- Sensitive-file scan: PASS (no tracked .db/.pem/.key files; .env.example
  template only).
- Migration 12 unchanged; config-v0.9.0 unchanged.

## 14. Documentation

- docs/development/V0.9.3_C_SPEC.md (pre-fix trace + issue table + contract)
- This report; integrated report RUN_VERIFICATION_V0.9.3.md
- README, CHANGELOG, PROJECT_STATE, docs/ARCHITECTURE, KNOWN_LIMITATIONS,
  MASTER_ROADMAP, DECISION_LOG, CURRENT_TASK_STATE, UI_DESIGN updated

## 15. Remaining limitations

- Practice targets are created through the API/demo path; the Student UI loads
  existing targets (no new target-creation UI added, per scope).
- Within-task response candidates are created by the deterministic demo/API
  path; the UI revision flow records the linked revision without auto-claiming
  a response observation (conservative by design).
- Transfer evidence candidates remain empty for all learners; no comparable
  later-task scenario was manufactured.
- `nlp_model_installed=false` in /health remains the documented cosmetic
  limitation from v0.9.3-A.
