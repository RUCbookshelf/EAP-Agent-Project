# v0.9.7-B Work Unit 5 — Evaluation Semantics, Target Completion, and Post-Practice Next Steps

**Status:** COMPLETE - all 54 WU5 acceptance criteria satisfied; WU6
(Journey integration and full verification) is the next planned work unit;
v0.9.7-B as a whole is NOT complete.
**Date:** 2026-08-05

## 1. Actual pre-reconciliation branch and HEAD

- Branch: `master` (unchanged).
- HEAD before MCU 5.0: `dbfe37b` (`docs(v0.9.7-b): close work unit 4`).
- Worktree before MCU 5.0: only preserved user-owned entries
  (`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
  `RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`) plus gitignored v0.9.7-a run logs.

## 2. Actual WU4 functional/verification closure HEAD

`dbfe37b` is the WU4 closure HEAD (parent `25d901e`; WU4 commit sequence
`93966b9` feat -> `25d901e` test -> `dbfe37b` docs).

## 3. WU4 metadata discrepancy findings

- `90a83c5` (`docs(v0.9.7-b): close work unit 4`) exists as a dangling
  object but is NOT an ancestor of `master`; it is the pre-amendment
  version of `dbfe37b` (same parent `25d901e`, same author timestamp,
  earlier committer timestamp).
- `RUN_VERIFICATION_V0.9.7_B_WU4.md` section 29 still listed `90a83c5` as
  the documentation commit.
- `PROJECT_STATE.md`, `docs/development/CURRENT_TASK_STATE.md`, and
  `docs/development/MASTER_ROADMAP.md` contained no stale WU4 hashes.

## 4. Metadata corrections made

- `RUN_VERIFICATION_V0.9.7_B_WU4.md` section 29 updated: commit list now
  names `dbfe37b` and records `90a83c5` explicitly as the superseded
  pre-amendment version (historical only).

## 5. Metadata-reconciliation commit

- `42e285e` `docs(v0.9.7-b): reconcile WU4 closure metadata`
  (documentation only; no functional, test, locale, API, schema, or
  migration change).

## 6. Actual WU5 implementation baseline

- `6dbf43a` (after the reconciliation commit and the frozen protocol
  commit). WU4 functional tests were not rerun for the metadata
  reconciliation (no evidence-based need; the WU4 tree is unchanged).

## 7. Final WU5 branch and HEAD

- Branch: `master`; final HEAD after closure: see section 34.

## 8. WU5 commits and purposes

- `6dbf43a` `docs(v0.9.7-b): freeze WU5 evaluation and completion protocol`
  - `docs/development/V0.9.7_B_WU5_PROTOCOL.md` (new): frozen protocol from
    MCU 5.0 reconnaissance.
- `089419c` `feat(v0.9.7-b): define practice evaluation and completion
  semantics`
  - `PracticeTargetStatus.COMPLETED` + JSON-only `updated_at`
    (`app/practice/schemas.py`); `PracticeEvaluationReadService`
    (`app/practice/evaluations.py`); `PracticeTargetCompletionService`
    (`app/practice/completion.py`); atomic
    `update_practice_target_status` repository method + port;
    `GET .../practice-targets/{id}/evaluations` and
    `POST .../practice-targets/{id}/complete` endpoints; completion
    service wiring; API client methods + port; Practice page evaluation
    view, finish action, completed state, and bounded next steps;
    `PRACTICE_COMPLETE` pending mode; 9 en/zh locale keys + 2 note-text
    updates; API-surface/OpenAPI/dependency-graph/allowlist refresh.
- `74b8698` `test(v0.9.7-b): verify completion and post-practice recovery`
  - `tests/test_v097b_wu5_completion.py` (new, 38 tests), harness methods,
    count/route/port contract updates.
- `5abab20` `test(v0.9.7-b): refresh frozen route and port contract pins`
  - `EXPECTED_ROUTE_CONTRACT` + H1 `protocol_inventory.json`
    `PracticeWritePort` declared methods.
- `0efd36d` `fix(v0.9.7-b): keep the current practice target stable across
  reruns`
  - Learner-scoped selection stability: after an explicit intent opens a
    target, reruns (submit/finish/locale) no longer switch to another
    active target; +1 regression test.
- `0662492` `test(v0.9.7-b): add WU5 rendered-page matrix evidence`
  - WU5 browser harness + matrix + evidence JSON + screenshots.
- `01115ba` `chore(v0.9.7-b): drop debug screenshots from WU5 matrix
  evidence`

No push or pull request was opened (not instructed).

## 9. WU5 stage boundary

WU5 implemented the completion semantics for one eligible Practice target:
persisted attempt -> honest evaluation view -> explicit finish ->
idempotent ACTIVE->COMPLETED -> persistence-backed completed state ->
bounded next steps. WU5 does NOT close v0.9.7-B; WU6 remains.

## 10. MCU 5.0-5.5 results

- MCU 5.0 (metadata reconciliation + protocol freeze): PASS - evidence in
  sections 1-6 and `docs/development/V0.9.7_B_WU5_PROTOCOL.md`.
- MCU 5.1 (evaluation semantic contract): PASS - focused evaluation tests
  11 passed; rendered available/unavailable states verified.
- MCU 5.2 (completion eligibility + idempotent transition): PASS - 15
  completion service/API tests passed, including concurrency and
  column/JSON consistency.
- MCU 5.3 (completion UI + re-entry): PASS - 12 page tests passed; matrix
  re-entry checks passed.
- MCU 5.4 (post-Practice next steps): PASS - 4 next-step page tests passed;
  matrix navigation checks passed.
- MCU 5.5 (integration verification): PASS - sections 24-30.

## 11. Evaluation semantic contract

The persisted evaluation is automated formative feedback on the submitted
Practice response (unchanged rule-based algorithm). It is never presented
as mastery, learning gain, transfer, proficiency, CEFR level, successful
remediation, or readiness to advance. A persisted attempt is authoritative
saved work; evaluation failure never invalidates it.

## 12. Evaluation availability states

- AVAILABLE: valid persisted evaluation row whose attempt -> exercise ->
  target -> learner chain validates.
- UNAVAILABLE: no valid row (missing, failed, legacy, or malformed);
  rendered as an honest notice; attempt remains authoritative.
- MALFORMED: unparseable rows are skipped server-side (controlled
  unavailable), never a crash.
- No new async PENDING evaluation state.

## 13. Completion eligibility rule

A learner-owned target is eligible after at least one persisted SUBMITTED
attempt exists on an exercise belonging to that target. Evaluation
availability is not a gate. Activity completion only; no mastery claim.

## 14. Completion service and transaction

`app/practice/completion.py::PracticeTargetCompletionService` owns lookup,
ownership, eligibility, status validation, transition, and idempotency.
The repository method `update_practice_target_status` runs BEGIN IMMEDIATE,
conditional UPDATE on the old status, and updates the status column and
`target_json` (status + `updated_at`) in one transaction.

## 15. Status column/JSON consistency

Both `practice_targets.status` and `target_json.status` equal `completed`
after the transition (verified by direct database checks in the focused
suite and the rendered matrix).

## 16. Idempotency and concurrency behavior

Repeated completion returns the same completed target (200) with the same
`updated_at`; concurrent completion (two threads) produced one stable
completed row; zero duplicate target/exercise/attempt/evaluation rows.

## 17. Completed-state UI

The completed state shows the completion heading, target label, saved
attempt reference, evaluation (or unavailable notice), the statement that
the activity was completed and the response/feedback were saved, and
bounded actions. No response form and no active finish button.

## 18. Re-entry behavior

Re-entry (rerun, refresh, locale switch, direct navigation, Feedback and
Revision entry) reloads target status from persistence; the completed
target is reused (WU3 create-or-reuse), no new target/exercise/attempt is
created, and the completed state renders without a fresh form.

## 19. Post-Practice next steps

Return to Feedback and Open Learning Journey are navigation-only; another
existing active target can be opened explicitly; no automatic
next-target creation or sequencing.

## 20. Legacy compatibility

A legacy target (no priority provenance) with a valid persisted attempt
completes normally (tested); no fabricated priority provenance.

## 21. Migration decision

**No migration 14.** Implementation uses the existing `status` TEXT column,
the existing `target_json`, a JSON-only optional `updated_at` field, and
existing attempt/evaluation tables. Migration 13 is untouched
(`run.bat --verify` reports migration 13).

## 22. Modified files and purposes

Production:
- `app/practice/schemas.py` - `PracticeTargetStatus.COMPLETED`; optional
  JSON-only `updated_at`.
- `app/practice/evaluations.py` (new) - learner-owned evaluation read
  service with malformed-row safety.
- `app/practice/completion.py` (new) - completion service + controlled
  `PracticeCompletionError`.
- `app/practice/ports.py` - `PracticeWritePort.update_practice_target_status`.
- `app/infrastructure/sqlite/repositories/practice.py` - atomic conditional
  status/JSON update.
- `app/api/routers/practice.py` - two new endpoints + error mapping.
- `app/api/deps.py`, `app/api/main.py` - completion-service wiring.
- `app/ui/api_client.py`, `app/ui/ports/student.py` - client methods +
  port.
- `app/ui/features/student/practice.py` - persisted evaluation view,
  finish action, completed state, stable selection, bounded next steps.
- `app/ui/features/student/submit_reliability.py` - `PRACTICE_COMPLETE`
  pending mode.
- `locales/en.json`, `locales/zh_CN.json` - 9 new keys + 2 note-text
  updates (parity maintained).

Contracts/evidence:
- `tests/contracts/api_surface_contract.py` (80 endpoints / 56 client
  methods); `verification/v0.9.5-h2d2/{openapi,dependency_graph}_{before,
  after}.json`; `verification/v0.9.5-h1/protocol_inventory.json`; canonical
  allowlist (30 -> 32) + command copy.

Tests:
- `tests/test_v097b_wu5_completion.py` (new); `tests/harness_v097a_student.
  py`; count/route/port contract tests; `verification/v0.9.7-b/
  v0.9.7-b-wu5-20260805-r1/` (harness, matrix, evidence, screenshots).

## 23. Tests added or modified

- New: `tests/test_v097b_wu5_completion.py` (38 tests): evaluation read
  path (11), completion service/API (15), Practice page evaluation (2),
  completion UI/next steps (10).
- Modified: `tests/harness_v097a_student.py`; `tests/test_v095d_api_
  contract.py`; `tests/test_v095f6d_practice_boundary_narrowing.py`;
  `tests/test_v095h2d2_api_dependency_bindings.py`; `tests/test_v096b_
  first_draft_submission.py`; `tests/test_v095b_router_contract.py`;
  `tests/contracts/api_surface_contract.py`.
- No existing test was deleted, skipped, or weakened.

## 24. Focused and combined results

- Focused WU5: 38 passed (repeated runs).
- Combined WU2-WU5: 178 passed.
- WU4 regression: 32 passed after the selection-stability fix.

## 25. Affected regression

30 files (WU2-WU5, v0.9.7-A, v0.9.6-C1, Practice, Journey, Student,
Streamlit, migration, router/API/port/parity contracts, repository
modularization/facade): **553 passed / 3 skipped / exit 0** under the
canonical environment (output `C:\tmp\wu5-affected\affected_output.txt`).

## 26. Full non-live core

Canonical environment (PYTHONUTF8=1, PYTHON_DOTENV_DISABLED=1,
LLM_PROVIDER=local, fresh isolated DATABASE_PATH, DATABASE_URL removed,
32-entry allowlist, `--ignore=tests/live`):
**1039 passed / 8 skipped / 0 failed / exit 0**
(`C:\tmp\wu5-fullcore\full_core_final_output.txt`; 1000 WU4 baseline
+ 39 net-new WU5 tests).

## 27. Launcher verification

`cmd /c "run.bat --verify"` PASS - health/docs/streamlit 200, isolated
auto-provisioned DB, migration 13, config-v0.9.0, exit 0 (run twice: after
implementation and after the final fix).

## 28. EN/ZH x desktop/mobile matrix

All four combinations ran independently (1280x900 and 390x844; en and
zh_CN): Writing -> Feedback priority -> Open Practice -> focused task ->
valid attempt (1 row) -> evaluation available -> finish (ACTIVE->COMPLETED)
-> completed state -> repeated completion idempotent -> Feedback re-entry
-> Return to Feedback -> Revision re-entry (linked revision submit) ->
reload re-entry -> second active target opened explicitly -> Open Learning
Journey. Every combination: 0 console errors, 0 page errors, 0 remote
requests, no overflow, no raw locale keys, no mastery wording, journey
event count unchanged by completion, column and JSON status `completed`,
mobile controls >= 44px.

## 29. Screenshot, database, and log locations

- Evidence: `verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1/
  rendered_page_matrix_evidence.json`.
- Screenshots: same run directory `screenshots/` (20 PNGs).
- Isolated DB + logs: same run directory `isolated/` and `logs/`
  (gitignored).
- Full-core/affected outputs: `C:\tmp\wu5-fullcore\*`, `C:\tmp\wu5-affected\*`.

## 30. Change-impact review

Code Review Graph `detect_changes` (base `6dbf43a`): 37 changed
functions/classes, 118 affected flows, risk 0.75, 28 reported test gaps.
The CRG graph predates WU5 (built at `01f6f119`), so its gap list is
stale; every flagged surface is covered by the WU2-WU5 focused suites and
the full core (e.g., `require_student` 404/403 paths, target creation,
repository writes/reads). Review conclusion: affected behavior is limited
to evaluation presentation, completion eligibility, the target status
transition, completion UI, bounded post-Practice navigation, and directly
required API/service/repository/locale/test wiring.

## 31. Known limitations

- `practice_targets` has no relational `updated_at` column; the completion
  timestamp is stored in `target_json.updated_at` (documented protocol
  decision; no migration).
- The CRG impact index was not rebuilt for WU5 (graph build at
  `01f6f119`); impact conclusions were cross-checked against direct test
  evidence.
- Vision sidecar was unavailable for screenshot inspection (rate-limited);
  DOM/text/write-count/browser checks are the verification basis.

## 32. Deferred WU6 work

Journey projection verification for priority-derived targets, the final
v0.9.7-B end-to-end product matrix, release-state reconciliation, full
closure documentation, and the final `detect_changes` review against a
fresh index.

## 33. WU5 acceptance-criteria matrix

1. WU4 Git history verified before implementation - PASS (sections 1-3).
2. WU4 closure metadata reconciled - PASS (section 4).
3. Reconciliation separate from WU5 implementation - PASS (`42e285e`).
4. WU4 functional tests not unnecessarily rerun - PASS.
5. Actual WU5 baseline recorded - PASS (`6dbf43a`).
6. Existing evaluation logic unchanged - PASS (`evaluate_attempt` untouched).
7. Evaluation described as formative task feedback - PASS (section 11).
8. Available/unavailable states explicit - PASS (section 12).
9. Malformed evaluation fails safely - PASS (tests + read service).
10. Attempt authoritative when evaluation unavailable - PASS.
11. No mastery/CEFR/proficiency/transfer/learning-gain/pass/improvement
    wording - PASS (forbidden-word checks in page tests and matrix).
12. Eligibility from persisted learner-owned attempts - PASS.
13. Evaluation outcome is not a completion gate - PASS.
14. Completion requires explicit student action - PASS (finish button
    only after saved attempt).
15. Target without eligible attempt cannot complete - PASS (422).
16. Cross-student completion rejected - PASS (403, zero writes).
17. Unrelated attempts/exercises cannot complete - PASS (422).
18. ACTIVE -> COMPLETED persists atomically - PASS (BEGIN IMMEDIATE +
    conditional UPDATE).
19. Relational and JSON status consistent - PASS.
20. Timestamp updated consistently - PASS (`updated_at` set once).
21. Repeated completion idempotent - PASS.
22. Concurrent completion one stable state - PASS (thread test).
23. No duplicate target/exercise/attempt/evaluation - PASS.
24. Reopening priority reuses completed target - PASS.
25. No new active target on reopen - PASS.
26. Completed targets show persistence-backed terminal state - PASS.
27. No fresh response form for completed targets - PASS.
28. Completion failure no false success - PASS (page test).
29. Interrupted responses reconcile against persistence - PASS (rerun
    re-reads status; pending guard).
30. Evaluation visible or honestly unavailable after completion - PASS.
31. Another active target opens explicitly - PASS.
32. No next target generated automatically - PASS.
33. No automatic priority ranking/sequencing - PASS.
34. Return to Feedback navigation-only - PASS.
35. Open Learning Journey navigation-only, no new Journey events - PASS
    (journey event count unchanged).
36. Legacy targets with valid attempts completable - PASS.
37. WU2 mapping intact - PASS (combined suite).
38. WU3 create-or-reuse + migration 13 intact - PASS.
39. WU4 focused task/attempt recovery intact - PASS (32 WU4 tests).
40. No migration 14 - PASS.
41. Focused WU5 tests pass - PASS (38).
42. WU2-WU5 combined pass - PASS (178).
43. Affected regression passes - PASS (553/3).
44. Full non-live core passes - PASS (1039/8, exit 0).
45. Launcher verification passes - PASS.
46. EN/ZH x desktop/mobile matrix passes independently - PASS.
47. No console/page errors, raw keys, remote requests, or overflow - PASS.
48. User-owned files untouched and uncommitted - PASS (section 35).
49. `git diff --check` clean - PASS (WU5 files; pre-existing user-owned
    whitespace in AGENTS.md remains untouched).
50. Final changes pass impact review - PASS (section 30).
51. Reproducible Git/file/line/test/database/screenshot/log evidence - PASS.
52. No new Journey event type - PASS.
53. v0.9.7-B described as incomplete - PASS (section 36).
54. WU6 identified as next - PASS (section 37).

## 34. Final Git state

- Branch: `master`.
- Final HEAD: `01115ba` (`chore(v0.9.7-b): drop debug screenshots from WU5
  matrix evidence`) plus the closure documentation commit (section 8).
- Commit sequence: `42e285e` -> `6dbf43a` -> `089419c` -> `74b8698` ->
  `5abab20` -> `0efd36d` -> `0662492` -> `01115ba` -> closure docs.

## 35. Preserved user-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
and `data/demo_journey_manifest.json` remain unmodified and uncommitted;
`git status --short` shows only these plus gitignored run logs/isolated
databases.

## 36. v0.9.7-B remains incomplete

WU5 completed the evaluation/completion semantics only. Journey
integration verification, the full product matrix, and release closure
belong to WU6; v0.9.7-B is NOT complete.

## 37. WU6 is next

WU6: Journey projection verification, full non-live core, `run.bat
--verify`, independent EN/ZH x desktop/mobile matrix, fresh-index
`detect_changes` review, documentation + commit.
