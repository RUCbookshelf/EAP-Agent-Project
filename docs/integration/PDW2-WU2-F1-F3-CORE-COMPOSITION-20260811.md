# Wave-2 F-1/F-2/F-3 CORE composition repair - PDW2-WU2-F1-F3-CORE-COMPOSITION

- Goal: `PDW2-WU2-F1-F3-CORE-COMPOSITION` (REPAIR, owner CORE)
- Worktree: `A:\EAP Agent Project\worktrees\shared-core` (branch `dept/shared-core`)
- Starting SHA (parent): `3204b6afda3320d4c09e395994cdc9d0671f29cd`
- Final SHA: `04ad8dec905d43587746087674ec09d485c56b5d`
- Verdict: **GREEN** (CORE repair scope; INT re-gate required for promotion eligibility)
- Returned: 2026-08-11

## Scope executed

Repair of the three CORE findings from the WU2 INT gate
(`PDW2-WU2-INT-INTEGRATION-GATE__20260810T162500Z__df3a05`, AMBER):

### F-1 - shared wave2 repository composition

`app/api/routers/wave2.py` now composes ONE shared `SQLiteWave2Repository`
over the composition-root Database and exposes it at
`app.state.wave2_repository`:

- `build_wave2_repository(database)` composes `SQLiteWave2Repository` over
  the Database's own connection manager (one SQLite file for the whole
  application; migration-14 table families live beside every other table
  family).
- `get_wave2_repository(request)` is a FastAPI dependency that resolves the
  shared store, composing and caching it on `app.state.wave2_repository` on
  first use (HTTP 503 if the composition-root Database is unavailable).
- Every mounted wave2 sub-router (learner/revision/personalized) now carries
  `dependencies=[Depends(get_wave2_repository)]`, so all wave2 routers
  resolve the same store through the real composed app. L2/LEARNER router
  defaults consuming `app.state.wave2_repository` remain their own repair
  follow-ups (gate F-1 note: "CORE composes; L2/LEARNER consume").

Additive only: `app/infrastructure/sqlite/repositories/wave2.py` needed no
composition helper (the Database's connection manager is the single shared
resource); no `migrations.py`/`app/api/main.py` changes.

New composition tests `tests/test_wave2_repository_composition.py`:

- composed store reuses the app Database's connection manager and persists
  through the migration-14 tables of the same database file;
- `get_wave2_repository` exposes exactly ONE instance on `app.state` across
  repeated resolution;
- a task saved through the store is visible across the revision /
  personalized / learner router families (shared store);
- HTTP 503 without the composition-root Database;
- a pre-populated `app.state.wave2_repository` is served as-is.

### F-2 - assembly-test refresh (integration-aware)

`tests/test_wave2_router_assembly.py` was refreshed:

- stale empty-mount assertions removed (empty mount is an implementation
  detail of the branch without sub-routers, not a contract);
- the test now pins the intended Wave-2 route surface: 18 unique paths /
  19 (method, path) pairs, enumerated from the real learner/revision/
  personalized sub-routers on the merged composition;
- fakes mirror the real route tables; the full-app test asserts the 18 real
  paths mount through `create_app`;
- a conditional test executes on trees where the real sub-router modules
  exist (merged composition) and asserts the product mounts exactly the
  intended surface; it is skipped on branches without the modules.

### F-3 - v095b pinned route-contract refresh

`tests/test_v095b_router_contract.py::EXPECTED_ROUTE_CONTRACT` now includes
the full merged Wave-2 surface (19 new (method, path) pairs: 11 GET, 7 POST,
1 PATCH). The packet's "9 new wave2 routes" is imprecise: direct enumeration
of the real merged app shows 19 (method, path) pairs over 18 unique paths
(revision 7, personalized 5, learner 7), which is what the exact-equality
pin requires.

## Verification evidence

### CORE worktree (`dept/shared-core` @ working tree, branch-local `.venv`)

