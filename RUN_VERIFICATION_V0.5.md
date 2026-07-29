# v0.5 run verification — 2026-07-29

## Result

PASS. Revision-aware feedback is runnable with migration 5, append-only Snapshot persistence, LocalDemo and real
DeepSeek paths, FastAPI, OpenAPI docs and Streamlit. These checks establish engineering behavior only; they do not
validate educational effectiveness, ability measurement or causal feedback effects.

## Commands actually executed

```powershell
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m pytest -q tests\test_revision_v05.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.initialize_project
$env:RUN_LIVE_LLM_TESTS='1'; .\.venv\Scripts\python.exe -m scripts.verify_live_deepseek
cmd /c run.bat --verify
```

## Evidence

- Full pytest: `121 passed, 1 skipped`; the skip is the explicitly opt-in live-provider test.
- Focused v0.5 suite: `19 passed` (plus revision client cases in the shared client suite).
- Migration: SQLite `PRAGMA user_version=5`; 16 application tables; existing essay data preserved.
- Prompt v0.5 manifest: validated; structured feedback schema `structured-feedback-v0.5.0`.
- `run.bat --verify`: PASS; FastAPI health 200, OpenAPI docs 200, Streamlit 200.
- Revision persistence: first/revised/final membership and append-only Snapshot history passed after repository reopen.
- Real DeepSeek longitudinal retry: PASS with provider `deepseek`, validation `passed`, retry count 0 and no fallback.
- Real DeepSeek revision call: PASS with Prompt `feedback-prompt-v0.5.0`, Schema
  `structured-feedback-v0.5.0`, validated references `R001`–`R005`, one correction retry and no fallback.
  Sanitized outputs record `api_key_recorded=false`; no key or complete request was printed or stored in reports.
- LocalDemo revision feedback: Prompt v0.5 and valid `R...` evidence references passed.

## Covered behavior

Explicit relationships and candidate reads; cross-student/self/cycle/duplicate rejection; paragraph/sentence/token
alignment; inserted/deleted/light/heavy/split/merged; major rewrite; compatible and incompatible metric differences;
diagnosis trajectories; supported/partially-supported/not-assessable uptake candidates; exercise-source metadata;
Snapshot save/recalculate/history; revision APIs/client/UI; and one-representative-draft longitudinal deduplication.

## Current limitations

Alignment, comparability, major-rewrite, diagnosis and uptake rules are transparent working assumptions. Surface
similarity is not semantic equivalence. `not_currently_observed` is not solved/mastered. Uptake candidates cannot show
that feedback caused a revision. Human review cases are listed in `docs/development/V0.5_HUMAN_REVIEW_GUIDE.md`.
