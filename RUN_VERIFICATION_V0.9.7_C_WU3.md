# v0.9.7-C Work Unit 3 - Student Journey Functional UI Closure

**Status:** COMPLETE - all 26 WU3 acceptance criteria satisfied (GREEN);
WU4 is the next planned work unit; v0.9.7-C as a whole is NOT complete.
**Date:** 2026-08-05
**Governing protocol:** the owner-provided v0.9.7-C goal (WU3 section) and
`docs/development/V0.9.7_C_SPEC.md` (WU3 section).

## 1. Baseline

- Branch `master`; pre-WU3 HEAD `0af31f2` (WU2 closure). Worktree before
  WU3: only preserved user-owned entries + pre-existing run logs.
- Migration 13; config-v0.9.0; locale parity 574/574 before WU3.

## 2. Implementation delivered

- `app/ui/features/student/journey.py`: grouped cycle rendering - cycle
  cards (cycle stage badge, unlinked warning), original/revision blocks
  with writing states and honest descriptions, feedback stages with
  priority count and category labels, Practice activity blocks (target
  label, activity state badge, valid/legacy/unresolved provenance notes,
  attempt reference, completed wording or evaluation-unavailable notice),
  safe Open Revision / Open Practice buttons per block, cycle limitations.
  The raw timeline remains only as a defensive fallback when no cycle data
  exists.
- Fix (found by the new API-error test): `render_api_error` was called by
  the Journey page without being imported - a pre-existing latent error
  path; the import is added and covered by a test.
- `tests/harness_v097a_student.py`: `learning_journey` renderer added to
  the AppTest harness (additive).
- `locales/en.json`, `locales/zh_CN.json`: 26 new structural/state/action
  keys (600/600 parity, no missing/empty values).

## 3. Page structure and wording

Documented in SPEC section 3: cycle-level grouping with original/revision
distinction, feedback/priority relationships, Practice attachment, state
badges via existing components, safe actions, and honest empty/error/
legacy handling. Completion wording reuses the WU5 allowed strings;
no mastery/pass/improvement/CEFR/proficiency/transfer/learning-gain
claims (the only "passed"/"transfer" text is inside the fixed
conservative disclaimers and the Diagnostic-Gate description, which the
matrix asserts as exclusions).

## 4. Focused tests

New `tests/test_v097c_wu3_journey_ui.py` (21 tests):

- Cycle rendering: full cycle sections (title, original #id, revised
  draft #id + revision-of caption, feedback, practice activity, state
  labels, completed wording, priority reference caption); multiple cycles
  render distinguishably in order; original/revision distinction; action
  presence and absence; unlinked warning; legacy and unresolved provenance
  notes.
- Practice states: available; completed (allowed wording, attempt
  reference, no finish button); completed without evaluation (honest);
  evaluation-unavailable (attempt saved + honest notice).
- Writing states: no-priority and insufficient-evidence with their honest
  descriptions.
- Navigation: Open Revision and Open Practice buttons navigate through the
  WU2 helpers with zero writes; rerun stable; rendering performs zero
  writes.
- Empty and API-error states (the API-error test exposed and now covers
  the fixed missing-import defect).
- Chinese localization: all structural/state/action copy localized; no
  English cycle copy leaks.

Result: **21 passed**.

## 5. Rendered matrix (all four combinations)

`verification/v0.9.7-c/v0.9.7-c-wu3-20260805-r1/w3_browser_matrix.py` ran
the affected Journey path independently with fresh isolated databases and
distinct learners (local provider):

| Combination | Grouped cycles | States | Actions | Reload | Zero writes |
|---|---|---|---|---|---|
| en 1280x900 | PASS | PASS | PASS | PASS | PASS |
| zh_CN 1280x900 | PASS | PASS | PASS | PASS | PASS |
| en 390x844 | PASS | PASS | PASS (>=44px) | PASS | PASS |
| zh_CN 390x844 | PASS | PASS | PASS (>=44px) | PASS | PASS |

Each combination seeded one completed priority-derived cycle with a linked
revision, one active target, one evaluation-unavailable activity, one
completed legacy target, one no-priority cycle, and one
insufficient-evidence cycle. Verified: grouped cycle UI with correct
relationship text and chronology, active/completed/evaluation-unavailable/
no-priority/insufficient/legacy states, safe action buttons (Open Revision
and Open Practice with stable keys), mobile action sizing >= 44px, action
navigation to the active target, reload re-entry, whole-database counts
unchanged across all Journey reads/navigation, 0 console errors, 0 page
errors, 0 remote requests, no overflow, no raw keys, no unsupported
learning claims. Evidence:
`rendered_page_matrix_evidence.json` + 4 screenshots.

## 6. Affected regression

19 suites (WU1-WU3, Journey v0.9.3-C, F4 narrowing, v0.9.7-A revision,
v0.9.6-C1 no-priority, v0.9.7-B WU2-WU6, student experience, UI
boundaries/feature extraction, sidebar, parity, API/router contracts):
**427 passed / 0 failed / exit 0** under the canonical environment
(`C:\tmp\wu3-affected\affected_final.txt`).

## 7. Static checks

- `compileall` OK; `git diff --check` clean on all WU3 files.
- Locale parity 600/600 measured (not assumed); no migration; no
  user-owned file touched.

## 8. WU3 acceptance criteria

1-2. Coherent cycles; multiple cycles distinguishable - PASS.
3. Original/revision relationships clear - PASS.
4. Feedback and priority relationships clear - PASS.
5. Practice attached to the correct cycle - PASS.
6. Active and completed states visibly distinct - PASS.
7. Evaluation unavailable honest - PASS.
8. No-priority and insufficient-evidence understandable - PASS.
9. Legacy data without fabricated provenance - PASS.
10. Safe actions render only when supported - PASS (WU2 action contract;
    absence tests).
11. Completed Practice re-entry works - PASS (rendered + action
    navigation).
12. Journey rendering creates no writes - PASS (whole-DB counts).
13. No automatic target creation/sequencing - PASS (zero counters; no
    creation paths).
14-17. EN/ZH x desktop/mobile pass - PASS.
18. No console/page errors - PASS.
19. No raw locale keys - PASS.
20. No horizontal overflow - PASS.
21. No remote UI resources - PASS.
22. No mastery/pass/improvement/CEFR/proficiency/transfer/learning-gain
    claim - PASS (fixed disclaimer exclusions asserted).
23. Focused tests pass - PASS (21).
24. Affected regression passes - PASS (427).
25. No migration - PASS.
26. User-owned files untouched - PASS.

## 9. Commits and final Git state

- `feat(v0.9.7-c): render grouped Student Journey cycles`
  - app/ui/features/student/journey.py (grouped renderer + error-path
    import fix), locales (26 keys, parity 600/600).
- `test(v0.9.7-c): verify Journey functional UI states`
  - tests/test_v097c_wu3_journey_ui.py (new, 21 tests),
    tests/harness_v097a_student.py (journey renderer entry).
- `docs(v0.9.7-c): close work unit 3`
  - RUN_VERIFICATION_V0.9.7_C_WU3.md (this report), SPEC WU3 section,
    verification/v0.9.7-c/v0.9.7-c-wu3-20260805-r1/ (matrix script,
    evidence JSON, screenshots).

Post-WU3 HEAD recorded in the final chat report. `git status --short`
after the commits shows only the preserved user-owned entries. No push or
pull request (not instructed).

## 10. Gate result

**GREEN** - all 26 acceptance criteria satisfied; no AMBER/RED issues; WU4
(Final Verification and v0.9.7-C Release Closure) may begin. v0.9.7-C
remains incomplete.
