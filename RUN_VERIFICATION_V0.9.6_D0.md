# v0.9.6-D0 Run Verification - Priority Path Production Validity Audit

**Status:** audit stopped at the preregistered preflight blocker; no
production code changed; no corpus execution
**Branch / HEAD:** master / `8896828`
**Date:** 2026-08-04

## Baseline (Phase 0)

```text
HEAD:            8896828 test(v0.9.6-c): close no-priority and sidebar repairs
Active config:   config-v0.9.0 (CFG000007)
Active prompt:   feedback-prompt-v0.7.1
Migration:       12
Provider:        deepseek / deepseek-v4-pro (credentials configured)
Analyzer:        spacy-analyzer-v0.8.0 (en_core_web_sm 3.8.0), no analyzer fallback
Dev DB:          FA2DE352AACED75325B4DE49E5276A1A7FD58C881F54614C104B131CF0CE6FC5, 14,151,680 B
Research exports: 776 files / 388 directories
API (8000) / Streamlit (8501): running dev instances, untouched
```

## Protocol and corpus freeze (Phases 1-2)

- `audit_protocol.json` preregistered before any live submission.
- Five newly authored essays frozen (four issue-targeted, one control),
  each SHA-256-hashed; raw text only in the local synthetic fixture.

## Preflight execution (Phase 3) - exact commands

The audit API was started with production code and a fresh isolated
database:

```text
venv python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001
env: DATABASE_URL=sqlite:///C:/tmp/v096d0/audit.db
env: API_PORT=8001, STREAMLIT_PORT=8502, API_BASE_URL=http://127.0.0.1:8001
env: WRITING_FEEDBACK_ENV_FILE=<repo>/.env
```

Readiness verified: `GET /api/v1/system/ready` ready=true; health showed
deepseek configured, config-v0.9.0, prompt v0.7.1, migration 12.

Submissions (audit driver, public API only):

```text
POST /api/v1/submissions  D0-01 / AUDIT-D0-01    -> 201, fallback_success   (preflight)
POST /api/v1/submissions  D0-01 / AUDIT-D0-01P2  -> 201, fallback_success   (single permitted recovery)
```

Both provider calls failed identically: attempt 0 truncated JSON
(`response_validation_failed`), attempt 1 `TimeoutError` at the frozen 30 s
timeout; both fell back to LocalDemo.

## Stop decision

Stop condition hit: "the real provider fails the bounded preflight".
Corpus, repeatability, downstream, and controlled-comparison phases were
not run, because production validity cannot be assessed on fallback
evidence.

## Targeted verification (section 19) - exact command and result

```text
venv python -m pytest -q -p no:cacheprovider
  tests/test_v06_configuration_dashboard.py
  tests/test_v095h2d1_configuration_port_protocol.py
  tests/test_providers.py
  tests/test_router_retry.py
  tests/test_diagnostic_calibration_v061.py
  tests/test_diagnosis.py
  tests/test_feedback_validation.py
  tests/test_feedback_schema.py
  tests/test_revision_v05.py
  tests/test_practice_v09.py
  tests/test_v096c1_no_priority_workflow.py

155 passed, 2 warnings, 0 failed, 0 errors, exit 0
```

The full non-live core suite and the launcher were intentionally not run
(no production code changed; not required for D0 closure).

## Safety results

```text
Development database: unchanged (hash/size/mtime identical after every layer)
Research exports:     776 files / 388 dirs, zero delta (missing=0 changed=0 added=0)
Production source:    no changes under app/ or migrations/; tests/contracts/ untouched
Audit DB:             C:\tmp\v096d0\audit.db (2 synthetic submissions; outside repo; not committed)
```

## Primary classification

```text
v0.9.6-D0 is COMPLETE.

Production priority path classification: D0-E.
Production-provider reliability must be repaired before priority-path
validation can continue.
```

Recommended next stage: **v0.9.6-DP0 - Production Provider Reliability**
(separately approved; investigate the evidence chain first; do not lower
thresholds automatically; do not begin v0.9.6-D1).

## Audit commit

Exactly one commit:

```text
docs(v0.9.6-d0): audit production priority path validity
```

Contains only audit protocol, corpus metadata/fixture, driver, redacted
verification artifacts, audit documentation, and minimal project-state
documentation updates.
