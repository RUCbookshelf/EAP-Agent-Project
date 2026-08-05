# v0.9.7-B Work Unit 4 - Focused Practice Task and Attempt Loop

**Stage:** v0.9.7-B Work Unit 4 (implementation)
**Status:** COMPLETE - all 36 WU4 acceptance criteria satisfied; WU5 is the
next planned work unit; v0.9.7-B as a whole is NOT complete.
**Date:** 2026-08-05
**Governing protocol:** the owner-provided WU4 work-unit objective,
docs/development/V0.9.7_B_SPEC.md (frozen by WU1), and the WU2/WU3 closure
reports.

## 1. Starting and ending Git state

- Branch: `master` (unchanged).
- Starting HEAD: `94ff43a` (post-WU3 closure; matches the owner report).
- Ending HEAD: the final `docs(v0.9.7-b): close work unit 4` commit on
  `master` (exact hash reported in the final chat report; the unit's stable
  commit hashes are listed in section 29).
- Worktree before implementation: only preserved user-owned entries
  (`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
  `RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`) plus the gitignored v0.9.7-a logs.

## 2. WU4 objective and exact stage boundary

WU4 connects the WU3 priority-derived target to a focused, understandable,
reliable Practice task and one persisted attempt: resolve the target,
re-resolve its persisted priority context, reuse/create one current
exercise, render the focused task, validate and persist one attempt, show an
explicit saved state, and recover after rerun/refresh/failure/re-entry.
Evaluation remains the existing side effect (unchanged); target COMPLETED,
completion actions, and Journey changes remain WU5/WU6.

## 3. Baseline discrepancy

None. The owner-reported post-WU3 state (master @ `94ff43a`, migration 13,
969 passed / 8 skipped) matched the actual checkout exactly.

## 4. Minimum Completion Units 4.0-4.6 and results

- **4.0 Reconnaissance + protocol**: reconstructed the full current flow
  with file:line evidence (Feedback Open Practice was a plain navigation
  without intent; Revision Open Practice likewise; the Practice page selected
  the oldest active target with no preset, no context display, manual source
  paste, and no attempt ownership validation at the API). Protocol frozen and
  recorded before implementation.
- **4.1 Entry + target selection**: implemented and tested (below).
- **4.2 Priority-context resolver**: implemented and tested (below).
- **4.3 Exercise + task rendering**: implemented and tested (below).
- **4.4 Reliable attempt submission**: implemented and tested (below).
- **4.5 Saved state + recovery**: implemented and tested (below).
- **4.6 Integration closure**: combined suites, affected regression, full
  core, launcher, rendered matrix, and impact review all pass (sections
  18-22). No target completion, completion action, next-target sequencing,
  or Journey event was implemented (scope guards + rendered checks).

## 5. Current-before and implemented-after workflow

Before: Feedback/Revision Open Practice navigated without intent; Practice
always rendered the oldest active target with only its label, required
manual source-text paste, and submitted attempts without ownership checks.

After: Feedback renders one "Practice this priority" action per priority
card; Revision completion carries the addressed priority; the Practice page
consumes the explicit intent through the server (WU3 create-or-reuse),
ensures one current exercise seeded from the persisted evidence quote,
renders the focused task (priority, why, direction, evidence, instruction,
response field), validates and persists one owned attempt, and restores the
saved state from persistence on rerun/refresh/re-entry.

## 6. Practice entry and target-selection design

- New navigation helper `_navigate_priority_practice(source_submission_id,
  priority_index, lang)` (app/ui/features/student/navigation.py) carries only
  persisted-reference components in session state
  (`practice_source_submission_id`, `practice_priority_index`); no priority
  content is copied into session state.
- Feedback (app/ui/features/student/feedback.py): one explicit
  `feedback_practice_priority_{index}` button per priority card (index is
  the zero-based position in the persisted priority list).
- Revision (app/ui/features/student/revision.py): the completion Open
  Practice action carries `(revision_of_submission_id,
  revision_priority_index)`.
- Practice page (app/ui/features/student/practice.py): `_consume_practice_intent`
  posts the intent form to the server; the server assembles the stable
  reference (never the UI), runs WU3 create-or-reuse, and the returned target
  id becomes `practice_target_preset`. Non-retryable failures clear the
  intent with an honest note; transient failures keep it for an idempotent
  retry. The preset is validated against the learner's ACTIVE target list
  (stale/cross-learner presets are ignored and the deterministic oldest-active
  rule applies). Direct navigation never fabricates a target.
- Intent keys are learner-scoped: switching learners clears them
  (app/ui/student_context.py).

## 7. Target-context resolution architecture

- New `PracticeTaskContextService` (app/practice/task_context.py), read-only
  and learner-owned: target existence (404), target ownership (403), then
  either the priority-derived branch (parse the stable reference server-side,
  load the persisted bundle, re-run the WU2 relationship checks through
  `build_target_contract`, and verify target-code/category consistency) or
  the legacy branch (existing path, `priority_context: null`, no fabricated
  provenance). Provenance that no longer resolves returns a controlled
  `context_status: "unavailable"` payload with a stable reason; malformed
  stored rows raise a controlled 422.
- New read endpoint `GET /api/v1/students/{student_id}/practice-targets/
  {practice_target_id}/context` (require_student + ownership), plus the UI
  client method `get_practice_target_context` and the port entry.
- UI code does not parse or construct the stable reference anywhere.

## 8. Exercise selection and seeding rule

- `_ensure_current_exercise` (entry action only): reuse the latest existing
  instance; create exactly one only when none exists, seeded with
  `priority_context.evidence_quote`; failures degrade to the existing manual
  generate step (recoverable, never a fabricated task). Repeated renders,
  locale switches, and refreshes reuse the persisted instance (no
  uncontrolled duplicates).
- The manual generate step pre-fills the source text area with the persisted
  evidence quote when available.

## 9. Attempt validation and persistence path

- Server (`POST /api/v1/exercises/{exercise_id}/attempts`): exercise
  existence (404), target existence (404), and learner ownership
  (exercise.student_id and target.student_id must equal the payload
  student_id; cross-student -> 403 with zero writes). Valid input persists
  one attempt; the existing rule-based evaluation side effect continues
  unchanged (attempt authoritative, evaluation best-effort).

## 10. One-action/one-attempt protection

- Shared pending guard (submit_reliability.py, new PRACTICE_ATTEMPT mode):
  `enter_pending` before the POST, `release_pending` after a terminal result,
  `consume_pending` on a queued duplicate click/refresh while in flight. After
  success the page shows the saved-state branch (no submit form), and the
  page reloads attempts from persistence on rerun; a response arriving after
  a rerun is reconciled against the persisted attempt.
- WU3 idempotent target creation remains the entry backstop; no
  database rule prohibits legitimate future retries or multiple intentional
  attempts (attempt_number stays server-computed).

## 11. Failure and partial-success behavior

- Submission failure: `render_api_error`, input preserved (widget state),
  target/exercise retained, no duplicate on retry (pending guard), zero new
  records.
- Attempt persisted but evaluation failed: the attempt remains authoritative
  and the page shows the saved state with the explicit evaluation-unavailable
  notice (pre-existing truthfulness preserved; verified by the existing
  failure-matrix tests and the WU4 suite).
- Invalid/stale/cross-learner intents: no target, safe note, no exception.

## 12. Saved-attempt and re-entry behavior

- Saved state shows the saved confirmation, the attempt reference
  (`#EA######` caption), the submitted response, the existing evaluation
  block (or the unavailable notice), and no WU5 actions.
- Re-entry (refresh/rerun/locale switch/direct navigation/return via
  Feedback/Revision) reloads attempts from persistence and shows the saved
  state; the latest valid attempt is deterministic (`attempts[-1]`);
  historical attempts are never deleted or overwritten; a saved attempt is
  never treated as unsubmitted.

## 13. Existing evaluation behavior preserved

- No evaluation criteria, wording, or persistence change; the evaluation
  side effect still runs after attempt persistence and is still best-effort.
- No mastery/learning-gain/completion claim is introduced; the WU4 success
  statement remains "Your practice response was saved."

## 14. Confirmation that no target completion was implemented

- No COMPLETED status, no completion persistence, no Finish/Continue
  actions, no automatic next-target sequencing, no new Journey events
  (verified by scope-guard tests, the rendered matrix's absence checks, and
  the diff review).

## 15. Modified files and purposes

- `app/practice/task_context.py` (new): read-only task-context resolver.
- `app/practice/mapping.py`: `resolve_target_contract_by_components` (entry
  intent resolution; stable reference assembled server-side) +
  type-checked `priority_index` in `build_target_contract`.
- `app/practice/target_creation.py`: `create_or_reuse_from_intent`.
- `app/api/routers/practice.py`: intent form on `POST /practice-targets`,
  new context GET endpoint, attempt ownership validation.
- `app/ui/features/student/navigation.py`: `_navigate_priority_practice`.
- `app/ui/features/student/feedback.py`: per-priority Open Practice actions.
- `app/ui/features/student/revision.py`: completion Open Practice carries
  the addressed priority.
- `app/ui/features/student/practice.py`: intent consumption, preset
  selection, context fetch, focused task rendering, seeded source text,
  pending-guarded submission, saved-state reference.
- `app/ui/features/student/submit_reliability.py`: PRACTICE_ATTEMPT mode.
- `app/ui/student_context.py`: practice intent/preset keys are learner-scoped.
- `app/ui/ports/student.py`, `app/ui/api_client.py`: context read method +
  port entry (`create_practice_target` moved into the practice port).
- `locales/en.json`, `locales/zh_CN.json`: 8 new keys, 2 note texts updated
  to describe the explicit transfer (parity 563/563).
- `tests/contracts/api_surface_contract.py`, `tests/test_v095d_api_contract.py`,
  `tests/test_v095b_router_contract.py`, `tests/test_v095f6d_...py`,
  `tests/test_v095h2d2_...py`, `tests/test_v096b_...py`: surface/route/
  dependency-graph/client-count contracts updated for the new endpoint,
  port method, and client method.
- `tests/harness_v097a_student.py`, `tests/test_v097a_priority_revision_cycle.py`,
  `tests/test_v096c1_no_priority_workflow.py`: WU4 entry flow + fake client.
- `verification/v0.9.5-h2d2/dependency_graph_*`, `openapi_*`: refreshed for
  the new endpoint/dependencies.
- `verification/v0.9.5-h2a/isolated_pytest_runner.py` +
  `verification/v0.9.6-dp0-v1/canonical_full_core_command.txt`: canonical
  allowlist 29 -> 30 entries (task_context.py).
- `tests/test_v097b_wu4_practice_task.py` (new, 32 tests) and the run
  directory `verification/v0.9.7-b/v0.9.7-b-wu4-20260805-r1/` (matrix
  scripts, screenshots, evidence).

## 16. Tests added or modified

New `tests/test_v097b_wu4_practice_task.py` (32 tests):

- Entry intent API: intent creates the target with the server-resolved
  reference, repeated requests reuse, cross-student 403, missing submission
  404, out-of-range/negative/malformed index 422, source_priority_id form
  precedence, zero writes on failure.
- Task context API: exact persisted context, cross-student 403, missing
  target 404, unknown learner 404, stale index and malformed reference ->
  controlled unavailable, legacy branch, zero writes on reads.
- Attempt ownership API: cross-student 403 with zero writes, missing target
  404, valid attempt persists.
- Page tests (AppTest harness): Feedback per-priority button transfers the
  intent and the Practice page consumes it exactly once; Revision completion
  transfers the addressed priority; repeated entry reuses the target; direct
  navigation creates nothing; invalid intent shows the note; stale preset
  falls back deterministically; focused task renders the persisted context;
  unavailable context renders the limitation note; saved attempt shows the
  reference; pending marker consumes duplicates; empty response writes
  nothing; valid submission persists and rerun shows the saved state.

Modified: v0.9.7-A Feedback-button assertions (per-card actions), v0.9.6-C1
button label (locale-key based), API-surface/route/dependency contracts
(new endpoint + port method + client method), client-method count 53 -> 54.
No valid test was deleted, skipped, or weakened.

## 17. Migration decision

No migration (14 is not added). Evidence: context re-resolution, target
presets, exercise seeding, attempt persistence, and saved-attempt recovery
all use existing tables/JSON (migration 13 preserved; WU3 uniqueness intact).

## 18. Focused and combined results

- Focused WU4: 32 passed (repeated runs).
- Combined WU2-WU4: 32 + 33 + 76 = 141 passed together with the v0.9.7-A,
  v0.9.6-C1, F6D, router, API-contract, streamlit, and student-experience
  suites (250 passed in the combined batch).
- Locale parity: 563/563 symmetric, no empty values; compileall and the
  pixel-art style audit PASS; `git diff --check` clean on WU4 files.

## 19. Affected regression result

38 files covering practice targets/API/repositories, attempts/evaluations,
Journey projection, Feedback/Revision navigation, WU2-WU4 suites, parity,
H2D2, migrations, and version-pinned suites: **638 passed, 1 skipped,
exit 0**.

## 20. Full non-live core result

Canonical environment (PYTHONUTF8=1, PYTHON_DOTENV_DISABLED=1,
LLM_PROVIDER=local, fresh isolated DATABASE_PATH, DATABASE_URL removed,
30-entry allowlist, `--ignore=tests/live`):
**1000 passed / 8 skipped / 0 failed / exit 0**
(C:\tmp\wu4-fullcore\full_core_output.txt; 969 baseline + 31 new WU4
tests; the 32nd was added after the run and passed in the combined suites).

## 21. Launcher result

`cmd /c "run.bat --verify"` PASS - health/docs/streamlit 200, isolated
auto-provisioned DB, migration 13, migrate/initialize/smoke exit 0.

## 22. EN/ZH x desktop/mobile affected-path matrix

`verification/v0.9.7-b/v0.9.7-b-wu4-20260805-r1/w4_browser_matrix.py`
ran the full focused path independently for en/zh x 1280x900/390x844:
Feedback priority -> Open Practice -> create-or-reuse -> focused task
(priority/why/direction/evidence/instruction) -> empty validation (zero
writes) -> valid response -> saved state -> reload re-entry (saved state,
no form). Every combination: exactly 1 target / 1 exercise / 1 attempt /
1 evaluation; no console errors, no page errors, no remote requests, no
overflow, no raw keys; mobile controls >= 44px; no WU5 actions; no
completion wording.

## 23. Screenshot, log, and evidence locations

- Matrix evidence: verification/v0.9.7-b/v0.9.7-b-wu4-20260805-r1/
  rendered_page_matrix_evidence.json (16 screenshots in screenshots/).
- Full core log: C:\tmp\wu4-fullcore\full_core_output.txt.
- The isolated matrix DB and logs are gitignored and retained only as local
  evidence; the screenshot viewer was rate-limited (vision sidecar
  unavailable), so DOM/text assertions and persisted write counts are the
  verification basis, with screenshots retained for the owner.

## 24. Change-impact review

CRG `detect_changes` on the 14 WU4 source files: 23 changed
functions/classes, 71 affected flows, risk 0.65 - the flows are the
Practice entry/context/exercise/attempt/saved-state paths plus shared
component fan-out; the flagged "test gaps" are covered by the new WU4
suite (the graph index predates the tests). GitNexus MCP was unavailable
(transport error) and the CRG graph is stale; both noted as limitations.
The dependency graph/OpenAPI snapshots were refreshed for the new endpoint
(routes 81 -> 82; GET/POST 77 -> 78).

## 25. Known limitations

- API-level exercise-instance idempotency remains a documented WU4 boundary:
  the Student path guards (check-before-create, entry-action-only), but the
  create-exercise endpoint itself is still not idempotent (audit G10,
  B-OPTIONAL).
- The pre-existing readiness-gate test flake (test_v095b) and the stale
  graph index are unchanged and documented.
- Legacy targets continue their existing path without priority context
  (by design); malformed stored rows on the affected path produce controlled
  errors, while repository-wide malformed-row repair remains deferred (G9).
- The note texts on Feedback/Revision were updated because they described
  the pre-WU4 no-auto-creation behavior.

## 26. Deferred WU5 and WU6 work

- WU5: evaluation semantics, COMPLETED transition, completion state,
  Finish/Continue actions.
- WU6: Journey integration verification, full v0.9.7-B matrix, release
  closure.

## 27. WU4 acceptance-criteria matrix

All 36 criteria are satisfied: entry from Feedback (1) and Revision (2);
create-or-reuse only through the explicit action (3); repeated entry reuses
(4); direct navigation fabricates nothing (5); preset validated against the
current learner (6); one target resolves one persisted context (7); no
rendered-text/session content reconstruction (8); cross-student/cross-source
reads rejected (9); focused task displays priority/rationale/evidence/
direction/instruction (10); current exercise reused-or-created without
uncontrolled duplication (11); exercise seeded from verified evidence (12);
legacy targets compatible (13); empty responses produce no write (14); valid
responses persist one correctly associated attempt (15); one explicit
submission produces at most one attempt (16); double clicks/reruns/uncertain
responses do not duplicate (17); failure preserves input and context (18);
partial/evaluation failure represented accurately (19); explicit saved state
(20); rerun/refresh/locale/re-entry recover from persistence (21); saved
attempts never treated as unsubmitted (22); no COMPLETED transition (23);
evaluation unchanged (24); no WU5 actions (25); no new Journey events (26);
WU2/WU3 tests green (27); baselines intact (28); focused/combined/affected/
full-core/launcher/rendered verification pass (29); EN/ZH x desktop/mobile
independently reported (30); no unnecessary migration (31); user-owned files
untouched (32); `git diff --check` clean (33); impact review done (34);
reproducible evidence recorded (35); v0.9.7-B incomplete with WU5 next (36).

## 28. Final Git state and preserved user-owned files

`git status --short` after the commits shows only the preserved user-owned
entries (`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
`data/demo_journey_manifest.json`) plus the gitignored v0.9.7-a and WU4 run
logs/isolated DBs; all WU4 project changes are committed.

## 29. Commit list

- `93966b9` `feat(v0.9.7-b): connect priority targets to focused practice`
  - server entry intent + read-only context resolver + attempt ownership;
    Student entry/task UI; locale keys; API-surface/dependency/OpenAPI
    contract refresh; canonical allowlist 29 -> 30.
- `25d901e` `test(v0.9.7-b): verify focused task and attempt recovery`
  - tests/test_v097b_wu4_practice_task.py (new, 32 tests) + surface/route/
    count contract test updates and the v0.9.7-A/v0.9.6-C1 entry updates.
- `dbfe37b` `docs(v0.9.7-b): close work unit 4`
  - RUN_VERIFICATION_V0.9.7_B_WU4.md (new), project-state docs, and the WU4
    rendered-matrix run directory (scripts, evidence, screenshots).

No push or pull request was opened (not instructed).

### WU4 closure metadata reconciliation (WU5 preflight)

The final `docs(v0.9.7-b): close work unit 4` commit on `master` is
`dbfe37b` (WU4 implementation and verification closure HEAD; parent
`25d901e`). The earlier `90a83c5` is the pre-amendment version of the same
documentation commit (same parent `25d901e` and author timestamp, earlier
committer timestamp). `90a83c5` is NOT an ancestor of the current `master`
history and is superseded by `dbfe37b`; it is retained here only as
historical record. The WU5 implementation baseline is `dbfe37b`.

## 30. End state

WU4 completed the focused task and reliable attempt-persistence loop only.
The Practice target, priority, and learning cycle are NOT complete; WU5 is
the next planned work unit; v0.9.7-B remains incomplete.
