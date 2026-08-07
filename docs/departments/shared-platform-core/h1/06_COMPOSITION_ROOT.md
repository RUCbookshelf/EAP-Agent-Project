# 06 — Composition Root

## Before (pre-WU9)

pp/api/main.py had **two parallel composition paths** constructing the same service graph:

| Path | Entry | How services were built | How pi.state.* was assigned |
|------|-------|------------------------|-------------------------------|
| Production | _run_startup() (background thread via _lifespan) | Inline construction: Database, build_analyzer, build_submission_service, all services — **duplicated** | Inline: pi.state.settings = settings … pi.state.admin_reanalysis = ... — **duplicated** |
| Test/immediate | _build_full_app() (called by create_app(settings)) | Same inline construction — **duplicated** | Same inline assignment — **duplicated** |

Both paths contained ~60 lines of identical service-construction code and ~30 lines of identical state-assignment code.  Any new domain service (e.g., Academic writing) would need to be added to **both** blocks.

## After (WU9)

A single parameterized builder _build_services() owns the entire service graph:

`
_run_startup()                        _build_full_app()
       │                                     │
       ▼                                     ▼
  _build_services(settings,          _build_services(settings,
    repository=repo,                   repository=repo,
    submission_service=...)            submission_service=...)
       │                                     │
       └─────────── shared ──────────────────┘
                       │
                       ▼
              _apply_service_state(api, services)
                       │
                       ▼
              api.state.* (all services)
`

### New functions

| Function | Purpose |
|----------|---------|
| _build_services(settings, *, repository, submission_service) → dict | Single parameterized service-graph builder.  Creates repository, analyzer, all business services, sets lifecycle metadata, and returns a dict with every service reference. |
| _apply_service_state(api, services) → None | Assigns the service dict to pi.state.*.  Single point of truth for state assignment. |

### Changed functions

| Function | Change |
|----------|--------|
| _run_startup(api) | Stage 4 now calls _build_services(settings, repository=repository) instead of inline construction.  Stages 1–3 (settings, database, analyzer) remain separate for stage-by-stage lifecycle logging.  State assignment delegated to _apply_service_state. |
| _build_full_app(settings, *, repository, submission_service) | Now calls _build_services(...) and _apply_service_state(...) instead of inline construction.  Adds readiness gate middleware for production parity. |

### Unchanged

- create_app(settings=None) — public entry point, behavior identical.
- pp = create_app() — module-level ASGI application for uvicorn.
- _lifespan() — unchanged, spawns _run_startup in a daemon thread.
- pi.state.* reference names — all unchanged.
- _register_error_handlers, _register_request_middleware — unchanged.
- Facade private-attribute access (
epository._learner_repository, etc.) — preserved as-is (note: broad refactor out of scope for this WU).

## Single-builder contract

`python
def _build_services(
    settings: Settings,
    *,
    repository: Database | None = None,       # None → creates new Database
    submission_service: SubmissionService | None = None,  # None → builds new
) -> dict:
    """Returns:
        settings, repository, analyzer, submission_service,
        learner_profiles, metrics, configurations, dashboards,
        reanalysis, journey, revisions, calf, research
    """
`

- **Deterministic**: given the same settings, the builder produces the same service graph.
- **Idempotent repository**: 
epository.initialize() is called; it is safe to call on an already-initialized repository.
- **Lifecycle metadata**: lifecycle.database_status, lifecycle.migration_version, lifecycle.application_version, etc. are set inside the builder.
- **No corpus wiring**: Corpus Intelligence stays optional/additive.  The builder does not import or wire pp.corpus.*.

## How domains register later

The composition root is designed for **additive domain registration**:

1. A new domain (e.g., Academic Writing) defines its own services and router.
2. Its services are added to _build_services() as new dict keys.
3. Its router is added to _BUSINESS_ROUTERS.
4. Its pi.state.* assignments are added to _apply_service_state().
5. **No second root is needed.**  Both production and test paths automatically get the new domain.

## Corpus optional/additive

Corpus Intelligence modules (pp/corpus/**) are **not** wired by the composition root.  The app boots successfully without them.  Corpus features, when enabled, attach to the service graph as an additive layer outside _build_services.

## Test/runtime configuration

- **Test path**: create_app(settings) → _build_full_app() → _build_services() → _apply_service_state().  FastAPI instance created with readiness gate middleware.
- **Production path**: create_app() → lifespan → _run_startup() → stages 1–3 (settings, database, analyzer) → _build_services() → _apply_service_state().
- **Builder-identity test**: 	ests/test_composition_root.py asserts that _build_services is the single builder used by both paths (module symbol identity).

## Files modified

- pp/api/main.py — refactored to single composition root
- 	ests/test_composition_root.py — new test file for builder identity and boot tests
- docs/departments/shared-platform-core/h1/06_COMPOSITION_ROOT.md — this document
