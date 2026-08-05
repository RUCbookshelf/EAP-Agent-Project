# v0.9.7-C Work Unit 1 - Journey Cycle Model and Completion State

**Status:** COMPLETE - all 18 WU1 acceptance criteria satisfied (GREEN);
WU2 is the next planned work unit; v0.9.7-C as a whole is NOT complete.
**Date:** 2026-08-05
**Governing protocol:** the owner-provided v0.9.7-C goal (WU1 section) and
`docs/development/V0.9.7_C_SPEC.md` (created by WU1).

## 1. Baseline

- Branch `master`; pre-WU1 HEAD `c4fba8b` (v0.9.7-B closure) - matches the
  expected baseline exactly; no history was rewritten.
- Worktree: only preserved user-owned entries (`AGENTS.md`,
  `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md` modified;
  `.claude/`, `CLAUDE.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`, and pre-existing v0.9.7-a run logs
  untracked).
- Migration 13, config-v0.9.0, locale parity 572/572, full-core baseline
  1057/8 - unchanged.

## 2. Targeted reconnaissance (limited)

Confirmed the persisted relationships needed for grouping
(file:line evidence in `V0.9.7_C_SPEC.md` section 1.2): revision linkage
via `essays.revision_of_submission_id`, feedback via
`feedback_records.essay_id`, target provenance via
`practice_targets.source_submission_id` + `target_json.source_priority_id`,
attempt->target via `exercise_attempts.exercise_id` ->
`exercise_instances.practice_target_id`, evaluation via
`practice_evaluations.attempt_id`. The Journey projection reader lacked an
exercise read; one additive protocol method was required for honest
attempt->target association (documented delta, section 6).

## 3. Implementation delivered

- `app/journey/cycles.py` (new): `JourneyCycle`/`JourneyPracticeCycle`/
  `JourneySubmissionView`/`JourneyFeedbackStage` models
  (`extra="forbid"`), writing/practice/evaluation state vocabulary, cycle
  grouping, revision-root resolution, read-only priority-provenance
  validation, latest-attempt + evaluation association, cycle
  `current_state` derivation, raw-order `chronology`, controlled unlinked
  groups, and cycle limitations.
- `app/journey/service.py`: `JourneyProjectionReadPort` gains
  `list_exercise_instances` (signature-identical to the repository);
  `get_journey` reads exercises once and returns the additive
  `cycles` + `cycles_version` keys alongside the unchanged raw response.
- No route, client, port (UI), locale, migration, or raw-event change.

## 4. Grouping and state rules (frozen in SPEC)

- Anchor = resolved root submission; broken revision chains form
  controlled unlinked cycles; independent essays stay separate.
- Practice attaches through the target's persisted source submission;
  provenance status `valid` / `legacy` / `unresolved` (never fabricated).
- Writing states: `revision_submitted`, `insufficient_evidence`,
  `analyzed`, `feedback_without_priority`, `feedback_available` (base
  `submitted` reserved). Practice states: `available`, `attempted`,
  `evaluation_available`, `evaluation_unavailable`, `completed`
  (defensive `unavailable` for unsupported statuses).
- Completion remains activity completion only; evaluation unavailable
  never implies failure or non-completion.

## 5. Focused tests

New `tests/test_v097c_wu1_journey_cycles.py` (29 tests):

- Cycle grouping: full cycle -> one linked cycle with root + revision;
  independent essays separate; multi-level revision chain; orphan revision
  -> controlled unlinked cycle with limitation; feedback attaches to the
  correct submission.
- Writing states: feedback_available; feedback_without_priority;
  insufficient_evidence; analyzed; revision_submitted.
- Practice association: valid priority provenance (category, reference);
  legacy provenance without fabrication; stale/invalid references ->
  unresolved; active vs completed targets; evaluation available;
  evaluation unavailable (attempt authoritative); completed without
  evaluation; inactive target with attempt -> attempted; multiple targets
  per cycle distinct; unlinked practice target -> controlled
  `cycle-unlinked-practice`.
- No-priority and insufficient-evidence flows honest; learner isolation;
  raw event contract unchanged (11 events, unique dedup keys, no
  `practice_completed`); additive response keys; chronology contains only
  cycle events in raw order with unique keys; repeated reads identical;
  zero writes (12-table count check); malformed feedback JSON and
  malformed priority references fail safely.

