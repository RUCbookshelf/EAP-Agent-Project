# v0.6 run verification — 2026-07-29

## Post-release DeepSeek and timed-writing repair

- Reproduced the reported LocalDemo result and confirmed from the persisted audit that DeepSeek had been called twice before `fallback_success`.
- Root cause: incomplete JSON under the 1,800-token first-call budget, followed by a contradictory correction instruction that prevented repair of non-verbatim evidence quotations.
- The one permitted correction request now receives a 3,600-token budget (capped at 8,192), actionable field-only validation details, and an explicit exact-substring quotation instruction.
- A real isolated submission returned provider `deepseek`, model `deepseek-v4-flash`, status `success`, validation `passed`, retry count 1, and no fallback. The API key was neither printed nor persisted.
- Streamlit now keeps `Time limit (minutes)` editable and persists a tested value of 45 when timed writing is selected.
- Regression result after the repair: `152 passed, 1 skipped`; `run.bat --verify` returned FastAPI health 200, docs 200, and Streamlit 200.

## Result

PASS. v0.6 provides API-sourced progress/revision views, versioned non-sensitive configuration and append-only scoped
reanalysis. This is an engineering acceptance result, not educational validation or a proficiency/CALF judgment.

## Commands actually executed

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate_database
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m pytest -q tests\test_v06_configuration_dashboard.py
.\.venv\Scripts\python.exe -m pytest -q
cmd /c run.bat --verify
```

## Evidence

- Full pytest: `149 passed, 1 skipped`; the skipped test is the opt-in live-provider test.
- Focused v0.6 service/API suite: `18 passed`, plus shared UI client and three Streamlit page tests.
- Migration: `PRAGMA user_version=6`; 18 application tables; v0.5 essay/revision/feedback data preserved.
- Configuration: create, content hash, required note, validate, reject invalid, activate, one-active constraint,
  rollback, persistence and audit passed. Activation/rollback versions appeared on subsequent AnalysisRuns.
- Security: extra secret-shaped fields were rejected and synthetic secret values were absent from API/database/UI tests.
- Visualization: timeline, inclusion/exclusion, issue data and separate Analyzer/Metric/config version segments passed.
- Reanalysis: four scopes previewed; new AnalysisRuns and Revision Snapshots appended; default LLM off; separately
  confirmed LocalDemo LLM path appended feedback without replacing the essay or earlier feedback.
- FastAPI health 200, OpenAPI docs 200 and Streamlit 200 through `run.bat --verify`.
- DeepSeek had already been reverified during the v0.5 gate, including a real Prompt/Schema v0.5 revision response
  citing R001–R005 with no fallback. v0.6 default reanalysis deliberately made no paid call.

## Research and deployment limits

Charts expose existing prototype signals and add no validity. Configuration range checks do not validate research
thresholds. The admin interface is local-only and lacks production authentication/multi-tenancy. CALF is represented
only by extension interfaces and verification statuses; there is no CALF total, proficiency score or CEFR inference.
v0.7 remains not started pending the final human review guide.
