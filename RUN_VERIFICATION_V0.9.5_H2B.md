# v0.9.5-H2B Verification - Rename Active Configuration Repository Contract

**Status:** IMPLEMENTATION COMPLETE; focused and launcher verification PASS; **full-core regression NOT CLEAN - final verification closure PENDING**

## Scope

Naming-only rename of the active local configuration contract `ConfigurationRepository` -> `ConfigurationPort` (consumer-owned configuration boundary used by `ConfigurationService`). No method, signature, return annotation, implementation, repository, SQL, transaction, migration, API, UI, behavior, or runtime dependency changed; no compatibility alias or duplicate name introduced; the old name is absent from active source.

## Baseline and commits

| Item | Value |
| --- | --- |
| Baseline HEAD | `8a01f5b` (H2A full verification closure) |
| Implementation commit | `refactor(v0.9.5-h2b): rename configuration contract` |
| Verification commit | `test(v0.9.5-h2b): verify configuration contract rename` |

## Rename rationale

`ConfigurationPort` matches the established consumer-owned Port naming convention (`CalfDataPort`, `CalfSubmissionReadPort`, `AdminConfigurationReadPort`, `ActiveConfigurationPort`, `PracticeReadPort`) and the v0.9.5-F1 audit's own proposed name. It communicates a service-facing configuration boundary rather than a database repository layer or CRUD aggregate, and removes the last ambiguity with repository-layer naming after H2A deleted the stale central `ConfigurationRepository`.

## Changes

- `app/services/configuration.py`: `class ConfigurationRepository` -> `class ConfigurationPort`; `ConfigurationService.__init__(repository: ConfigurationPort, ...)` (2-line naming-only diff).
- `tests/test_v095h2a_removed_contracts.py`: H1-inventory rename map (`ConfigurationRepository` -> `ConfigurationPort`) so the 42-active-contract preservation test stays valid; local-contract test renamed and asserts the old name is absent.
- `tests/test_v095h2b_configuration_contract_rename.py` (new, 6 tests): old name absent from production source; new contract with exactly the seven methods; constructor annotation against the new contract only; no duplicate name/alias; concrete `SQLiteConfigurationRepository` satisfies the renamed contract (method + parameter parity); create/validate/activate runtime flow unchanged on an isolated database.
- `verification/v0.9.5-h2a/isolated_pytest_runner.py`: added `app/services/configuration.py` to the `SERVICE_API_DIFF_ALLOWLIST` (E-parity contract mechanism; the H2B-touched file is authorized, mirroring the G-era allowlist pattern).

## Method preservation (unchanged, in order)

`list_configurations`, `get_configuration`, `get_active_configuration`, `create_configuration`, `set_configuration_validation`, `activate_configuration`, `list_configuration_audit` - verified by test (`EXPECTED_METHODS`) and by parameter-name parity against `SQLiteConfigurationRepository`.

## Verification

### Layer 1 - Static

- `py_compile` of changed modules: PASS; package imports (`app.services.configuration`, `app.services.factory`, `app.services`, `app.api.main`, `app.repositories`, `app.feedback.service`) PASS (no circular import).
- Old-name scan: `\bConfigurationRepository\b` absent from every `app/**/*.py`.

### Layer 2 - Contract preservation (focused suite, isolated DB)

- Command: `.venv\Scripts\python.exe verification/v0.9.5-h2a/isolated_pytest_runner.py --targets <F2-F6D+G+H2A+H2B files>`.
- Result: **203 passed, 2 warnings** (197 H2A-V1 focused baseline + 6 new H2B tests).
- All 42 active persistence contracts remain defined with exact method sets; `SQLiteConfigurationRepository` still satisfies the renamed contract; `ConfigurationService` create/validate/activate flows pass.

### Layer 3 - Runtime (isolated databases, local provider)

- Application construction (both `create_app` paths) and `ConfigurationService` construction with the renamed contract: PASS (covered by the focused suite and the H2B runtime test: list, active, create, validate, activate, audit).

### Full non-live core regression - NOT CLEAN (2 runs)

- Command (each run): `.venv\Scripts\python.exe verification/v0.9.5-h2a/isolated_pytest_runner.py --full` (`pytest -q -p no:cacheprovider --ignore=tests/live tests`), fresh unique isolated database per run.
- Run 1: **exit code 1**; `1 failed, 668 passed, 8 skipped, 2 warnings in 311.23s`; failure `tests/test_v095b_router_contract.py::test_live_and_ready_unchanged` (lifecycle_state `ready` instead of `starting`).
- Run 2 (fresh, after classification): **exit code 1**; `1 failed, 668 passed, 8 skipped, 2 warnings in 309.09s`; failure `tests/test_v095b_router_contract.py::test_business_route_gated_until_ready_while_health_available` (identical traceback to the pre-H2B H2A full-core failure).
- Both failures are instances of the documented pre-existing lifecycle-race flake in `test_v095b_router_contract.py` (prod-mode TestClient + background startup thread mutating the global lifecycle singleton inside large sets; recorded in `RUN_VERIFICATION_V0.9.5_G.md`). Both pass in isolation (`test_live_and_ready_unchanged` 2.12s; the gated-route test 0.52s in the H2A stage). The failures are unrelated to the H2B rename (identical failure occurred before H2B changed anything).
- Per the v0.9.5-H2A-V1 full-core closure standard, an isolated pass is not a substitute for a clean exit-0 full-core run, and no automatic reruns are performed after failures. A clean full-core run has not been established for H2B; final verification closure is PENDING.

### Launcher verification (separate fresh isolated database)

- Exact command: `cmd /c "run.bat --verify"` -> **PASS (exit 0)**; migration 12; tables 33; `config-v0.9.0`; `feedback-prompt-v0.7.1`; FastAPI health 200; docs 200; Streamlit 200; `llm_provider=local`.

## Frozen contracts (unchanged)

Database public methods 2; API 77; frontend client 52; locale 520/520; migration 12; tables 33; configuration `config-v0.9.0`; feedback prompt `feedback-prompt-v0.7.1`; total persistence contracts 42 (active 42, unused 0).

## Database isolation

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-vis6ddbc\h2a.db` (fresh temp dir, resolved and asserted).
- Full-core run 1 DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-0zbqb234\h2a.db`; run 2 DB: `C:\Users\16073\AppData\Local\Temp\v095h2a-soqpph9l\h2a.db` (both fresh).
- Launcher DB: `C:\Users\16073\AppData\Local\Temp\v095h2b-verify-6c387098\verify.db` (fresh).
- Development database before/after every write-capable run: SHA-256 `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size 8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` - unchanged; never opened.
- Ports 8000/8501 free before and after; all temporary databases and processes removed; `research_exports/` untouched; no live provider.

## Conclusion

`v0.9.5-H2B is incomplete; verification pending.` (Implementation, focused contract suite, and launcher verification are complete and passing; the full-core clean exit-0 run is not yet established because the documented pre-existing `test_v095b_router_contract` lifecycle-race flake failed once in each of the two full-core attempts, with both instances passing in isolation. H2B did not cause these failures.)