Result: **29 passed** (twice - standalone and in the affected batch).

## 6. Contract deltas (documented)

- `JourneyProjectionReadPort`: +`list_exercise_instances` (9 projection
  methods); `get_journey` performs one additional read; response adds
  `cycles`/`cycles_version` (additive; raw events byte-compatible).
- `tests/test_v095f4_reanalysis_journey_narrowing.py` updated: minimal
  reader stub, expected method set, exact empty output, populated fixture
  (one exercise row) - the test now pins the honest nine-method read
  surface.
- `verification/v0.9.5-h1/protocol_inventory.json`: new method entry.
- Canonical service-diff allowlist 32 -> 33 (`app/journey/cycles.py`) in
  `verification/v0.9.5-h2a/isolated_pytest_runner.py` and
  `verification/v0.9.6-dp0-v1/canonical_full_core_command.txt`.
- No new route; OpenAPI unchanged; no client/UI change.

## 7. Affected regression

13 suites (Journey v0.9.3-C, F4 narrowing, H2A/H2C/H2D1 inventories,
repository modularization, practice boundary, WU6 Journey projection, WU5
completion, parity, API contract, router contract, WU1 cycles):
**215 passed / 0 failed / exit 0** under the canonical environment
(`C:\tmp\wu1-affected\affected_final.txt`). One batch hit the known
pre-existing readiness-gate timing flake
(`test_v095b_router_contract.py::test_business_route_gated_until_ready_while_health_available`),
which passes in isolation and passed in the final coherent batch; it is
unrelated to WU1 (no lifecycle change) and remains documented.

## 8. Static checks

- `compileall` OK (app/tests/verification).
- `git diff --check` clean on all WU1 files.
- No locale files changed; no migration; no user-owned file touched.

## 9. WU1 acceptance criteria

1. One complete Writing-Revision-Practice flow groups into one correct
   cycle - PASS (test_full_cycle_groups_into_one_cycle).
2. Independent essays remain separate - PASS.
3. Revisions attach only to their persisted root cycle - PASS (chain +
   orphan tests).
4. Feedback attaches to the correct submission - PASS.
5. Priority-derived Practice attaches to the correct writing cycle - PASS
   (valid provenance + cycle attachment).
6. Legacy Practice remains readable without fabricated provenance - PASS.
7. No-priority and insufficient-evidence flows represented honestly -
   PASS.
8. Active/attempted/evaluation-available/evaluation-unavailable/completed
   states accurate - PASS.
9. Completion creates no new raw event - PASS.
10. Existing raw-event response remains compatible - PASS (additive keys;
    raw events byte-identical).
11. Learner isolation preserved - PASS.
12. Repeated reads deterministic - PASS.
13. Cycle reads cause zero writes - PASS.
14. No migration - PASS.
15. Focused tests pass - PASS (29).
16. Directly affected Journey/API regression passes - PASS (215).
17. Static checks and `git diff --check` pass - PASS.
18. User-owned files untouched - PASS.

## 10. Commits and final Git state

- `feat(v0.9.7-c): add Student Journey cycle model`
  - app/journey/cycles.py (new), app/journey/service.py, H1 protocol
    inventory, canonical allowlist (32 -> 33, both copies).
- `test(v0.9.7-c): verify Journey grouping and states`
  - tests/test_v097c_wu1_journey_cycles.py (new, 29 tests),
    tests/test_v095f4_reanalysis_journey_narrowing.py (documented delta).
- `docs(v0.9.7-c): close work unit 1`
  - RUN_VERIFICATION_V0.9.7_C_WU1.md (this report),
    docs/development/V0.9.7_C_SPEC.md (living spec, WU1 section).

Post-WU1 HEAD recorded in the final chat report. `git status --short`
after the commits shows only the preserved user-owned entries. No push or
pull request (not instructed).

## 11. Gate result

**GREEN** - all 18 acceptance criteria satisfied; no core invariant
failure; no AMBER/RED issues; WU2 (Safe Journey Navigation and Midpoint
Integration) may begin. v0.9.7-C as a whole remains incomplete.
