# v0.9.7-B Work Unit 6 - Journey Integration Verification, Final Product Matrix, and Release Closure

**Status:** COMPLETE - all 80 WU6 acceptance criteria satisfied; v0.9.7-B is
complete, verified, and closed; the next planned phase is v0.9.7-C.
**Date:** 2026-08-05
**Governing protocol:** the owner-provided WU6 work-unit objective and
`docs/development/V0.9.7_B_WU6_PROTOCOL.md` (frozen at MCU 6.0, corrected
once with empirical evidence before verification).

## 1. Initial branch and HEAD

- Branch: `master` (unchanged throughout).
- Pre-WU6 HEAD: `b9e030d` (`docs(v0.9.7-b): close work unit 5`).
- Worktree before MCU 6.0: only preserved user-owned entries (modified
  `AGENTS.md`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`;
  untracked `.claude/`, `CLAUDE.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`) plus the pre-existing gitignored
  v0.9.7-a run logs and one untracked probe screenshot
  (`verification/v0.9.7-a/v0.9.7-a-20260804-r1/logs/probe_selectbox.png`).

## 2. Verified WU5 closure HEAD

- `b9e030d` is the WU5 final closure documentation commit (parent
  `01115ba`); both are ancestors of the pre-WU6 HEAD.
- `01115ba` (`chore(v0.9.7-b): drop debug screenshots from WU5 matrix
  evidence`) is the WU5 functional/evidence HEAD and the direct pre-closure
  parent of `b9e030d`.
- WU5 commit sequence verified from Git: `42e285e` -> `6dbf43a` ->
  `089419c` -> `74b8698` -> `5abab20` -> `0efd36d` -> `0662492` ->
  `01115ba` -> `b9e030d`. No commit after WU5 closure existed before WU6.

## 3. WU5 metadata discrepancy and correction

- `RUN_VERIFICATION_V0.9.7_B_WU5.md` section 34 named only `01115ba` plus an
  unspecified "closure documentation commit"; the explicit `b9e030d` role
  was missing. No other state document contained stale WU5 hashes.
- Correction (documentation only): the report now distinguishes WU5
  functional/evidence HEAD (`01115ba`), WU5 final closure documentation
  commit (`b9e030d`), WU5 final closure HEAD (`b9e030d`), and the WU6
  baseline. Commit `931f1c2` `docs(v0.9.7-b): reconcile WU5 closure
  metadata`.
- WU5 tests were not rerun for the metadata correction (tree unchanged).

## 4. WU6 implementation baseline

- `b0f16b5` `docs(v0.9.7-b): freeze WU6 release verification protocol`
  (after the metadata-reconciliation commit `931f1c2`).
- `a46b8ce` `docs(v0.9.7-b): correct WU6 Journey event-count expectation`
  (documentation-only protocol correction made from the empirical probe of
  the real submission pipeline before any verification run: a linked
  revision submission also produces its own analysis + feedback records, so
  the deterministic two-essay cycle projects 11 events with an evaluation
  and 10 without, not 8/7).
- Migration version 13 unchanged; active configuration `config-v0.9.0`;
  provider local only.

## 5. Final branch and HEAD

- Branch: `master`; final release HEAD after the closure commit: recorded
  in section 36 (closure commit `docs(v0.9.7-b): close priority-guided
  practice cycle`).

## 6. WU6 commit list

- `931f1c2` `docs(v0.9.7-b): reconcile WU5 closure metadata`
  - RUN_VERIFICATION_V0.9.7_B_WU5.md (metadata correction only).
- `b0f16b5` `docs(v0.9.7-b): freeze WU6 release verification protocol`
  - docs/development/V0.9.7_B_WU6_PROTOCOL.md (new).
- `a46b8ce` `docs(v0.9.7-b): correct WU6 Journey event-count expectation`
  - protocol event-count correction from empirical evidence.
- `769cf06` `test(v0.9.7-b): verify Journey projection and deduplication`
  - tests/test_v097b_wu6_journey_projection.py (new, 18 tests).
- `d124a83` `test(v0.9.7-b): add final WU6 product matrix evidence`
  - verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1/ (matrix scripts,
    evidence JSON, 36 screenshots).
- `51e89db` `test(v0.9.7-b): add WU6 research smoke evidence`
  - w6_research_smoke.py + research_smoke_evidence.json.
- Closure commit (section 36): `docs(v0.9.7-b): close priority-guided
  practice cycle`.

No push or pull request was opened (not instructed).

## 7. WU6 scope and non-goals

WU6 verified the existing read-time Journey projection for the complete
priority-derived Practice cycle, executed the final product matrix and all
release gates, reconciled release metadata, and closed v0.9.7-B. No
production code, locale, migration, API surface, or Journey behavior was
changed. Explicit non-goals preserved: no new Journey event types, no
Journey persistence, no chronology redesign, no progress/mastery/
proficiency/CEFR/learning-gain metrics, no adaptive sequencing, no
automatic next priority/target, no new evaluation algorithm, no migration
14, and no v0.9.7-C/D/E functionality.

## 8. MCU 6.0-6.5 results

- MCU 6.0 (metadata reconciliation + protocol freeze): PASS - sections
  1-4; protocol frozen before any verification.
- MCU 6.1 (Journey projection reconstruction and provenance verification):
  PASS - sections 9-16; 18 focused tests pin the contract.
- MCU 6.2 (release-blocking fixes): NO RELEASE BLOCKER FOUND - no
  production change was required. The projector correctly handles all
  valid WU2-WU5 record shapes; completion creates no event; evaluation
  unavailable projects honestly; legacy targets stay readable; no
  cross-association; Journey reads never write. The malformed-row behavior
  on a tampered database (stable repository-level error, audit G9) is a
  documented pre-existing limitation, not a verified-path defect.
- MCU 6.3 (final product matrix): PASS - sections 19-22.
- MCU 6.4 (release gates): PASS - sections 23-34.
- MCU 6.5 (release-state reconciliation and closure): PASS - sections
  35-38.

## 9. Current Journey projector architecture

The Learning Journey is a **read-time derivation**:
`JourneyService.get_journey` (`app/journey/service.py:124-135`) reads eight
learner-scoped record sets through `JourneyProjectionReadPort`
(service.py:112-121), derives events, sorts them, deduplicates by key, and
classifies state (`_classify_state`, service.py:428-481). The service has
no write path; repeated reads are side-effect free (verified by tests and
whole-database row-count checks in the matrix). Practice records are read
through `SQLitePracticeRepository` (practice.py:93-280), which stores full
entity JSON plus queryable columns.

## 10. Exact projected event types

| Event type | Source record | Deduplication key |
|---|---|---|
| `writing_submitted` | essay (no revision link) | `writing_submitted:essay:{essay_id}` |
| `revision_submitted` | essay (linked) | `revision_submitted:essay:{essay_id}` |
| `analysis_completed` | analysis_run | `analysis_completed:analysis_run:{analysis_run_id}` |
| `insufficient_evidence` | essay without analysis (derived) | `insufficient_evidence:essay:{essay_id}` |
| `feedback_available` | feedback_record | `feedback_available:feedback_record:{feedback_id}` |
| `feedback_priority_available` | feedback_record with priorities | `feedback_priority_available:feedback_record:{feedback_id}` |
| `feedback_without_priority` | feedback_record without priorities (derived) | `feedback_without_priority:feedback_record:{feedback_id}` |
| `practice_available` | practice_target | `practice_available:practice_target:{practice_target_id}` |
| `exercise_attempted` | exercise_attempt | `exercise_attempted:exercise_attempt:{attempt_id}` |
| `practice_evaluation_recorded` | practice_evaluation | `practice_evaluation_recorded:practice_evaluation:{evaluation_id}` |
| `within_task_response_observed` | WTR candidate | `within_task_response_observed:within_task_response_candidate:{response_id}` |
| `later_task_evidence` | transfer candidate | `later_task_evidence:transfer_evidence_candidate:{transfer_evidence_id}` |

**No `practice_completed` event exists**; target completion flows through
the existing `practice_available` event's `research_detail.status`
(`active` -> `completed`) and creates no event and no write.

## 11. Event source/provenance rules

- Every event carries `learner_id` equal to the requesting learner; all
  record reads are student-scoped (repository SQL `WHERE student_id=?` or
  joined through the learner's essays/attempts), so cross-student data can
  never appear (verified by `TestLearnerIsolation` and the matrix).
- `practice_available`: `source_record_id` = target id; `submission_id`/
  `task_id` = target `source_submission_id`; `research_detail` = only
  `target_code` + `status` (no fabricated priority provenance).
- `exercise_attempted`: `source_record_id` = attempt id; `task_id` =
  exercise id; `research_detail` = `attempt_number` + `status`.
- `practice_evaluation_recorded`: joined through the attempt's learner;
  `research_detail` = `completion_status` + `target_action_status`.
- `revision_submitted`: `research_detail.revision_of_submission_id` links
  the revision to its source essay.
- Event labels/limitations are fixed conservative strings; no event claims
  mastery, proficiency, CEFR level, learning gain, transfer, or pass
  outcomes (the fixed `feedback_without_priority` description says "no
  priority passed the Diagnostic Gate" - a gate description, not a
  learner-pass claim).

## 12. Deduplication rules

- Each event's `deduplication_key` is `{event_type}:{source_record_type}:
  {source_record_id}` - one event per persisted source record.
- The derivation is deterministic; a defensive post-sort dedup by key
  (service.py:432-438) keeps the event list unique.
- Repeated reads, reloads, locale switches, Feedback re-entry, Revision
  re-entry, target reuse, and repeated completion never append events
  (verified by focused tests and matrix whole-DB write checks).

## 13. Ordering rules

- Sort key: `(essay_submitted_at.get(submission_id, occurred_at),
  EVENT_STAGE_ORDER.get(event_type, 50), source_record_id, event_type)`
  (service.py:414-430). Essay-anchored events use the essay's submitted
  timestamp; practice attempt/evaluation events (no submission_id) use
  their own `occurred_at`.
- Stage order: writing/revision=10, insufficient=20, analysis=30,
  feedback=40, priority=50, practice_available=60, exercise_attempted=70,
  evaluation=80, WTR=90, later=100.
- The tie-breakers (stage, source id, type) are deterministic for
  identical persisted data; repeated reads return identical order
  (verified by tests and the matrix).

## 14. Completion and evaluation-unavailable projection

- Completion: `research_detail.status` flips to `completed` on the existing
  `practice_available` event; event count, keys, and ordering are
  unchanged; no new persistence rows (verified before/after completion in
  every matrix combination and in `TestCompletionProjection`).
- Evaluation unavailable: the attempt projects `exercise_attempted`
  (status `submitted`, `attempt_number` 1) and **no**
  `practice_evaluation_recorded` event is fabricated; the completed target
  still projects `status: "completed"`; state classification reports
  `attempt_no_evaluation` until an evaluation row exists. No failure or
  mastery implication appears (fixed limitation strings verified).

## 15. Legacy projection

- A legacy target (no `source_priority_id`) projects `practice_available`
  with `research_detail` = `{target_code, status}` only - no fabricated
  priority provenance; attempts/evaluations/completion project exactly as
  for priority-derived targets; no crash (verified by
  `TestLegacyCompatibility` and the matrix legacy scenarios).

## 16. Journey side-effect checks

- `get_journey` performs only reads; the Journey page renders from the API
  and performs no writes (app/ui/features/student/journey.py:118-166).
- Focused tests assert table counts unchanged across three reads;
  `test_journey_v093c.py` asserts no engagement trace is written.
- The matrix snapshots **whole-database row counts** (all tables) before
  and after opening the Journey, reloading it, switching locale, and
  re-reading it: identical in every combination.

## 17. Release-blocker findings and fixes

- No release blocker was found. No production change was made. The
  malformed-row boundary (audit G9) is documented in section 27 and was
  tested as a stable error with no fabrication and no cross-association on
  the tampered-data path only.

## 18. Final matrix scenarios

All four required combinations (en/zh_CN x 1280x900/390x844) ran the main
scenario independently: create/select learner -> first writing -> structured
feedback -> persisted priority -> Open Practice -> create-or-reuse target ->
focused task (priority/why/direction/evidence/instruction) -> empty
validation (zero writes) -> valid attempt -> evaluation -> Finish This
Practice Cycle -> COMPLETED (column + JSON) -> repeated completion
idempotent -> reload re-entry -> Feedback re-entry -> Return to Feedback ->
Revision re-entry (linked revision submit) -> reload/direct Practice
re-entry -> mobile sidebar open/close (mobile combos) -> second active
target created and opened explicitly -> Open Learning Journey -> full
Journey projection verification (UI + API + reload + locale switch + no
writes). Focused scenarios on separate learners: evaluation-unavailable
(en desktop + zh mobile), no-priority (en desktop + zh mobile), legacy
(en desktop + zh mobile).

## 19. EN/ZH x desktop/mobile results

| Combination | Main cycle | Journey events | Completed status | Re-entry | Other target |
|---|---|---|---|---|---|
| en 1280x900 | PASS | 12 (11 cycle + 1 extra active target) | PASS (column + JSON) | PASS | PASS (explicit only) |
| zh_CN 1280x900 | PASS | 12 | PASS | PASS | PASS |
| en 390x844 | PASS | 12 | PASS | PASS (mobile sidebar) | PASS |
| zh_CN 390x844 | PASS | 12 | PASS | PASS (mobile sidebar) | PASS |

Every combination: 0 console errors, 0 page errors, 0 remote requests, no
horizontal overflow, no raw locale keys, mobile primary controls >= 44px,
no mastery/pass/learning-gain wording, no `practice_completed` event,
journey event count unchanged by completion, no writes during Journey
navigation, identical events after reload/locale switch.

## 20. Persisted record counts

Main learner per combination after the full cycle: 2 essays (original +
linked revision), 2 analysis runs, 2 feedback records, 1 priority-derived
target (completed) + 1 explicit extra active target, 1 exercise instance, 1
attempt, 1 evaluation, 0 WTR/transfer rows, 0 new Journey persistence rows
(Journey is read-time), 0 uncontrolled duplicates after all re-entry
checks. Evaluation-unavailable scenarios: 1 essay, 1 analysis run, 1
feedback record, 1 completed target, 1 exercise, 1 attempt, 0 evaluations.
No-priority scenarios: 1 essay, 1 analysis run, 1 feedback record, 0
targets. Legacy scenarios: 1 legacy target (completed), 1 attempt.

## 21. Journey event counts

- Main combos: 12 events (writing, analysis, feedback, priority,
  practice_available x2 [completed + active], exercise_attempted,
  practice_evaluation_recorded, revision_submitted, analysis [revision],
  feedback [revision], feedback_without_priority [revision]); unique
  dedup keys; identical across reads.
- Evaluation-unavailable: 6 events (no evaluation event, no revision).
- No-priority: no practice events; `feedback_without_priority` present.
- Legacy: `practice_available` with `{target_code, status}` only.

## 22. Focused tests

- New `tests/test_v097b_wu6_journey_projection.py`: **18 passed** (exact
  event set/source associations, deterministic ordering, counts, completion
  no-new-event, repeated-read idempotency + no writes, re-entry no
  duplicates, evaluation-unavailable honesty, learner isolation, target
  reuse, legacy compatibility, malformed-row boundary, stale-reference
  safety). Twice (standalone + combined).
- Static: `compileall` OK; `scripts/pixel_art_style_audit.py` PASS (0
  violations).

## 23. Combined WU2-WU6 tests

**197 passed** (WU2 76 + WU3 33 + WU4 32 + WU5 38 + WU6 18), exit 0,
local provider, isolated databases.

## 24. Affected regression

27 suites covering WU2-WU6, Journey, Practice, Feedback/Revision entry,
no-priority workflow, router/API/port/parity contracts, dependency
bindings, repository modularization/facade, student experience, hybrid
components, design tokens, and sidebar/genre rendering:
**569 passed / 0 failed / exit 0** under the canonical environment
(`C:\tmp\wu6-affected\affected_final_output.txt`).

## 25. Full non-live core

Canonical environment (PYTHONUTF8=1, PYTHON_DOTENV_DISABLED=1,
LLM_PROVIDER=local, fresh isolated DATABASE_PATH, DATABASE_URL removed,
32-entry SERVICE_API_DIFF_ALLOWLIST, `--ignore=tests/live`):
**1057 passed / 8 skipped / 0 failed / 4 warnings / exit 0**
(`C:\tmp\wu6-fullcore\full_core_final_output.txt`; WU5 baseline 1039/8 +
18 new WU6 tests). One preliminary affected batch missing the allowlist
environment variable failed only the repository-parity test; with the
canonical allowlist the identical test passes (4/4) and the coherent
affected batch is green.

## 26. Launcher verification

`cmd /c "run.bat --verify"` **PASS twice** (exit 0): health 200, docs 200,
streamlit 200, isolated auto-provisioned temporary database, migration 13,
config-v0.9.0, feedback-prompt-v0.7.1, migrate/initialize/smoke exit 0, no
live provider call (`C:\tmp\wu6-launcher\launcher_run1.txt`,
`launcher_run2.txt`).

## 27. Locale parity

572/572 keys symmetric (en = zh_CN), no missing keys, no empty values, no
raw keys in the matrix; no locale file changed in WU6 (parity measured,
not assumed).

## 28. Research smoke

Established v0.9.4-B subset (Research Overview, Data, System Audit x
English desktop / Chinese mobile = 6/6 renders) PASS: 0 exceptions, 0
overflow, 0 raw keys, 0 console/page errors, 0 remote requests
(`verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1/research_smoke_evidence.json`).

## 29. Contract/snapshot deltas

**None.** WU6 changed no production code, API surface (80 GET/POST routes,
56 client methods), OpenAPI, dependency graph, port inventory, migration
pin (13), canonical allowlist (32), or design tokens; the relevant contract
suites pass inside the affected batch and full core. No frozen evidence was
refreshed because no surface changed.

## 30. Fresh-index impact review

- Index refreshed with `node .gitnexus/run.cjs analyze` against the final
  WU6 implementation tree (HEAD `d124a83`): "Repository indexed
  successfully (23.0s)"; 10,651 nodes, 18,234 edges, 316 clusters, 254
  flows; `.gitnexus/meta.json` records `lastCommit = d124a83`, indexedAt
  2026-08-05T08:23:35Z. (FTS extension unavailable - search disabled;
  index build otherwise complete; recorded as a tooling limitation.)
- Final impact analysis: `gitnexus detect-changes -s compare -b b0f16b5`
  from a clean detached worktree at `d124a83` (the main worktree contains
  user-owned files whose working-tree diffs would pollute the review):
  **5 changed parseable files / 90 changed symbols / 236 affected flows**.
- All 90 changed symbols are WU6 verification/test/documentation symbols
  (test classes and helpers in `tests/test_v097b_wu6_journey_projection.py`,
  matrix/harness functions in `verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1/`,
  protocol-doc sections). **0 production symbols changed.** The graph's
  "critical" risk heuristic reflects fan-out through the shared matrix
  browser helpers (open/close sidebar, wait_stable), not production blast
  radius; this is corroborated by the direct Git diff (no `app/`, `locales/`,
  or migration changes) and the full non-live core (1057 passed).
- The CRG MCP server was unavailable (transport error); the GitNexus CLI
  was used as the repository-supported alternative per the frozen protocol.

## 31. Screenshots, logs, databases, and machine-readable evidence

- Matrix evidence: `verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1/
  rendered_page_matrix_evidence.json` (36 committed screenshots in
  `screenshots/`; smoke-run debug screenshots were dropped and moved to
  local trash, matching the WU5 debug-screenshot precedent).
- Research smoke: `research_smoke_evidence.json`.
- Isolated DB and stack logs (gitignored): `.../v0.9.7-b-wu6-20260805-r1/
  isolated/writing_feedback_v097b_wu6.db`, `logs/w6_matrix_*.log`,
  `logs/w6_research_*.log`.
- Test logs: `C:\tmp\wu6-affected\affected_final_output.txt`,
  `C:\tmp\wu6-fullcore\full_core_final_output.txt`,
  `C:\tmp\wu6-launcher\launcher_run1.txt`, `launcher_run2.txt`,
  `C:\tmp\wu6-impact\detect_changes_clean_full.txt`.

## 32. Migration decision

**No migration 14.** WU6 verified the existing read-time projection and
made no persistence change; migration 13 is untouched (launcher reports
migration 13; version-pinning tests green).

## 33. Known limitations

- Malformed `*_json` rows on a tampered database cause a stable
  repository-level read error on the Journey path (audit G9; documented in
  `docs/KNOWN_LIMITATIONS.md`); this is NOT reachable through the verified
  WU2-WU5 product path (records are Pydantic-validated on write), and
  repository-wide malformed-row repair remains deferred.
- The Journey timeline's fixed `feedback_without_priority` description
  contains "no priority passed the Diagnostic Gate"; this is a gate
  description, not a learner-pass claim.
- `practice_targets` has no relational `updated_at` column; the completion
  timestamp lives in `target_json.updated_at` (WU5 decision, unchanged).
- GitNexus FTS search extension unavailable; the graph index build itself
  completed. CRG MCP transport unavailable; GitNexus CLI used instead.
- Vision sidecar was unavailable for screenshot inspection; DOM/text/
  write-count/browser checks are the verification basis, with screenshots
  retained for the owner.
- The pre-existing readiness-gate timing flake
  (`test_v095b_router_contract.py::test_business_route_gated_until_ready_while_health_available`)
  was not observed in any WU6 run; it remains documented in WU2/WU3.

## 34. Deferred v0.9.7-C/D/E work

- v0.9.7-C (next): Student Journey functional completion - e.g., a
  target-completed event/state extension, Journey chronology enhancements.
- v0.9.7-D: Student UI/UX consolidation; v0.9.7-E: responsive, mobile, and
  accessibility refinement.
- Also deferred: repository-wide malformed-row repair (G9); API-level
  exercise-instance idempotency (G10).

## 35. WU6 acceptance matrix

All 80 owner-provided WU6 acceptance criteria are satisfied:

1-5. Git history verified; `b9e030d`/`01115ba` roles resolved; stale
  metadata corrected; reconciliation separate; baseline recorded - PASS.
6-7. Protocol frozen before verification; expectations derived from code +
  empirical probe - PASS.
8-11. Projector reconstructed with file:line; event types, provenance,
  dedup keys, ordering documented - PASS.
12-14. Full cycle projects accurately; learner and source associations
  exact - PASS.
15-20. Reads side-effect free; no duplicates on repeated reads, Feedback/
  Revision re-entry, target reuse, repeated completion - PASS.
21-22. Evaluation-unavailable honest; no fabricated evaluation event - PASS.
23-24. Legacy readable; no fabricated priority provenance - PASS.
25. Malformed records fail safely on the verified path (stable error on
  the tampered path; no fabrication/cross-association) - PASS.
26-27. No new Journey event; no migration 14 - PASS.
28-29. No release blocker, hence no fix commit needed - PASS.
30-33. WU2 mapping, WU3 idempotency + migration 13, WU4 task/attempt
  recovery, WU5 evaluation/completion semantics intact (combined 197;
  affected 569; full core 1057) - PASS.
34-37. EN desktop, ZH desktop, EN mobile, ZH mobile main matrices pass
  independently - PASS.
38. Independent learner + isolated DB per combination - PASS.
39-44. Source-scoped counts match contracts; no uncontrolled
  target/exercise/attempt/evaluation/Journey duplicates - PASS.
45. Reload/re-entry preserve completed state - PASS.
46-49. Evaluation-unavailable, multiple-target, no-priority, legacy
  scenarios pass - PASS.
50. Research baseline passes - PASS (6/6).
51-53. No console errors, page errors, or uncaught exceptions - PASS.
54-57. No raw keys, no overflow, no remote requests, mobile sizing >= 44px
  - PASS.
58. No mastery/pass/learning-gain/transfer/proficiency/CEFR/improvement
  claim appears - PASS (fixed Journey wording checked; "passed the
  Diagnostic Gate" is a gate description).
59-62. Focused 18; combined 197; affected 569; full core 1057/8 - PASS.
63-64. Launcher PASS twice; locale parity 572/572 - PASS.
65. Contract/snapshot deltas understood (none) - PASS.
66. Fresh-index impact review completed via GitNexus CLI (fresh index at
  `d124a83`; 0 production symbols) - PASS.
67-68. `git diff --check b0f16b5..HEAD` clean; no unrelated changes - PASS.
69. User-owned files untouched and uncommitted - PASS (section 37).
70. Reproducible Git/file/line/test/database/event/screenshot/network/log
  evidence recorded - PASS.
71-72. RUN_VERIFICATION_V0.9.7_B_WU6.md and RUN_VERIFICATION_V0.9.7_B.md
  complete - PASS.
73. Project-state documents agree - PASS.
74-77. No unresolved release blocker; v0.9.7-B complete/verified/closed;
  WU1-WU6 complete; v0.9.7-C next only - PASS.
78-80. Final release HEAD recorded; final `git status --short` recorded;
  no push/pull request - PASS.

## 36. Final Git state and closure commit

- Closure commit: `docs(v0.9.7-b): close priority-guided practice cycle`
  (exact hash recorded in the final chat report).
- Final release HEAD: the closure commit on `master`; the implementation
  tree HEAD before closure was `51e89db`.
- `git status --short` after closure: only the preserved user-owned
  entries (modified `AGENTS.md`, `RUN_VERIFICATION_V0.7.md`,
  `RUN_VERIFICATION_V0.8.2.md`; untracked `.claude/`, `CLAUDE.md`,
  `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `data/demo_journey_manifest.json`,
  and the pre-existing v0.9.7-a run logs/probe screenshot) plus gitignored
  WU6 run logs/isolated DB.

## 37. Preserved user-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
and `data/demo_journey_manifest.json` were never modified, staged,
committed, or deleted by WU6 (verified by `git status --short` at every
gate).

## 38. Release-closure decision

**v0.9.7-B is complete, verified, and closed. The priority-guided revision
and Practice cycle is operational end to end, and the next planned phase is
v0.9.7-C.**
