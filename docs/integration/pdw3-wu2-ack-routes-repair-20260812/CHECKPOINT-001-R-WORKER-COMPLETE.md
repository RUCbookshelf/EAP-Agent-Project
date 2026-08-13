# CHECKPOINT 001 — Repair Worker R Complete (Journey Routes)

- Goal/run: `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`
  / `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812__20260812T014849Z__710c45`
- Owner: LEARNER (parent). Worker route:
  `deepseek/deepseek-v4-flash`, reasoning `ultra`, `PLANNING_DISABLED=1`
  (dispatch via `codex exec` with the opencodex proxy; no substitution).
- Worktree/branch/HEAD: `A:\EAP Agent Project\worktrees\learner` /
  `dept/feedback-learner` / `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`.
- Checkpoint written: 2026-08-12 (Asia/Shanghai) after Worker R returned.

## Worker R result

- Status: COMPLETE (no BLOCKED; no edit outside owned scope).
- Files (exactly owned scope):
  - `app/api/routers/journey.py` (+20 additive lines): the two approved
    learner-owned routes
    `GET /api/v1/students/{student_id}/journey/practice-history` and
    `GET /api/v1/students/{student_id}/journey/authentic-application`;
    existing `GET /journey` route unchanged; `app/journey/service.py` and
    `app/journey/transfer.py` untouched.
  - `tests/learner/test_wu2_journey_routes.py` (new focused tests).
  - `docs/integration/pdw3-wu2-ack-routes-repair-20260812/workers/R/findings.md`.
- Verification (worker-run, worktree `.venv`):
  - `pytest tests/learner/test_wu2_journey_routes.py
    tests/learner/test_wu2_journey_history_transfer.py` -> **25 passed**,
    exit 0.
  - `pytest tests/learner` -> **287 passed**, exit 0.
- Coverage: both paths registered exactly once with GET; unknown student ->
  404 with zero projection reads; known student -> 200 with expected section
  keys; existing journey route payload unchanged; no path collisions with
  any other router.

## Parent actions next

1. Wait for Worker P (persistence/evidence lookup) and audit its output.
2. Parent wires the composition root (`app/api/main.py` optional CORE
   typed-boundary injection + durable store/evidence lookup), updates
   `tests/learner/test_wu2_api_composition.py` for the new fail-closed
   semantics, and runs the full WU2/Journey/Wave-2/Learner regression.
3. Write the canonical repair handoff and remain
   `HANDOFF_PENDING_ACCEPTANCE` until INT/PROGRAM accepts or rejects.

## Resource hygiene (this checkpoint)

- No Git mutation, Program Control write, promotion, or other-worktree
  change. All five pre-existing untracked evidence paths remain untouched.
- Durable evidence paths:
  - `docs/integration/pdw3-wu2-ack-routes-repair-20260812/workers/R/findings.md`
  - `docs/integration/pdw3-wu2-ack-routes-repair-20260812/packets/R-JOURNEY-ROUTES.md`
