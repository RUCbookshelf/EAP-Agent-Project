# v0.9.5-B Verification — API Router Decomposition and Health Contract Reconciliation

**Date:** 2026-08-02
**Result:** PASS
**Baseline:** `284378e` (v0.9.4-B implementation) + `c1e2bfc` (v0.9.4-B verification)
**Implementation commit:** `refactor(v0.9.5-b): split FastAPI feature routers` (see commit log)
**Verification commit:** `test(v0.9.5-b): verify router decomposition contracts` (see commit log)
**Specification:** `docs/development/V0.9.5_B_SPEC.md`
**Scope:** behavior-preserving API-layer refactor only. No UI, API client, schema, service, repository, database, migration, configuration, or domain change.

## 1. Router modules created (`app/api/routers/`)

`__init__.py`, `system.py`, `submissions.py`, `analysis.py`, `students.py`, `revisions.py`, `practice.py`, `journey.py`, `research.py`, `calf.py`, `admin.py` plus the shared API-only helper module `app/api/deps.py` (app-state accessors and the `require_student` guard).

## 2. Final responsibility of `app/api/main.py`

Composition root only: FastAPI application creation, lifespan wiring, middleware (request-ID, readiness gate), exception handlers, service construction, lifecycle/NLP fact population, and router inclusion. No feature route handlers remain; the former `_register_business_routes` (684 lines) was removed.

## 3. Route contract parity

Captured with `verification/v0.9.5-b/capture_route_inventory.py` (evidence: `route_inventory_before.json`, `route_inventory_after.json`).

| Metric | Before | After |
|---|---|---|
| Declared route rows (test/app-factory builder) | 78 (health duplicated) | 77 |
| Unique path+method pairs | 77 | 77 |
| Duplicate path+method pairs | 1 (GET `/api/v1/system/health` ×2) | 0 |
| Missing endpoints after change | — | 0 |
| Added endpoints after change | — | 0 |
| Route name changes | — | 0 |
| Response-model changes | — | 0 |
| Declared status-code changes | — | 0 |
| Handler function-name changes | — | 0 |
| OpenAPI operation-ID changes | — | 0 |
| Health handler resolved in test builder | `app.api.main.health` (business, index 4) | `app.api.routers.system.health` (index 6) |
| Health handler resolved in production builder | `app.api.main.health` (lifecycle, index 6; business copy appended at startup) | `app.api.routers.system.health` (index 6) |

Before the change, OpenAPI emitted `Duplicate Operation ID health_api_v1_system_health_get`; after the change the warning is gone.

## 4. Health handler before and after

- **Before:** two registrations — a business handler (live `repository.ping()` + live analyzer introspection) in `_register_business_routes`, and a lifecycle handler (`lifecycle.health_dict()`) in `_register_lifecycle_routes`. The test builder registered business-first (business semantics), the production builder lifecycle-first (lifecycle semantics): the same endpoint had different observable semantics per builder.
- **After:** exactly one canonical lifecycle-based handler in `routers/system.py`, included first by both builders. The duplicate business handler and the unreachable duplicate lifecycle-route block after `return` in `create_app` were removed.
- **Production/test health parity:** both builders resolve the same handler and both now populate the same lifecycle analyzer/NLP facts (shared `_apply_analyzer_lifecycle`). This also repaired the production lifecycle health reporting of `nlp_model_installed`/`nlp_model_version` (the old startup lookup used an `isinstance(..., dict)` guard that never matched `AnalyzerRegistry`).
- `/api/v1/system/live` and `/api/v1/system/ready` handlers are unchanged.

## 5. Focused API verification

