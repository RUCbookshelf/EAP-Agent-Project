# v0.2 acceptance verification

Date: 2026-07-29 (Asia/Shanghai). Baseline commit: `62f8a39f8ace4091a34fcff92bef08135e01037e`.

## Baseline

- 42 passed, 1 default-skipped live test.
- Existing Streamlit HTTP 200 and legacy `run.bat --verify` PASS.
- Existing SQLite contained 9 domain tables and `PRAGMA user_version=0`.

## Commands executed

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests -q
& ".\.venv\Scripts\python.exe" -m scripts.migrate_database
& ".\.venv\Scripts\python.exe" -m scripts.smoke_stack --python ".\.venv\Scripts\python.exe"
cmd.exe /d /c "call run.bat --verify"
```

The no-environment-file path was separately executed with a nonexistent `WRITING_FEEDBACK_ENV_FILE`, `LLM_PROVIDER=local`, an isolated database, and alternate fixed ports.

## Direct results

| Gate | Status | Evidence |
|---|---|---|
| v0.1.1 behavior retained | PASS | original Analyzer, Diagnoser, Prompt, Provider, validation, retry/fallback and history tests remain green |
| FastAPI local startup | PASS | health HTTP 200 |
| API docs | PASS | `/docs` HTTP 200 |
| Streamlit local startup | PASS | HTTP 200 |
| Streamlit complete API workflow | PASS | AppTest submitted a form through a live uvicorn process and rendered LocalDemo feedback |
| UI isolation | PASS | AST tests prohibit database, Repository, LLM, Analyzer, Diagnoser and Feedback imports |
| Repository abstraction | PASS | ten named protocols and SQLite implementation |
| Transaction rollback | PASS | forced exception leaves no inserted student |
| Restart persistence/isolation | PASS | reopened database retains row; separate database does not see it |
| Empty/legacy/idempotent migration | PASS | migration tests retain legacy row and reach version 2 repeatedly |
| Existing database migration | PASS | local database reached version 2 without deletion |
| LocalDemo without `.env` | PASS | health/docs/Streamlit all HTTP 200; key configured false |
| DeepSeek compatibility | PASS | existing interface, mocked transport, retry and fallback tests remain green |
| `run.bat` | PASS | `cmd.exe` execution migrates, checks assets and probes both services |
| Secrets | PASS | no key is returned by health or stored by the schema |

## Current limits

All services are local. SQLite is not a production multi-user database. PostgreSQL, cloud deployment and WeChat are not implemented. v0.2 profile/progress explicitly defer formal prototype longitudinal analysis to v0.3.

## Clean-environment verification

`run.bat --verify` created and used a previously absent environment at:

`C:\Users\16073\AppData\Local\Temp\writing-feedback-v02-clean-20260729-1405`

Results: Python 3.11.15; dependencies installed from zero; `pip check` reported no broken requirements; migrations reached version 2; health, `/docs`, and Streamlit each returned HTTP 200; the clean interpreter reported 58 passed, 1 default-skipped live test in 5.28 seconds.

The project environment's pre-final run also reported 58 passed, 1 skipped. One upstream Starlette deprecation warning is emitted by FastAPI's compatibility `TestClient`; it does not affect runtime endpoints and is not suppressed.

The v0.2 implementation commit is recorded immediately after the final acceptance audit; its hash is added to the roadmap during the v0.3 transition.
