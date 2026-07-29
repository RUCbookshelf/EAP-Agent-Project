# v0.3 acceptance verification

Date: 2026-07-29 (Asia/Shanghai). v0.2 implementation commit: `155df8a6a6a2800205b6dc821d1e51cf135b78a1`. v0.3 implementation commit: `0ce8f1a`.

## Executed commands

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests -q
& ".\.venv\Scripts\python.exe" -m scripts.seed_longitudinal_data --database data\demo_longitudinal_v03_verification.db
& ".\.venv\Scripts\python.exe" -m scripts.migrate_database
cmd.exe /d /c "call run.bat --verify"
$env:RUN_LIVE_LLM_TESTS="1"
& ".\.venv\Scripts\python.exe" -m scripts.verify_live_deepseek
& ".\.venv\Scripts\python.exe" -m scripts.audit_live_verification
& ".\.venv\Scripts\python.exe" -m pytest tests -q
```

## Current direct evidence

- Tests with `RUN_LIVE_LLM_TESTS=1`: 86 passed; one upstream TestClient deprecation warning.
- Migration: existing local database upgraded non-destructively to version 3.
- Startup: FastAPI health 200, `/docs` 200, Streamlit 200 through `run.bat --verify`.
- Synthetic database: A=available/increasing/persistent/recently_reduced; B=insufficient after task exclusions; C=insufficient with 2 records; D=available/fluctuating.
- Snapshot restart: tests reopen SQLite and recover latest/history Snapshot IDs.
- LLM integration: a three-submission API test sends a screened Snapshot, generates local H evidence IDs, and validates that LocalDemo cites only allowed IDs.
- Real DeepSeek integration: two fresh submissions completed with provider `deepseek`, model `deepseek-v4-flash`, prompt `feedback-prompt-v0.3.0`, schema `structured-feedback-v0.1.1`, validation `passed`, retry count 0, and no fallback. The second response cited both allowed history evidence IDs (`H001`, `H002`).
- Secret handling audit: the verification report records no secret; SQLite has no API-key column. The check inspected presence only and did not print the key.

## 27-item gate audit

| # | Requirement | Status | Evidence |
|---:|---|---|---|
| 1 | Comparability engine | PASS | `ComparabilityService` and tests |
| 2 | Reasons per judgment | PASS | matched/mismatched/reasons assertions |
| 3 | Personal baseline | PASS | 3-record available baseline test |
| 4 | Insufficient history | PASS | 1/2-record engine and API tests |
| 5 | Metric time series | PASS | eight versioned MetricTrend outputs |
| 6 | Direction | PASS | increasing/decreasing/stable/fluctuating/insufficient tests |
| 7 | Variability | PASS | CV and high-variation test |
| 8 | Trend confidence | PASS | insufficient/low/medium only |
| 9 | Persistent issue | PASS | structured diagnosis occurrence test |
| 10 | Recently reduced issue | PASS | prior occurrence + two-record absence test |
| 11 | Snapshot save | PASS | SQLite repository test |
| 12 | Snapshot versioning | PASS | append/recalculate/history test |
| 13 | progress API | PASS | filters and success tests |
| 14 | profile API | PASS | latest Snapshot/profile test |
| 15 | Filtered DeepSeek evidence | PASS | live DeepSeek response cited only `H001` and `H002` from the screened history evidence |
| 16 | No CEFR | PASS | API field/content test |
| 17 | No overall ability score | PASS | API field/content test |
| 18 | No ability-growth interpretation | PASS | model wording and limitation tests |
| 19 | Ordinary and live tests | PASS | 86 passed with live DeepSeek enabled |
| 20 | FastAPI startup | PASS | health 200 |
| 21 | Streamlit startup | PASS | HTTP 200 |
| 22 | run.bat | PASS | actual `cmd.exe` verification |
| 23 | Database migration | PASS | empty/v0.1.1/v0.2/idempotent/current DB tests |
| 24 | Restart persistence | PASS | reopened Snapshot database test |
| 25 | Documentation | PASS | named v0.3 docs and review guide |
| 26 | Independent Git commit | PASS | `0ce8f1a` (`feat(v0.3): add longitudinal analysis and learner profile snapshots`) |
| 27 | Real verification report | PASS | this file plus `data/live_deepseek_verification.json`; database audit passed |

## Research boundary

This acceptance proves software behavior and traceability only. It does not prove educational validity, language ability, genuine development, measurement reliability, fairness or suitability for automated instructional decisions.

Post-gate architecture backup: `docs/visualizations/V0.3_FUNCTION_ARCHITECTURE.md`. Human review guide: `docs/development/V0.3_HUMAN_REVIEW_GUIDE.md`. Work stops at v0.3; no v0.4 implementation is included.
