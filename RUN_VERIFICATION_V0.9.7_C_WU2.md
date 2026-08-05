# v0.9.7-C Work Unit 2 - Safe Journey Navigation and Midpoint Integration

**Status:** COMPLETE - all 20 WU2 acceptance criteria satisfied (GREEN);
WU3 is the next planned work unit; v0.9.7-C as a whole is NOT complete.
**Date:** 2026-08-05
**Governing protocol:** the owner-provided v0.9.7-C goal (WU2 section) and
`docs/development/V0.9.7_C_SPEC.md` (WU2 section).

## 1. Baseline

- Branch `master`; pre-WU2 HEAD `3acfd91` (WU1 closure). Worktree before
  WU2: only preserved user-owned entries + pre-existing run logs.
- Migration 13; config-v0.9.0; locale parity 572/572 before WU2.

## 2. Implementation delivered

- `app/journey/cycles.py`: `available_actions` populated with stable
  reference descriptors - `open_revision` per submission with a persisted
  feedback record (root + revisions) and `open_practice` per Practice
  target (including legacy and the controlled unlinked-practice group).
  No Feedback action (session-scoped destination by design); no action is
  fabricated for submissions without feedback.
- `app/ui/features/student/navigation.py`: `_navigate_journey_revision`
  and `_navigate_journey_practice` - session state carries references
  only; the practice helper clears any lingering priority intent.
- `app/ui/features/student/revision.py`: fail-safe preset guard - an
  unresolvable `revision_source_preset` renders the honest
  `student_revision_preset_invalid` note instead of silently opening
  another source.
- `app/ui/features/student/practice.py`: fail-safe preset guard - an
  unresolvable or foreign `practice_target_preset` (id + `student_id`
  match) renders `student_practice_preset_invalid`; WU5 stable selection
  semantics preserved.
- `locales/en.json`, `locales/zh_CN.json`: two new keys (574/574 parity).

## 3. Navigation contract (frozen in SPEC)

- Explicit actions only; stable references only; no database writes; no
  creation of targets/exercises/attempts/evaluations/revisions.
- Destinations validate learner ownership; stale/cross-learner references
  fail safely with an honest note.
- Active Practice reuses the existing target; completed Practice remains
  completed; target selection stable across reruns; legacy records expose
  only supported actions.

## 4. Focused tests

New `tests/test_v097c_wu2_journey_navigation.py` (17 tests):

- Cycle actions: full cycle exposes open_revision (root + revision) and
  open_practice; no-feedback and insufficient-evidence cycles expose no
  revision action; legacy and unlinked targets expose open_practice; no
  feedback action is ever exposed.
- Navigation helpers: stable reference + destination page for both
  helpers; practice helper clears lingering priority intent.
- Revision destination guard: valid preset opens the requested source with
  zero writes; stale and cross-learner presets render the honest note.
- Practice destination guard: valid active preset opens the target with
  zero creation; valid completed preset keeps the completed state; stale
  and cross-learner presets render the honest note; rerun keeps the
  Journey selection stable; navigation renders perform zero writes
  (post/revision/target/attempt/complete counters all zero).

Result: **17 passed**. One WU1 assertion (`available_actions == []`) was
superseded by WU2 and updated to pin the new action descriptors
(documented delta).

## 5. Midpoint integration checkpoint

- WU1 + WU2 focused tests, existing Journey tests, affected
  Student/Feedback/Revision/Practice navigation suites, router/API/parity
  contracts: **264 passed / 0 failed / exit 0** under the canonical
  environment (`C:\tmp\wu2-affected\affected_final.txt`).
- Journey read/write checks: whole-database row counts unchanged across
  Journey page renders (smoke) and API reads (WU1/WU2 suites).
- Rendered smoke (real stack, isolated DB, local provider):
  `verification/v0.9.7-c/v0.9.7-c-wu2-20260805-r1/w2_midpoint_smoke.py` -
  English 1280x900 and Chinese 390x844: Journey page renders the raw
  timeline with the additive cycle view, 0 exceptions, 0 overflow, 0 raw
  keys, 0 console/page errors, 0 remote requests; cycle view carries the
  WU2 actions; journey reads perform zero writes
  (`midpoint_smoke_evidence.json`, 2 screenshots).
- Locale parity: 574/574, no missing/empty values.

## 6. Impact review

GitNexus index refreshed at the WU2 implementation tree (11,002 nodes;
265 flows) and `detect-changes` run from the WU1 baseline against a clean
worktree: changed symbols are limited to the cycle action population, the
two navigation helpers, the two destination guards, locale keys, and the
WU2 tests/evidence; no production fan-out outside the intended
Journey/Revision/Practice surfaces (details in section 10 of the final WU2
commit message evidence; full output preserved locally).

## 7. WU2 acceptance criteria

1. Every exposed Journey action has a real destination - PASS (open_revision
   -> Revision source preset; open_practice -> Practice target preset).
2. Every destination uses stable IDs/references - PASS.
3. Learner ownership validated - PASS (candidates/targets are learner-scoped
   API reads + page-level id/learner match).
4. Cross-student references fail safely - PASS (honest note; zero writes).
5. Stale references fail safely - PASS (honest note).
6. Navigation creates no Journey rows - PASS (zero writes; no Journey
   persistence exists).
7. Feedback/Revision navigation cause no unintended write - PASS
   (revision_post_count 0; navigation-only helpers).
8. Active Practice reuses the existing target - PASS.
9. Completed Practice remains completed - PASS.
10. Navigation creates no target/exercise/attempt/evaluation - PASS
    (counters + API path).
11. Target selection stable across reruns - PASS.
12. Legacy records expose no fabricated action - PASS (open_practice only
    for legacy targets; no revision action for no-feedback records).
13. WU1 grouping remains accurate - PASS (WU1 suite green, 29 tests).
14-15. English desktop + Chinese mobile smoke pass - PASS.
16. Locale parity passes - PASS (574/574).
17. Focused and affected tests pass - PASS (17; 264).
18. Impact review shows no unexplained fan-out - PASS.
19. No migration - PASS.
20. User-owned files untouched - PASS.

## 8. Commits and final Git state

- `feat(v0.9.7-c): add safe Student Journey actions`
  - app/journey/cycles.py (actions), app/ui/features/student/navigation.py
    (helpers), app/ui/features/student/revision.py + practice.py
    (fail-safe guards), locales (2 keys, parity 574/574).
- `test(v0.9.7-c): verify Journey navigation and re-entry`
  - tests/test_v097c_wu2_journey_navigation.py (new, 17 tests) + the WU1
    action-descriptor assertion update.
- `docs(v0.9.7-c): close work unit 2`
  - RUN_VERIFICATION_V0.9.7_C_WU2.md (this report), SPEC WU2 section,
    verification/v0.9.7-c/v0.9.7-c-wu2-20260805-r1/ (smoke script,
    evidence JSON, screenshots).

Post-WU2 HEAD recorded in the final chat report. `git status --short`
after the commits shows only the preserved user-owned entries. No push or
pull request (not instructed).

## 9. Gate result

**GREEN** - all 20 acceptance criteria satisfied; no AMBER/RED issues; WU3
(Student Journey Functional UI Closure) may begin. v0.9.7-C remains
incomplete.