| Layer | Result |
|---|---|
| Static (compileall app+tests+scripts; `git diff --check` on stage files; import/app-construction) | PASS |
| Route-contract tests (`tests/test_v095b_router_contract.py`, 10 tests: pinned 77-pair contract, no duplicates, one health registration in both builders, prod/test route-set match, health operation ID, healthy/unavailable health states, prod/test health JSON equality, request ID, live/ready behavior, readiness 503 gate) | 10 passed |
| Focused API set (system, submissions, analyses, students/learner, revisions, practice, journey, CALF, research, admin/configuration, request reliability/error envelopes, UI client/streamlit API integration, architecture invariants) | 274 passed, 3 skipped |
| Minimal runtime smoke (`verification/v0.9.5-b/runtime_smoke.py`, isolated temp DB, local provider, port 8011): live during startup, ready, health (ok/connected, migration 12), version (`config-v0.9.0`), submission write 201 + read 200, Practice read 200, Journey read 200, Research read 200, process kill → port freed → restart recovery → health ok, clean stop → port free, isolated DB essay count = 1 | PASS |

The runtime smoke clears `DATABASE_URL` and points `DATABASE_PATH` at a fresh temporary directory; the dev database (`data/writing_feedback.db`) was verified unchanged (17 essays before and after the smoke).

## 6. Full regression

- Core suite (`pytest tests --ignore=tests/live`): **431 passed, 8 skipped** (baseline v0.9.4-B: 421 passed, 8 skipped; the +10 are the new v0.9.5-B contract tests).
- Externally managed live browser tests (`tests/live/test_v09_playwright.py`, `test_v0921_playwright.py`) require an explicitly started stack and the pytest-playwright plugin; they are not part of the core gate and were not started for this API-only stage. The 20 in-process live-validation tests that need no external stack passed within the focused/core runs.
- Exact launcher verification, run once: `cmd /c "run.bat --verify"` → **PASS** (dependencies satisfied; NLP resource PASS — spaCy 3.8.7, `en_core_web_sm` 3.8.0; migration 12; 33 tables; `config-v0.9.0`; prompt `feedback-prompt-v0.7.1`; health 200, docs 200, Streamlit 200).

## 7. Unchanged contracts (confirmed by diff scope + tests)

Schemas (`app/api/schemas.py` untouched), services, repository protocols, `Database`, SQL/migrations (migration 12), table ownership, configuration behavior (`config-v0.9.0`), retry/timeout behavior, request IDs, error taxonomy, Diagnostic Gate, CALF, Practice, Revision, Journey, research-export behavior, authentication posture, Streamlit pages, UI components, design tokens, localization, and `app/ui/api_client.py`.

## 8. Deferred audit findings (unchanged, per v0.9.5-B non-goals)

Version constants reporting `0.8.0`; UI imports of backend schemas; 22 endpoints without client wrappers; `export_jobs` writer; WTR ID-allocation collision; duplicated repository protocols; `Database` god-class; Student/Research page monoliths; test-pyramid imbalance; sync-conflict files; legacy `FeedbackPipeline`.

## 9. Preserved user-owned files

`AGENTS.md`, `CLAUDE.md`, `.claude/`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`, `data/demo_journey_manifest.json` were not staged, modified, or committed by this stage.

## 10. Evidence artifacts

- `verification/v0.9.5-b/capture_route_inventory.py`
- `verification/v0.9.5-b/route_inventory_before.json`
- `verification/v0.9.5-b/route_inventory_after.json`
- `verification/v0.9.5-b/runtime_smoke.py`

## 11. Post-implementation graph review

Code Review Graph impact analysis was attempted on the API factory symbols; the local graph was built from a different machine's absolute paths (`A:\坚果云同步\...`), so its path resolver returns no matches in this checkout. A static bounded impact analysis was used instead: `create_app`/`app` are consumed only by uvicorn (`scripts/service_processes.py`, `run.bat`) and 11 test files via `from app.api.main import create_app`; `_register_business_routes`, `_register_lifecycle_routes`, and `_build_full_app` have no external callers. GitNexus `detect_changes` post-implementation review: LOW risk, no affected processes (it indexes the pre-existing user-owned doc changes; new router files are not yet indexed). The graph index was not modified.

**v0.9.5-B is complete. v0.9.5-C Frontend Feature Extraction may begin under a separate goal; it has not been started.**
