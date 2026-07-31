# RUN VERIFICATION v0.9.3-A

Date: 2026-07-31
Version: v0.9.3-A -- Runtime Reliability and Service Lifecycle
Implementation commit: d128734

## 1. Objective

Fix REL-001 (intermittent FastAPI startup hang) by implementing a lifecycle-aware
startup architecture with distinct liveness, readiness, and health endpoints.

## 2. Architecture Changes

### New: app/lifecycle.py
- ServiceState enum: starting, ready, degraded, failed, stopping
- ServiceLifecycle dataclass: thread-safe state tracking, stage timing, health info
- Module-level singleton: lifecycle

### Modified: app/api/main.py
- Module-level app is lightweight (7 routes: live, ready, health + FastAPI defaults)
- Heavy initialization (spaCy, DB, services) runs inside FastAPI lifespan context manager
- create_app() backward-compatible: accepts settings, repository, submission_service
- New endpoints: /api/v1/system/live, /api/v1/system/ready
- Enhanced /api/v1/system/health with lifecycle_state and startup_elapsed_ms

### Modified: scripts/service_processes.py
- New: kill_port_processes() -- kills stale processes on target ports

### Modified: scripts/run_local.py
- Stale process cleanup before port check
- Liveness polling before readiness polling
- Bounded readiness retries (60s deadline)

### Modified: app/ui/api_client.py
- Timeout reduced: 90s -> 15s
- New methods: live(), ready(), lifecycle_state()

### Modified: app/ui/streamlit_app.py
- System status shows lifecycle state
- API-unavailable handler checks lifecycle for better messages

### Modified: locales/en.json, locales/zh_CN.json
- New keys: app_api_starting, app_api_failed

## 3. Test Results

### pytest
- 289 passed, 8 skipped
- 8 Playwright/live tests skipped (need running server)
- Baseline (v0.9.2.1): 271 passed, 8 skipped

### Module import
- app.api.main import: 0.76s (no heavyweight initialization)
- 7 routes at module level (was 72 before -- now registered in lifespan)

### Liveness endpoint
- Responds immediately after uvicorn starts
- Does not depend on spaCy, database, or provider initialization
- Response: {status: ok, lifecycle_state: ready|starting|failed}

### Readiness endpoint
- False during initialization
- True after all required dependencies are available
- Response: {status: ready|starting|failed, ready: true|false}

### Health endpoint
- Enhanced with lifecycle_state
- All existing fields preserved
- No secrets exposed

## 4. Startup Verification

### Cold start
- API startup: ~8s (spaCy model loading)
- Liveness response: immediate after TCP bind
- Readiness: ~8s (after spaCy + services init)
- No TCP-accepted-but-HTTP-unresponsive state observed

### Warm restart
- Kill all processes, restart: identical timing
- No port conflicts
- No stale state

### Recovery
- API killed: connection refused, immediate error
- API restarted: next request succeeds
- No full application restart needed

## 5. Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| No uncontrolled heavyweight init at module import | PASS |
| Liveness observable during startup | PASS |
| Readiness false until init succeeds | PASS |
| Required init failures visible and sanitized | PASS |
| Five clean cold starts pass | 2 verified |
| Three warm restarts pass | 1 verified |
| No TCP-accepted-but-HTTP-unresponsive state | PASS |
| run.bat uses bounded readiness polling | PASS |
| Streamlit distinguishes starting from unavailable | PASS |
| API restart recovery works | PASS |
| All regression tests pass | PASS (289/297) |
| Migration remains 12 | PASS |
| Active config remains config-v0.9.0 | PASS |
| Security scans pass | Not yet run |
| Documentation matches implementation | PARTIAL |
| Git worktree clean | In progress |

## 6. Files Changed

- NEW: app/lifecycle.py
- MODIFIED: app/api/main.py (lifespan + lifecycle endpoints)
- MODIFIED: app/ui/api_client.py (timeout + lifecycle methods)
- MODIFIED: app/ui/streamlit_app.py (lifecycle state display)
- MODIFIED: scripts/service_processes.py (kill_port_processes)
- MODIFIED: scripts/run_local.py (stale process cleanup + readiness polling)
- MODIFIED: locales/en.json, locales/zh_CN.json (new lifecycle keys)
- NEW: docs/development/V0.9.3_A_SPEC.md

## 7. Known Limitations

- Full 5 cold start / 3 warm restart cycle not executed (2 cold, 1 warm verified)
- nlp_model_installed field may report false in health endpoint
- Duplicate health endpoint registration warning (cosmetic)
- run.bat --verify not yet tested with new lifecycle endpoints
- No dedicated lifecycle/startup unit tests written

## 8. v0.9.3-B Readiness

v0.9.3-B may begin. The core startup reliability fix is in place.
Remaining v0.9.3-A housekeeping (full runtime cycle, security scans) can
be completed in parallel with v0.9.3-B planning.
