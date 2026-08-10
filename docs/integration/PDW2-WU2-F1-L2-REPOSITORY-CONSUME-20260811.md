# PDW2-WU2-F1 L2 Repair — Shared Repository Consumption (2026-08-11)

**Goal:** `PDW2-WU2-F1-L2-REPOSITORY-CONSUME`
**Owner:** L2 (canonical worktree `worktrees\l2-writing`, branch `dept/l2-writing`)
**Starting SHA:** `b13155d23a3f416fd5a8d116f007120a15e9cf12`
**Source:** PROGRAM-authorized F-1 repair (L2 side) from the WU2 INT gate
(`PDW2-WU2-INT-INTEGRATION-GATE`, AMBER, handoff
`PDW2-WU2-INT-INTEGRATION-GATE__20260810T162500Z__df3a05`).

## F-1 (L2 side) defect

The composed Wave-2 app mounted the revision and personalized routers with
disconnected per-router in-memory repositories
(`revision_api._DEFAULT_REPOSITORY`, `personalized_api._DEFAULT_REPOSITORY`).
Direct gate evidence: through the real composed app,
`POST /api/v1/wave2/personalized/priority-plan` returned 404
`Writing task not found: WT000001` for a task created via the revision router,
and LearningItem creation was unreachable through the API.

Repair split by PROGRAM: CORE composes one shared
`SQLiteWave2Repository` and exposes it at `app.state.wave2_repository`
(sibling packet `PDW2-WU2-F1-F3-CORE-COMPOSITION`); L2 routers consume it
when present and fall back to the module-local repository only for standalone
test contexts (this packet).

## Changes (L2 side, write scope only)

| File | Change |
| --- | --- |
| `app/api/routers/wave2_modules/revision_api.py` | `get_revision_loop_service` now reads `request.app.state.wave2_repository` when present and passes it to `RevisionLoopService`; falls back to `_DEFAULT_REPOSITORY` only when absent (standalone test contexts). Composition-root service 503 guard unchanged. |
| `app/api/routers/wave2_modules/personalized_api.py` | `get_personalized_bridge_service` consumes `request.app.state.wave2_repository` when present; same fallback semantics. |
| `tests/wave2_l2_pipeline.py` | Refactored the real-pipeline builder into `build_real_services` (returns pipeline + repository + submission_service + reanalysis_service) so composition-aware router tests can attach the raw composition-root services to `app.state`; `build_real_pipeline` contract unchanged. |
| `tests/test_wave2_l2_repository_consume.py` | New coverage: shared-repository consumption (revision service, personalized service, one shared instance across both routers, and the F-1 cross-router visibility flow: task → V1 → priority plan → LearningItem through the DEFAULT dependencies) plus standalone fallback (module-local repository for both dependencies; standalone flow still functional without the shared store). |

No other files changed. No `app/api/main.py`, no `migrations.py`, no
program-control files, no raw SWECCL access.

## Verification (all GREEN)

### L2 wave2 suites + new coverage

Command (worktree venv, task-scoped `--basetemp` under `%TEMP%`):

```text
.venv\Scripts\python.exe -m pytest tests\test_wave2_l2_api.py
    tests\test_wave2_l2_corpus_routing.py tests\test_wave2_l2_models.py
    tests\test_wave2_l2_personalized.py tests\test_wave2_l2_repository.py
    tests\test_wave2_l2_revision_loop.py
    tests\test_wave2_l2_repository_consume.py -q
```

Result: **79 passed** (71 pre-existing L2 wave2 tests + 8 new shared-repository
consumption/fallback tests), 0 failed.

New coverage details (`tests/test_wave2_l2_repository_consume.py`):

1. `test_revision_service_consumes_shared_repository` — revision dependency
   repository is the `app.state.wave2_repository` instance (identity).
2. `test_personalized_service_consumes_shared_repository` — same for the
   personalized dependency.
3. `test_both_routers_share_one_repository_instance` — one shared instance
   reaches both services.
4. `test_revision_created_task_visible_to_personalized_router` — F-1 e2e
   regression: default dependencies (no overrides), task created through the
   revision router is visible to the personalized router; priority-plan
   returns 200 with items; LearningItem creation returns 201.
5. `test_revision_falls_back_to_module_local_repository` — without
   `app.state.wave2_repository`, the revision dependency uses
   `_DEFAULT_REPOSITORY`.
6. `test_personalized_falls_back_to_module_local_repository` — same for the
   personalized dependency.
7. `test_standalone_flow_still_works_without_shared_store` — standalone
   (fallback) context keeps both routers functional (task 201, submission 201,
   scaffold 200).
8. `test_shared_absent_falls_back_for_both_dependencies` — fallback identity
   for both dependencies together.

### Focused regression

`tests/test_composition_root.py tests/test_router_retry.py`: **8 passed**
(composition root and router retry paths unaffected by the dependency change).

## Resource hygiene

- Pre-existing untracked evidence in the worktree (domain decisions,
  integration reports, census artifacts, the PDW2-C handoff JSON) preserved
  untouched — not staged, not committed, not deleted.
- Task-scoped pytest `--basetemp` directories used under `%TEMP%`; no test
  output written into the repository tree.
- No push, no PR, no merge, no promotion, no reset/clean/rebase.
- Commit limited to the four scoped files on `dept/l2-writing` with parent
  `b13155d23a3f416fd5a8d116f007120a15e9cf12`.

## Resulting commit

Final SHA recorded in the structured handoff (`final_sha`). Branch:
`dept/l2-writing`. No promotion authority was granted or exercised.
