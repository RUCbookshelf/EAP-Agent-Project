# L2 Pin Refresh — Writing Intelligence Slice Route (PDW1)

Goal: `PDW1-WRITING-INTELLIGENCE-SLICE__PINS-REFRESH`
Run: `PDW1-WRITING-INTELLIGENCE-SLICE__PINS-REFRESH__20260809T183520Z__5181d2`
Date: 2026-08-10
Worktree: `A:\EAP Agent Project\worktrees\l2-writing`
Branch: `dept/l2-writing`
Starting SHA: `f5b433f7a70049e35492580c00f38cf33a24d9c8`

## Scope

Mechanical refresh of the six frozen API-surface pin files so they record
`POST /api/v1/writing-intelligence/slice` exactly as the live app renders it on
this candidate branch, following the v0.9.7-b pin-refresh precedent (commits
`089419c`/`5abab20`). No product code, `app/api/main.py`, the slice router, or
the slice tests were touched.

## Files changed (commit scope: exactly these six)

1. `tests/contracts/api_surface_contract.py` — added
   `('POST', '/api/v1/writing-intelligence/slice')` classified `C` (unwrapped:
   no UI client wrapper, no feature consumer) plus its documented
   `ENDPOINT_UNWRAPPED_REASON` entry. Hand-sync of the generated pin, matching
   the v0.9.7-b precedent (the repo's `build_contract.py` inputs — the tracked
   `api_surface_before.json`/capture — are stale relative to the hand-maintained
   contract; a regeneration fidelity check against the committed contract
   confirmed the builder cannot reproduce the committed file, so the
   precedent-style minimal sync was used).
2. `tests/test_v095b_router_contract.py` — added the slice route to
   `EXPECTED_ROUTE_CONTRACT` (1 line, mirroring precedent `5abab20`).
3. `tests/test_v095d_api_contract.py` — endpoint-set count `80 -> 81` (assertion
   and docstring).
4. `tests/test_v095h2d2_api_dependency_bindings.py` — GET/POST route count
   `80 -> 81`.
5. `verification/v0.9.5-h2d2/dependency_graph_before.json` — regenerated from
   the live app with the exact extraction logic of
   `test_v095h2d2_api_dependency_bindings.py`: `route_count 84 -> 85`; one route
   added (`POST /api/v1/writing-intelligence/slice`,
   `run_writing_intelligence_slice`); one `Depends` call added
   (`writing_intelligence.py:899`, `get_analyzer`, `use_cache: null`);
   `depends_calls 115 -> 116`; pre-existing entry order preserved.
6. `verification/v0.9.5-h2d2/openapi_before.json` — `normalized_openapi`
   regenerated from `api.openapi()` on the live app: one path added
   (`/api/v1/writing-intelligence/slice`) with the 15 slice request/response
   schemas added to `components/schemas`; no paths or schemas removed. Two
   pre-existing schema defaults refreshed to the live value:
   `TaskCluster`/`VersionResponse` `task_cluster_version` default
   `task-cluster-v0.7.0 -> v0.8.0` (Domain Pack v1 taxonomy version, promoted
   before this candidate; unrelated to the slice but recorded as the live app
   renders it).

## Verification (post-refresh)

All runs used the worktree-local `.venv` via `uv run` (pyproject.toml ->
uv.lock -> worktree-local `.venv` environment contract).

| Module | Result |
| --- | --- |
| `tests/test_v095b_router_contract.py` | 10 passed |
| `tests/test_v095d_api_contract.py` | 9 passed |
| `tests/test_v095h2d2_api_dependency_bindings.py` | 13 passed |
| `tests/contracts/api_surface_contract.py` | data module (no test functions); import check: 81 endpoints, slice classified `C` with reason |
| `tests/test_writing_intelligence_slice.py` | 6 passed (stays green) |
| Combined run (all of the above) | 38 passed |

Baseline (pre-refresh) failures were exactly the three stale pin assertions:
`test_route_contract_pinned`, `test_endpoint_set_matches_runtime_and_is_fully_classified`
(81 != 80), and `TestFastAPIParity::test_openapi_and_dependency_graph_unchanged`.

## Commit

- Parent: `f5b433f7a70049e35492580c00f38cf33a24d9c8` (unchanged)
- Commit scope: ONLY the six pin files above
- Resulting SHA: recorded in the handoff
- No rebase/amend/force, no push/PR, no promotion
- Pre-existing untracked evidence (docs/domain/*, docs/integration/*,
  docs/domain/census/) preserved untouched
