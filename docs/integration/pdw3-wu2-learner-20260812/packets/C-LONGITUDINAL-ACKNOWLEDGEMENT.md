# RETRY-2 Worker C — Positive Longitudinal Acknowledgement / Safety

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

- `app/learner/acknowledgement.py` (new typed contracts/service)
- `app/learner/acknowledgement_contracts.py` (new contracts if useful)
- `app/api/routers/acknowledgement.py` (new learner-owned router only)
- `tests/learner/test_wu2_acknowledgement.py` (new focused tests)
- `docs/integration/pdw3-wu2-learner-20260812/workers/C/findings.md`

Do not edit `app/learner/__init__.py`, `app/api/main.py`, `app/api/deps.py`,
`app/practice`, `app/journey`, infrastructure/repositories, migrations, or
any test file outside the list. Worker D will wire the router/service into the
single composition root after this slice returns.

## Required context

Read:

1. `docs/integration/pdw3-wu2-learner-20260812/CHECKPOINT-002-RETRY2-DISPATCH-SURFACE.md`.
2. CORE WU1 handoff at
   `A:\EAP Agent Project\worktrees\shared-core\docs\integration\pdw3-wu1-recovery-20260811\CORE-WU1-DEPARTMENT-HANDOFF.md`.
3. Current learner `app/learner/evidence.py`, `exposure.py`, `normative.py`,
   `history.py`, `practice_provenance.py`, and existing learner tests.
4. Current API router conventions and `AGENTS.md`.

## Implementation objective

Implement a positive, longitudinal acknowledgement contract over already
admitted learner evidence, with these hard boundaries:

- Acknowledgement is a descriptive learner-facing acknowledgement of observed
  evidence or a bounded practice/history signal. It is not mastery,
  proficiency, writing ability, learning gain, score, ranking, diagnosis,
  recommendation, or causal transfer attribution.
- Require explicit learner consent for learner-facing acknowledgement. Missing,
  false, malformed, revoked, or otherwise invalid consent must fail closed with
  no acknowledgement write/return.
- Require non-empty source evidence IDs, stable provenance, policy/model/config
  or record version, and an explicit evidence status. Missing or invalid
  provenance/version/status must fail closed.
- Preserve the distinction between source event, observed evidence, diagnostic
  inference, feedback recommendation, practice activity/result, and outcome.
- Use the existing normative scanner or equivalent fail-closed check to reject
  normative/ability/causal language in generated or supplied text.
- No new database, migration, scheduler, or runtime. An injected append-only
  store/port is acceptable for the contract and tests; do not silently invent a
  second persistence authority.
- Add a learner-owned router with a stable, additive path if the existing API
  conventions allow it. The router must depend on
  `request.app.state.acknowledgement_service`; do not wire `main.py` or
  `deps.py` in this slice.

## Verification contract

Use TDD. Test positive acknowledgement with consent and complete provenance,
then test no-consent, missing evidence, missing provenance/version, invalid
status, normative/causal text, cross-student source, duplicate/conflict, and
malformed payload paths. Assert no-write behavior for failed cases. Test the
router in isolation if added. Record exact commands/counts and changed files
in `workers/C/findings.md`. Return a compact result and findings path.

