# RETRY-2 Worker A — Practice / Review Dual-Channel Evidence

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

- `app/practice/review_transfer.py` (new learner-owned orchestration)
- `app/learner/review_bridge.py` (new structural CORE-consumption port/bridge)
- `app/infrastructure/learner_review.py` (new learner adapter only, if needed)
- `tests/learner/test_wu2_practice_review_evidence.py` (new focused tests)
- `docs/integration/pdw3-wu2-learner-20260812/workers/A/findings.md`

Do not edit existing files in `app/review`, `app/api`, `app/journey`,
`app/learner/__init__.py`, existing repositories, migrations, or any test file
outside the list. Do not copy CORE implementation into LEARNER.

## Required context

Read:

1. `docs/integration/pdw3-wu2-learner-20260812/CHECKPOINT-002-RETRY2-DISPATCH-SURFACE.md`.
2. `A:\EAP Agent Project\worktrees\shared-core\docs\integration\pdw3-wu1-recovery-20260811\CORE-WU1-DEPARTMENT-HANDOFF.md`.
3. CORE `app/review/models.py`, `protocols.py`, `service.py`, and
   `rating_policy.py` from `A:\EAP Agent Project\worktrees\shared-core`.
4. Learner `app/practice/service.py`, `ports.py`, `schemas.py`, and the current
   SQLite practice repository.
5. `AGENTS.md` and the Goal Packet constraints in the executor prompt.

## Implementation objective

Implement the learner-owned WU2 bridge for Practice/Review evidence while
consuming the shared CORE review contracts structurally:

- Define a narrow Protocol/adapter boundary that can receive the integrated
  CORE `ReviewService`/repository later. Do not duplicate `app/review` or make
  a second scheduler, database, runtime, or migration.
- Preserve the distinction between `PracticeActivity`, `ReviewEvent`,
  `LearningItem v1`, authentic writing evidence, observed evidence, diagnostic
  inference, feedback recommendation, and learning outcome.
- Preserve the three CORE rating channels separately: system provisional,
  learner self-rating, and final scheduler rating. Carry the CORE rating-rule
  version and scheduler identity/version/parameters in provenance; do not
  average or reinterpret them.
- Provide a learner-owned orchestration entry point that records a practice
  activity and, when explicitly requested with valid UTC time and valid
  inputs, records a review through the injected CORE service. Missing CORE
  service, missing durable LearningItem, ownership mismatch, invalid rating,
  invalid authentic-evidence status, or malformed provenance must fail closed
  before a write.
- Keep practice evidence and authentic writing application evidence as two
  separate channels. Practice completion/review must not imply authentic
  transfer or any outcome claim.
- Keep provenance/version fields explicit and make reconstructed evidence
  deterministic from stored fields.

Use the existing project error conventions where applicable. The public
surface may use learner-owned typed records or dicts, but it must be easy for
the future INT composition root to inject the actual CORE service without a
second store.

## Verification contract

Use TDD: add focused tests first and run them red for the missing behavior,
then implement the smallest change and run them green. Tests must cover at
least:

- practice activity is labeled as practice and distinct from authentic
  evidence;
- all three rating channels and rating-rule/scheduler provenance survive the
  bridge;
- CORE service is actually called through the injected boundary;
- invalid rating, non-UTC time, missing item/service, ownership mismatch,
  malformed provenance, duplicate/conflict, and invalid status fail closed;
- no mastery/proficiency/ability/learning-gain/causal language is emitted;
- the two evidence channels remain separate.

Run the focused file with the worktree Python environment. Record exact test
commands and output counts in `workers/A/findings.md`. Return a compact result
with status, changed files, tests, risks, and findings-file path. If the CORE
candidate cannot be consumed safely without an unowned file change, stop with
`BLOCKED` and explain the exact boundary.

