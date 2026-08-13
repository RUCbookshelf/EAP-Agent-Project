# RETRY-2 Worker D — API Composition / Wave-2 Compatibility

You are a third-level implementation worker for
`PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`.

This packet is dispatched only after Workers A, B, and C have returned. Their
source files are inputs, not your write scope.

## Mandatory execution contract

- Model: `deepseek/deepseek-v4-flash`
- Reasoning: `ultra`
- Environment: `PLANNING_DISABLED=1`
- Authorized worktree: `A:\EAP Agent Project\worktrees\learner`
- Branch: `dept/feedback-learner`
- Starting baseline: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- No provider/model/reasoning substitution.
- No commit, push, PR, merge, promotion, reset, clean, restore, rebase, or
  Program Control write.

## Owned write scope (do not edit outside this list)

- `app/api/main.py`
- `app/api/deps.py`
- `tests/learner/test_wu2_api_composition.py` (new focused tests)
- `tests/test_composition_root.py` (only if an additive assertion is required)
- `docs/integration/pdw3-wu2-learner-20260812/workers/D/findings.md`

Do not edit Worker A/B/C source or focused test files, migrations,
infrastructure/repositories, UI, CORE, L2, UX, Academic, Corpus, Governance,
INT, or Program Control.

## Required context

Read:

1. `docs/integration/pdw3-wu2-learner-20260812/CHECKPOINT-002-RETRY2-DISPATCH-SURFACE.md`.
2. Worker A/B/C findings and changed files under
   `docs/integration/pdw3-wu2-learner-20260812/workers/`.
3. Current `app/api/main.py`, `app/api/deps.py`, router conventions, and
   composition/Wave-2 tests.
4. CORE WU1 handoff and the Goal Packet acceptance constraints.

## Implementation objective

Integrate the completed learner slices through the existing single
composition root:

- Wire the Worker A practice/review bridge and Worker C acknowledgement
  service through `app.state` with dependency injection. If the integrated CORE
  review service is not present on this branch, preserve a typed optional
  injection boundary; do not copy CORE code or create a second store.
- Include Worker C's learner-owned acknowledgement router exactly once.
- Ensure the existing Journey router exposes Worker B's additive projection
  through the existing `JourneyService`; preserve all Wave-2 routes and keys.
- Keep one application, one process, one SQLite database, one API namespace,
  one composition root. No Migration 14/15 edits, second scheduler, runtime,
  or database.
- Keep invalid inputs fail closed and preserve ownership/consent/version and
  semantic boundaries.

## Verification contract

Use TDD for any new composition behavior. Run focused WU2 tests, the affected
composition/Wave-2 tests, and the existing practice/journey/learner suites
needed to establish compatibility. Inspect route registration for duplicate
paths and inspect the app state for one repository/database authority. Record
exact commands, counts, changed files, and any residual concern in
`workers/D/findings.md`. Return a compact result and findings path. If a
worker's implementation requires unowned edits, report `BLOCKED` rather than
editing that file.

