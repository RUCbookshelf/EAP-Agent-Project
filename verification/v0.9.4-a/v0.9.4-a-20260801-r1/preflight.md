# v0.9.4-A Preflight Manifest

Run ID: `v0.9.4-a-20260801-r1`
Date: 2026-08-01

## Baseline (Phase 0 record)

| Item | Value |
|---|---|
| Branch | master |
| HEAD | 8d5583d (test v0.9.3 complete product hardening verification) |
| Required commits | b8f1e95, 31a7fde, 8d5583d — all ancestors of HEAD (verified) |
| Python | 3.11.15 (`.venv`) |
| Streamlit | 1.60.0 |
| Migration | 12 (schema_migrations max; run.bat reports migration_version 12) |
| Active configuration | config-v0.9.0 (status=active, activated 2026-07-30T22:00:00+00:00) |
| UI entrypoint | `streamlit_app.py` → `app/ui/streamlit_app.py:run()` |
| FastAPI entrypoint | `app.api.main:app` (uvicorn, ports 8000/8501 defaults) |
| `run.bat --verify` | PASS (health 200, docs 200, streamlit 200) |
| `/api/v1/system/live` | 200, status ok, lifecycle ready |
| `/api/v1/system/ready` | 200, ready=true |
| `/api/v1/system/health` | 200, status ok, migration 12, provider local (override) |

## Processes / ports

- No application Python/Streamlit/Uvicorn processes; no listeners on
  8000/8001/8501/8502/8080/5000.
- Running infrastructure processes (not application-owned): Code Review
  Graph `serve` (multiple) and GitNexus MCP node servers — left untouched.

## Preserved user-owned / pre-existing changes (never staged or modified)

- `AGENTS.md` (modified — project rules, user-owned)
- `RUN_VERIFICATION_V0.7.md` (modified — pre-existing)
- `.claude/` (untracked)
- `CLAUDE.md` (untracked)
- `data/demo_journey_manifest.json` (untracked — demo manifest; not part of
  v0.9.4-A)

## Provider / data safety

- `.env` configures `LLM_PROVIDER=deepseek` + key. All ordinary verification
  runs in this stage override `LLM_PROVIDER=local`; `run.bat --verify` is
  executed as the exact acceptance command and performs no provider call
  (health/startup checks only).
- Browser verification uses the deterministic synthetic demo learner
  (DEMO-001) and/or an isolated database copy; no real learner data is
  modified.

## Verification artifact scope

All logs, screenshots, manifests, and temporary artifacts are scoped under
`verification/v0.9.4-a/v0.9.4-a-20260801-r1/`.
