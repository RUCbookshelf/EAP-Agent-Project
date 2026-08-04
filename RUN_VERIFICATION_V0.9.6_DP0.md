# v0.9.6-DP0 Run Verification - Production Provider Reliability

**Status:** COMPLETE - DeepSeek structured feedback stabilized and verified
**Branch / HEAD:** master / `3ee3d1f` (before the test-verification commit)
**Date:** 2026-08-04

## Diagnosis commits and evidence (DP0-A)

```text
eec7197 docs(v0.9.6-dp0a): diagnose DeepSeek structured-output failures
verification/v0.9.6-dp0/GATE1_DIAGNOSIS_REPORT.md
verification/v0.9.6-dp0/root_cause_classification.json
```

Root cause: thinking mode defaults to enabled on `deepseek-v4-pro`; the
request omitted the toggle; reasoning consumed 72% of the 1800-token budget;
JSON truncated (`finish_reason=length`); correction attempt timed out at 30s.

## Approved repair (owner Gate-1 acceptance)

```text
ac6a569 fix(v0.9.6-dp0): stabilize DeepSeek structured feedback
3ee3d1f fix(v0.9.6-dp0): include response id in provider call logs
```

Changes: `thinking={"type":"disabled"}` in the DeepSeek structured-feedback
payload; sanitized metadata capture (response id, returned model, finish
reason, token usage, content length, duration, parse/validation status);
`finish_reason=length` classified as `provider_output_truncated`; malformed
JSON classified as `provider_json_invalid`. Timeout kept at 30s per owner
decision; model, prompt, schema, gate, max tokens, correction/fallback
policy, and the 180s client timeout unchanged.

## Live verification (exact conditions)

```text
Fresh isolated database: C:\tmp\v096dp0\live.db
Normal startup: venv python -m uvicorn app.api.main:app --port 8001
Env: DATABASE_URL, API_PORT=8001, API_BASE_URL=http://127.0.0.1:8001,
     WRITING_FEEDBACK_ENV_FILE=<repo>/.env
Submissions: POST /api/v1/submissions via verification/v0.9.6-dp0/live_driver.py
```

```text
D0-01 -> submission 1: success, stop, 813/1800 tokens, 15.5s, 0 correction, 0 fallback
D0-02 -> submission 2: success, stop, 995/1800 tokens, 21.8s, 0 correction, 0 fallback
D0-05 -> submission 3: success, stop, 201/1800 tokens, 4.5s, 0 correction, 0 fallback
D0-01 -> submission 4: success, stop, 850/1800 tokens, 13.2s, 0 correction, 0 fallback (response id logged)
```

## Focused and regression verification (exact commands and results)

```text
pytest -q -p no:cacheprovider (DP0-B focused + provider/config/gate/validation suites)
  -> 101 passed, exit 0
pytest -q -p no:cacheprovider (submission-service, v0.9.6-A/B reliability, API contracts)
  -> 103 passed, exit 0
pytest -q -p no:cacheprovider (provider suites after response-id fix)
  -> 24 passed, exit 0
pytest -q -p no:cacheprovider --ignore=tests/live tests   (full non-live core, exactly once)
  -> 821 passed, 8 skipped, 2 failed, 1 error, exit 1
     failure 1: parity contract test - runner omitted the documented
       SERVICE_API_DIFF_ALLOWLIST env; passes with it (4 passed)
     failure 2: test_v095b_router_contract lifecycle-race flake (documented
       pre-existing); passes in isolation
     error 1:   sidebar browser test transient chromium launch timeout;
       passes in isolation
     full core was not automatically rerun per protocol
cmd /c "run.bat --verify"   (isolated DATABASE_URL)
  -> PASS, exit 0
```

## Safety results

```text
Development database: unchanged (62615C6C..., 14,352,384 B, mtime 12:54:07)
Research exports: 776 files / 388 dirs (16 test-generated files removed via exact allowlist)
Provider budget: 6 of 12 attempts used; 0 corrections; 0 fallbacks
Isolated DBs: tests.db, live.db, core.db, launcher.db (all under C:\tmp\v096dp0)
D0 workspace C:\tmp\v096d0 preserved
```

## Final state

```text
Active model: deepseek-v4-pro | Prompt: feedback-prompt-v0.7.1
Configuration: config-v0.9.0 (unchanged) | Migration: 12 | Tables: 33
API pairs: 77 | Database public methods: 2 | Client methods: 53 | Locale: 540/540
```

Provider reliability acceptance: **met** (3+ consecutive initial-attempt
live successes with zero corrections, zero fallback, zero truncation, zero
timeout). Recommended next stage: **v0.9.6-D0-R** (resume the frozen priority
path audit).


## v0.9.6-DP0-V1 closure (2026-08-04)

The original DP0 full-core run was NOT accepted for formal closure:

`	ext
821 passed, 8 skipped, 2 failed, 1 error, exit 1
- tests/test_v095e_repository_modularization.py::test_static_owner_sql_dependency_and_ddl_parity_contract
  (runner omitted the documented SERVICE_API_DIFF_ALLOWLIST env; passes with it)
- tests/test_v095b_router_contract.py::test_business_route_gated_until_ready_while_health_available
  (documented pre-existing lifecycle flake; passes in isolation)
- tests/test_v096c2_sidebar_control.py::test_browser_expanded_normal_left_visible_without_hover
  (transient Chromium launch timeout; passes in isolation)
`

Canonical full-core environment (source authority:
verification/v0.9.5-h2a/isolated_pytest_runner.py):

`	ext
PYTHONUTF8=1, PYTHON_DOTENV_DISABLED=1, LLM_PROVIDER=local,
DATABASE_PATH=<fresh isolated db>, SERVICE_API_DIFF_ALLOWLIST=<26-entry
G_ALLOWLIST copied verbatim from the runner>, DATABASE_URL absent
pytest -q -p no:cacheprovider --ignore=tests/live tests
`

Readiness (all pass, run once each): parity test 1 passed; router lifecycle
isolated 1 passed; router contract module 10 passed; Chromium launch probe
PASS; prior Chromium test 1 passed; C2 module 18 passed; combined targeted
readiness 101 passed, exit 0.

Final full non-live core (exactly once):

`	ext
824 passed, 8 skipped, 0 failed, 0 errors, exit 0 (566.22s)
`

Launcher (exactly once with the isolated-DB contract
DATABASE_URL=sqlite:///C:/tmp/v096dp0/v1-launcher.db):

`	ext
cmd /c "run.bat --verify" -> PASS, exit 0; health/docs/streamlit 200/200/200
`

Safety: research exports 776 files / 388 dirs (16 test-generated files
removed via exact allowlist); development database logically unchanged -
see dev_db_incident.json for the recorded byte-fingerprint incident during an
invalid first launcher attempt (operator env error; read-only verification
proved zero logical change; corrected launcher run used the isolated DB and
the fingerprint is stable).

DP0-V1 closure status: **COMPLETE and fully verified**.
