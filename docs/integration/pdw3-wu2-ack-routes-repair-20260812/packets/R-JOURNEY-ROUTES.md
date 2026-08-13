# Repair Worker R — Two Approved Journey Projection Routes

You are a nested implementation worker for
`PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`.

## Mandatory execution contract

- Model: `deepseek/deepseek-v4-flash`
- Reasoning: `ultra` (injected by the opencodex proxy; do not change it)
- Environment: `PLANNING_DISABLED=1` (already set by the parent dispatcher)
- Authorized worktree: `A:\EAP Agent Project\worktrees\learner`
- Branch: `dept/feedback-learner`; HEAD: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- No provider/model/reasoning substitution. No commit, push, PR, merge,
  promotion, reset, clean, restore, rebase, or Program Control write.
- Do not modify Program Control, other worktrees, Git history, or
  promotion state. Do not touch raw SWECCL.
- Do not edit any file outside your owned write scope. If a requirement
  cannot be satisfied inside that scope, stop and report `BLOCKED` with the
  exact boundary; do not edit outside scope.

## Preserve (never modify or delete)

- The five pre-existing untracked evidence paths:
  `docs/integration/LEARNER-FOUNDATION-FREEZE-20260809.md`,
  `docs/integration/PDW1-ALIGN-LEARNER-B6FCE9-20260809.md`,
  `docs/integration/PDW2-ALIGN-LEARNER-59500127-20260810.md`,
  `docs/integration/PDW3-ALIGN-LEARNER-7A9E4B-20260811.md`,
  `tests/learner/__init__.py`.
- Every existing WU2 file, including `app/journey/service.py` and
  `app/journey/transfer.py`: you must NOT change the JourneyService or its
  projections; you only expose the two already-implemented projection
  methods through the existing learner-owned Journey router.

## Owned write scope (exact)

1. `app/api/routers/journey.py` — add exactly two learner-owned routes.
2. `tests/learner/test_wu2_journey_routes.py` — new focused tests.
3. `docs/integration/pdw3-wu2-ack-routes-repair-20260812/workers/R/findings.md`
   — your durable findings report.

Do NOT edit `app/api/main.py`, `app/api/deps.py`, `app/journey/`,
`app/learner/`, `app/practice/`, or any other test file. The parent wires
composition after you return.

## Required context (read before writing)

1. `app/api/routers/journey.py` (current single-route router).
2. `app/journey/service.py` — `JourneyService.get_practice_history(student_id)`
   and `get_authentic_application(student_id)` already exist and are fully
   implemented; do not modify them.
3. `app/api/deps.py` — `get_journey_service` and `require_student` already
   exist.
4. `tests/learner/test_wu2_journey_history_transfer.py` — proves the service
   projections; your routes must not change their behavior.

## Implementation spec (follow exactly)

In `app/api/routers/journey.py`, keep the existing
`GET /api/v1/students/{student_id}/journey` route unchanged and add exactly
two additive routes in the same style:

1. `GET /api/v1/students/{student_id}/journey/practice-history`
   - `require_student(journey_service.student_reader, student_id)`, then
     return `journey_service.get_practice_history(student_id)`.
2. `GET /api/v1/students/{student_id}/journey/authentic-application`
   - `require_student(journey_service.student_reader, student_id)`, then
     return `journey_service.get_authentic_application(student_id)`.

Use the existing `APIRouter`, `Depends(get_journey_service)` convention.
Add short docstrings naming them as learner-owned route-facing projections
of the practice-history (activity/evidence only) and authentic-writing
application (separate channel) sections. No new dependency, service,
persistence, or schema changes.

## Verification contract

Use the worktree `.venv`:
`PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest tests/learner/test_wu2_journey_routes.py tests/learner/test_wu2_journey_history_transfer.py -q --no-header -p no:cacheprovider`

Your new tests must cover:

- The two paths are registered exactly once each with GET, alongside the
  existing journey route, with no duplicate path/method pairs in an isolated
  app that includes the router.
- Unknown student returns 404 for both routes (the router's
  `require_student` guard) and no projection read occurs.
- Known student returns 200 with the expected projection section keys
  (`section`, `learner_id`, `available`, `status`, `counts`, `limitations`)
  using deterministic stub readers; use `JourneyService` with stub ports so
  the real service behavior is exercised.
- The existing `GET /journey` route still returns its unchanged journey
  payload.
- The existing journey history/transfer service tests stay green.

Record exact commands, exit codes, pass counts, changed-file list, and any
compatibility risk in your findings file. Return a compact result including
status, files, tests, and the findings path. If anything forces an edit
outside scope, stop with `BLOCKED` and explain the exact boundary.
