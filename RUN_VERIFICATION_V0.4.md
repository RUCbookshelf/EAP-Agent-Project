# v0.4 acceptance verification

Date: 2026-07-29 (Asia/Shanghai). Baseline recovery tag: `pre-v0.4-baseline-20260729`.

## Executed verification

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests -q
& ".\.venv\Scripts\python.exe" -m scripts.migrate_database
& ".\.venv\Scripts\python.exe" -m scripts.verify_nlp_resources
cmd.exe /d /c "call run.bat --verify"
set WRITING_FEEDBACK_VENV=.venv-clean-v04
set LLM_PROVIDER=local
cmd.exe /d /c "call run.bat --verify"
& ".\.venv-clean-v04\Scripts\python.exe" -m pip check
```

## Results

- Tests: 97 passed, 1 skipped. The skipped test is the opt-in real DeepSeek test; no paid call was requested for this gate.
- Runtime: Python 3.11.15; spaCy 3.8.7; en_core_web_sm 3.8.0.
- Migration: non-destructive upgrade to version 4; existing essays/feedback/Snapshots retained.
- Services: FastAPI health 200, `/docs` 200, Streamlit 200; Streamlit-through-HTTP submission test passed.
- Portability: a newly created `.venv-clean-v04` installed every dependency/model from zero, passed `pip check`, migration and dual-service startup in the project path containing Chinese, spaces and an apostrophe.
- LocalDemo: protected v0.4 submission returned valid feedback-prompt-v0.4.0 output without a key.
- DeepSeek: configuration presence only was checked; the normal suite did not make a paid request.
- Persistence: first analysis received `AR000001`; reanalysis appended `AR000002`, retained the first run and left feedback count unchanged.
- Fallback: missing-model test persisted BasicAnalyzer use and a non-secret fallback reason; health exposes fallback state.
- Security: `.env`, `.venv*`, databases, Python/model caches and logs are ignored; API/database schemas contain no API-key field.

## Acceptance gate

All 34 required areas are covered by the v0.4 NLP, repository, migration, API, UI, Prompt, fallback and regression suites. The Analyzer registry, versioned metrics, input-quality evidence, lexical/connective/syntactic candidates, append-only reanalysis, mixed-version limitation path, LocalDemo and existing post-validation chain are operational.

This proves software behavior and traceability only. It does not validate educational interpretations, CALF measurement, proficiency, grammar accuracy, task equivalence or learner development.