`pytest tests/test_wave2_migration_v14.py tests/test_wave2_repositories_v14.py
tests/test_wave2_router_assembly.py tests/test_wave2_repository_composition.py
tests/shared/test_version_single_sourcing.py
tests/test_shared_core_drift.py::TestModuleSetManifest::test_manifest_exists_and_parses`
-> **32 passed, 1 skipped** (the real-modules test skips because the
sub-routers are contributed by LEARNER/L2 branches, not this one).

`tests/test_v095b_router_contract.py` in this worktree: 9 passed, 1 failed
(`test_route_contract_pinned`). This is expected and pre-existing in kind:
the pinned contract now includes the Wave-2 routes that exist only in the
merged composition; the pin is verified GREEN there (below). This is the
same verification boundary as `TestModuleSetManifest`, whose frozen manifest
is the union module set (244 modules) and can only match where the union
tree exists.

### Merged composition preview (read-only union of the five WU2 candidates
in TEMP, `uv sync --frozen`, same package versions as the gate)

| Suite | Result |
| --- | --- |
| tests/wave2 (UX) + CORE wave2 (migration-14, repositories, assembly, composition) + L2 wave2 (api, corpus routing, models, personalized, repository, revision loop) + LEARNER wave2 (learner api, longitudinal, models, repository, synthetic learner) | **256 passed** |
| tests/test_v095b_router_contract.py (full file incl. pinned route contract with the 19 wave2 pairs) | PASS |
| tests/shared/test_version_single_sourcing.py | PASS |
| tests/test_shared_core_drift.py::TestModuleSetManifest (union 244 modules) | PASS (2/2) |
| tests/test_migrations_v02.py | PASS |
| tests/corpus | **133 passed** |
| Focused regression (writing_intelligence_slice, task_type_classifier, revision_v05, learner_model_v07, composition_root, journey UI) | **100 passed** |
| tests/test_environment_drift.py | 9 passed, 1 failed - only the documented baseline false positives (B-2: test_seccl.py:317, test_seccl_artifacts.py:81) plus the CORPUS-owned new instance (F-4: test_routing.py:422); no new failure from this repair |

### F-1 real-path wiring (merged preview, real composed app)

- `POST /api/v1/wave2/revision/tasks` through the composed app: 201; after
  the request `app.state.wave2_repository` is populated with a single
  `SQLiteWave2Repository` over `app.state.repository._connection_manager`
  (same instance on repeated resolution) - the shared store contract.
- The INT gate's e2e script rerun on the preview: assembly mount 18/18
  PASS; create task / V1 / V2 / observation / reanalysis / scaffold PASS;
  priority-plan still 404 `Writing task not found: WT000001` because L2's
  `personalized_api` default still uses its branch-local in-memory
  repository (LearningItem unreachable with it). That remaining gap is the
  L2/LEARNER consumption half of F-1, dispatched to their repair lanes;
  CORE's composition half is complete and verified.

## Git evidence

- Commit: `04ad8dec905d43587746087674ec09d485c56b5d` on `dept/shared-core`, parent
  `3204b6afda3320d4c09e395994cdc9d0671f29cd`.
- Committed files (exactly): `app/api/routers/wave2.py`,
  `tests/test_wave2_router_assembly.py`,
  `tests/test_v095b_router_contract.py`,
  `tests/test_wave2_repository_composition.py`,
  `docs/integration/PDW2-WU2-F1-F3-CORE-COMPOSITION-20260811.md`.
- Pre-existing untracked evidence preserved byte-identically (ADR and
  integration docs under `docs/architecture/` and `docs/integration/`).
- No `migrations.py`/`app/api/main.py` changes; no reset/clean/rebase/
  force update/push/PR/promotion; no writes outside the authorized worktree
  (TEMP union preview only, read-only wrt the repository).

## Dependencies

- Unlocked for the WU2 INT re-gate: shared wave2 store composition (CORE
  half of F-1), integration-aware assembly test (F-2), refreshed route pin
  (F-3).
- Remaining: L2/LEARNER F-1 consumption (router defaults reading
  `app.state.wave2_repository`), CORPUS F-4 drift-guard instance,
  baseline repairs tracked by INT (B-1 census, B-2 corpus path-literal
  guard), then the WU2 INT re-gate on the merged composition; promotion is
  a separate authorized action.
