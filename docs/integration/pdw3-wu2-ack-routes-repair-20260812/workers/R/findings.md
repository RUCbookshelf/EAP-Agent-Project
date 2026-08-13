# Repair Worker R — Journey Projection Routes: Findings

Packet: `R-JOURNEY-ROUTES.md`
Goal: `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`
Date: 2026-08-12

## Status

**COMPLETE** — both approved additive routes are implemented, verified, and
reported. No edit outside the owned write scope was required.

## Environment identity (preflight)

- Worktree: `A:\EAP Agent Project\worktrees\learner`
- Branch: `dept/feedback-learner`
- HEAD: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` (matches packet contract)
- Python: worktree-local `.venv\Scripts\python.exe`
- Pre-existing untracked evidence paths and WU2 files preserved untouched
  (verified via `git status --porcelain` before and after).

## Changed files (exactly the owned scope)

1. `app/api/routers/journey.py` — modified (+20 lines), additive only:
   - `GET /api/v1/students/{student_id}/journey/practice-history` —
     `require_student(journey_service.student_reader, student_id)` then
     `journey_service.get_practice_history(student_id)`.
   - `GET /api/v1/students/{student_id}/journey/authentic-application` —
     `require_student(journey_service.student_reader, student_id)` then
     `journey_service.get_authentic_application(student_id)`.
   - Existing `GET /api/v1/students/{student_id}/journey` route left byte
     unchanged; same `APIRouter` / `Depends(get_journey_service)` convention;
     short docstrings name them as learner-owned route-facing projections
     (practice-history = activity/evidence only; authentic-application =
     separate channel).
   - `app/journey/service.py` and `app/journey/transfer.py` not touched.
2. `tests/learner/test_wu2_journey_routes.py` — new file: focused route tests
   in an isolated FastAPI app that includes only the journey router, with
   `get_journey_service` overridden by a real `JourneyService` on
   deterministic stub ports.
3. `docs/integration/pdw3-wu2-ack-routes-repair-20260812/workers/R/findings.md`
   — this report.

No changes to `app/api/main.py`, `app/api/deps.py`, `app/journey/`,
`app/learner/`, `app/practice/`, or any other test file.

## Verification commands and results

Command 1 (packet contract):

```
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest
  tests/learner/test_wu2_journey_routes.py
  tests/learner/test_wu2_journey_history_transfer.py
  -q --no-header -p no:cacheprovider
```

Result: **25 passed, 0 failed** (exit code 0) in 4.49s. The existing
journey history/transfer service tests stay green alongside the new route
tests.

Command 2 (compatibility sweep, learner suite):

```
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest tests/learner
  -q --no-header -p no:cacheprovider
```

Result: **287 passed, 0 failed** (exit code 0) in 28.48s.

## Coverage against the verification contract

- Both new paths registered exactly once with GET alongside the existing
  journey route; no duplicate path/method pairs in the isolated app
  (`TestProjectionRouteRegistration`).
- Unknown student returns 404 for both new routes via the router's
  `require_student` guard with no projection read (call-tracking stubs:
  `get_student` x2 only) (`TestProjectionRouteGuards`).
- Known student returns 200 for both routes with the expected section keys
  (`section`, `learner_id`, `available`, `status`, `counts`, `limitations`)
  and payloads byte-equal to the real `JourneyService` projections, using
  `JourneyService` with stub ports (`TestPracticeHistoryRoute`,
  `TestAuthenticApplicationRoute`).
- Existing `GET /journey` returns its unchanged journey payload, including
  the empty-journey shape (`TestExistingJourneyRouteUnchanged`).
- Existing service projections and port-call surface unchanged (the
  untouched `test_wu2_journey_history_transfer.py` suite passes).

## Compatibility risk

- None observed. No other router in `app/api/routers` defines these two
  paths (grep confirmed), so full-app composition will not collide.
- One warning only (pre-existing, not introduced): Starlette testclient
  deprecation about `httpx` vs `httpx2`, and a spacy/Click deprecation in
  `test_wu2_api_composition.py`. Neither is caused by this change.
- Git reports an LF→CRLF normalization notice on the edited router file
  (repository autocrlf behavior); no functional impact.
- Parent still owns composition wiring (`app/api/main.py` unchanged here)
  and must include the journey router's new routes in the acceptance
  report and the full regression run before integration.
