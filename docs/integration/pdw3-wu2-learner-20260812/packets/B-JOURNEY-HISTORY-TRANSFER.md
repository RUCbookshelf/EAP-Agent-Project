# RETRY-2 Worker B — Practice History / Authentic Application Projections

You are a third-level implementation worker for
`PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`.

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

- `app/journey/service.py`
- `app/journey/cycles.py`
- `app/journey/transfer.py` (new typed projection helpers if useful)
- `tests/learner/test_wu2_journey_history_transfer.py` (new focused tests)
- `docs/integration/pdw3-wu2-learner-20260812/workers/B/findings.md`

Do not edit `app/practice`, `app/learner`, `app/api`, infrastructure/repository
files, migrations, or any test file outside the list. Preserve existing
Journey response keys and Wave-2 behavior.

## Required context

Read:

1. `docs/integration/pdw3-wu2-learner-20260812/CHECKPOINT-002-RETRY2-DISPATCH-SURFACE.md`.
2. CORE WU1 handoff at
   `A:\EAP Agent Project\worktrees\shared-core\docs\integration\pdw3-wu1-recovery-20260811\CORE-WU1-DEPARTMENT-HANDOFF.md`.
3. Current learner `app/journey/service.py`, `cycles.py`, practice schemas,
   practice repository, and existing Wave-2 journey/practice tests.
4. `AGENTS.md` and the Goal Packet constraints in the executor prompt.

## Implementation objective

Implement WU2 history and transfer projections using existing learner-owned
read ports:

- Add a clearly typed practice-history projection that lists PracticeActivity /
  ReviewEvent or existing practice records as activity/evidence, with stable
  IDs, timestamps, provenance/version fields, rating-channel visibility where
  available, and explicit activity-only limitations.
- Add a clearly separate authentic writing application observation projection
  using later writing/submission observations and the existing within-task /
  transfer candidate concepts. It must retain comparability, source/later
  submission IDs, observation status, provenance, and limitations.
- Never merge practice completion/review into authentic writing evidence and
  never infer causal transfer, mastery, proficiency, ability, or learning
  gain. A non-comparable or insufficient observation must remain explicitly
  non-comparable/insufficient.
- Preserve existing `JourneyService.get_journey()` output and Wave-2 route
  compatibility. Additive sections are acceptable; changing/removing existing
  keys is not.
- Avoid new persistence or migration. Consume existing repository ports and
  CORE-shaped data without importing/copying `app/review` implementation.

## Verification contract

Use TDD and run the focused tests. Cover:

- separate practice-history and authentic-application sections/channels;
- stable ordering and stable IDs/provenance;
- insufficient history and non-comparable tasks fail closed descriptively;
- no causal or normative outcome language;
- existing Wave-2 journey tests remain green.

Record exact commands, counts, changed files, and any compatibility risks in
`workers/B/findings.md`. Return a compact result and findings path. If the
existing Journey contracts cannot be extended without changing an unowned API
or repository file, report `BLOCKED` rather than editing outside scope.

