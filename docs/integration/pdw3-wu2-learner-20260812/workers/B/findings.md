# RETRY-2 Worker B findings - Practice History / Authentic Application Projections

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- goal_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`
- owner: LEARNER
- worktree / branch / HEAD: `A:\EAP Agent Project\worktrees\learner` /
  `dept/feedback-learner` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- model / reasoning / env: `deepseek/deepseek-v4-flash` / ultra /
  `PLANNING_DISABLED=1` (no substitution)
- verdict: **DONE** (no commit, no push, no Program Control write)

## 1. Owned write scope (exactly these files)

- `app/journey/service.py` (modified: two additive methods + one import)
- `app/journey/transfer.py` (new: typed projection models + builders +
  optional structural review-event read port)
- `tests/learner/test_wu2_journey_history_transfer.py` (new focused tests)
- `docs/integration/pdw3-wu2-learner-20260812/workers/B/findings.md` (this)

`app/journey/cycles.py` was NOT changed (no cycle-model change was needed).
No file outside the list was edited. Pre-existing untracked LEARNER evidence
paths were preserved byte-for-byte.

## 2. Design decision: additive service methods, not new Journey keys

`JourneyService.get_journey()` output is pinned byte-for-byte by
`tests/test_v095f4_reanalysis_journey_narrowing.py`:

- `test_empty_journey_output_unchanged` asserts the EXACT result dict
  (adding any top-level key would fail);
- `test_exact_names_methods_and_source_signatures` pins the exact public
  method sets of `JourneyProjectionReadPort` (9 methods) and
  `JourneyStudentReadPort` (`get_student`);
- `test_minimal_stubs_sufficient_and_only_nine_methods_requested` pins the
  exact set of projection calls during `get_journey`;
- the service source scan forbids `app.database`, `SQLite`, `self.repo`, and
  `hasattr(` in `app/journey/service.py`.

Because these tests are unowned and the verification contract requires them
to remain green, the two WU2 projections were added as clearly typed,
additive `JourneyService` entry points:

- `get_practice_history(student_id) -> dict` - practice-history projection;
- `get_authentic_application(student_id) -> dict` - authentic writing
  application observation projection.

Both consume only the existing learner-owned projection port methods
(`getattr`-based structural detection of the optional
`list_review_events_by_student` read; no new protocol method on the pinned
ports). Worker D's packet ("ensure the existing Journey router exposes
Worker B's additive projection through the existing JourneyService") is the
authorized surface for exposing these through the composition root.

## 3. Implementation summary

### `app/journey/transfer.py` (new)

- `PracticeActivityRecord` / `PracticeHistoryProjection`: typed,
  `extra="forbid"`, with `section="practice_history"`, a projection version
  (`journey-practice-history-v0.9.7`), stable `record_id`, `occurred_at`,
  provenance/version fields, `evidence_kind="practice"`, and
  `rating_channel_visibility` ("available" only when a CORE-shaped
  review-event reader is present).
- Records are derived from persisted practice targets (activity),
  exercise attempts (activity), practice evaluations (evidence), and -
  when injected - CORE-shaped `ReviewEvent` rows consumed structurally
  (field names mirror the CORE JSON keys; `app/review` is never imported or
  copied). The three rating channels
  (`system_provisional_rating`, `learner_self_rating`,
  `final_scheduler_rating`) are preserved separately and verbatim with
  `rating_rule_version` / `scheduler_implementation` / `scheduler_version` /
  `scheduler_parameters` / state snapshots in provenance; nothing is
  averaged or reinterpreted.
- `AuthenticApplicationObservation` / `AuthenticApplicationProjection`:
  typed, `extra="forbid"`, `section="authentic_application"`, version
  `journey-authentic-application-v0.9.7`. Observations are built only from
  later submissions (persisted revision links), within-task response
  candidates, and transfer evidence candidates, keeping source/later
  submission ids, `observed_status`, `comparability`, `comparison_version`,
  provenance, and limitations. Stored `observed_status` and
  `task_comparability` values are retained verbatim, so
  `not_comparable` / `insufficient_evidence` / `version_incompatible`
  observations remain explicitly non-comparable/insufficient.
- Fixed limitation strings deny mastery/proficiency/ability/learning gain,
  deny causal transfer inference, and state that practice completion/review
  does not imply authentic writing transfer; review scheduler state is
  labeled memory scheduling state only.
- Malformed rows fail closed: non-dict or empty-id review rows are skipped;
  missing rating channels stay `null` with an explicit limitation; no
  fabricated field is emitted.

### `app/journey/service.py` (modified, additive only)

- `get_practice_history` / `get_authentic_application` (each calls
  `_require_learner` first, raising `LookupError("Student not found.")`
  before any projection read, mirroring `get_journey`).
- `get_journey()` and the constructor are untouched; the source-scan pins
  (no `app.database`, `SQLite`, `self.repo`, `hasattr(`) hold.

## 4. Verification (TDD; exact commands and counts)

Environment: worktree `.venv` (Python 3.12.13, pytest 9.1.1).

```text
.\.venv\Scripts\python.exe -m pytest tests/learner/test_wu2_journey_history_transfer.py -q --no-header -p no:cacheprovider
```

- Red (missing behavior): 15 failed / 3 passed.
- Green (after implementation): 18 passed / 0 failed.

Covered by the 18 focused tests:

- separate practice-history and authentic-application sections/channels
  (`section` literals, disjoint record kinds, practice records never merge
  into the authentic section);
- stable ordering and stable IDs/provenance (deterministic record order,
  verbatim stored ids, version fields; repeated reads identical);
- insufficient history and non-comparable/insufficient observations fail
  closed descriptively (`insufficient_history`, `insufficient`, verbatim
  `not_comparable` / `insufficient_evidence` statuses);
- rating channels preserved separately and verbatim when the optional
  CORE-shaped review reader is present; `unavailable` with an explicit
  limitation when it is absent (including the real repository);
- malformed review rows fail closed without fabrication;
- unknown student raises `LookupError` before any projection read;
- no causal or normative outcome language (field-level forbidden-token
  scan + fixed denial limitations);
- `get_journey()` output byte-identical (empty) and unchanged (populated);
  `get_journey` still calls exactly the pinned nine port methods;
- real `SQLitePracticeRepository` consumption on an isolated temporary
  database, read-only and side-effect free.

Affected Wave-2 regression (all green):

```text
439 passed  - tests/test_v095f4_reanalysis_journey_narrowing.py,
             tests/test_journey_v093c.py,
             tests/test_v097b_wu6_journey_projection.py,
             tests/test_v097c_wu1_journey_cycles.py,
             tests/test_v097c_wu2_journey_navigation.py,
             tests/test_v097c_wu3_journey_ui.py,
             tests/test_v097c_wu4_release.py,
             tests/test_v095g_facade_contraction.py,
             tests/test_v095f6d_practice_boundary_narrowing.py,
             tests/learner/ (including the 18 new tests)

249 passed  - practice WU2-WU6 + composition-root + service-narrowing suites
             (test_v097b_wu2..wu5, test_composition_root,
              test_v095f2/f3/f6a/f6c narrowing suites)
```

Total re-verified on this slice: 18 + 439 + 249 = 706 tests, 0 failed.

## 5. Compatibility risks / observations (for Worker D / INT)

1. The new projections are NOT yet exposed through any API route; Worker D
   owns the composition step that surfaces `get_practice_history` /
   `get_authentic_application` through the existing `JourneyService`
   (per packet D).
2. Through the current real repository (`SQLitePracticeRepository`), the
   optional `list_review_events_by_student` read does not exist, so
   `rating_channel_visibility` is honestly `unavailable` until the
   integrated CORE review reader (Worker A bridge / INT composition root)
   provides it. No schema change is needed to surface it.
3. `comparability="within_task"` / `"within_task_revision"` are derived from
   the persisted record kind / revision link (the candidate concept and the
   revision relationship), not from learner performance; transfer
   `task_comparability` is always passed through verbatim.
4. Projection versions are `journey-practice-history-v0.9.7` /
   `journey-authentic-application-v0.9.7` (no fabricated release suffix).
5. Timestamps are normalized to UTC microseconds (same convention as the
   raw Journey events) for deterministic ordering and stable output.
6. `cycles.py` untouched; existing `get_journey()` keys and Wave-2 route
   behavior preserved; no persistence, migration, or repository change.

## 6. Resource hygiene

No commit/push/PR/merge/promotion/reset/clean/restore/rebase; no Program
Control write; no other worktree touched; no raw SWECCL access. Pre-existing
untracked paths preserved. Only the four owned files above were created or
modified.
