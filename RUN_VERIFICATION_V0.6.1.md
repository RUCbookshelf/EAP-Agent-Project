# v0.6.1 Run Verification

Date: 2026-07-29 (Asia/Shanghai). Status: `PASS`.

## Baseline and recovery point

- Read the required governing, architecture, NLP, registry, configuration, limitation, roadmap, decision, and v0.6 review files before implementation.
- Baseline: `152 passed, 1 skipped`; FastAPI, `/docs`, Streamlit, and `run.bat --verify` passed.
- Preserved the pre-v0.6.1 fixes in commit `554f248` and created annotated tag `pre-v0.6.1-baseline-20260729` before calibration work.

## Commands actually executed

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -q
& ".\.venv\Scripts\python.exe" -m compileall -q app scripts tests
& ".\.venv\Scripts\python.exe" -m scripts.initialize_project --help
$env:RUN_LIVE_LLM_TESTS='1'; & ".\.venv\Scripts\python.exe" -m scripts.verify_live_deepseek_v061
cmd /c run.bat --verify
```

Git status/log, migration version, active configuration, prompt manifest hashes, NLP resource status, ignored `.env`, tracked-file secret matches, and database secret matches were also checked without printing the key.

## Automated results

- Default pytest: `183 passed, 2 skipped` in 79.18 seconds. The skips are opt-in live external-API tests.
- Compile: PASS.
- Initialization: PASS; 19 tables; migration 7; prompt `feedback-prompt-v0.6.1`; active `config-v0.6.2`.
- Empty database initialization: covered and PASS.
- Synthetic v0.6 database upgrade: PASS; preserved historical essay and created the v0.6.1 child configuration without deleting its parent.
- Configuration activate/rollback: PASS.
- First Draft regression: PASS. Prompt keywords `history`/`lie` retained; `bias` count 3 at sentence IDs 2/6/11, density below 0.025, no local cluster, monitored and not selected; Furthermore, However, and Ultimately detected; no count-only connective priority; lexical protocols reproducible.
- Revised Draft regression: PASS. Explicit revision relationship and Snapshot retained; monitored first-draft signal not marked solved; v0.6.1 diagnosis version stored independently; longitudinal and revision evidence remain separate.
- `run.bat --verify`: PASS; migration 7; FastAPI health 200; API docs 200; Streamlit 200.

Two dependency deprecation warnings remain: FastAPI TestClient's compatibility shim and spaCy/Click parser import. They do not fail runtime or tests.

## Live DeepSeek result

```text
Provider: deepseek
Model: deepseek-v4-flash
Status: success
Prompt: feedback-prompt-v0.6.1
Schema: structured-feedback-v0.6.1
Validation: passed
Retry count: 0
Fallback: false
Selected priorities: 0
Exercises: 0
```

The model accepted the conservative zero-priority result and did not reactivate monitored `bias`. The verifier used a temporary SQLite database and recorded neither API Key nor raw response. The safe report is `data/live_deepseek_v061_verification.json`.

## Completed capability gates

Metric Confidence; reproducible lexical protocols; Diagnostic Gate; raw/monitored/eligible/selected/suppressed states; transparent Priority Score; relevant-evidence validation; calibrated repetition/connective rules; necessary-term and prompt-keyword down-weighting; strength/descriptive separation; calibrated syntax-candidate names; selected-only exercises; DeepSeek/LocalDemo gate compliance; API/repository/migration/configuration/audit UI; First and Revised Draft regression.

## Versions

- Application: 0.6.1
- Database migration: 7
- Analyzer: `spacy-analyzer-v0.6.1`
- Diagnosis: `prototype-diagnosis-v0.6.1`
- Calibration/Gate/Priority: v0.6.1
- Prompt/Schema: v0.6.1
- Active configuration: `config-v0.6.2`; preserved parent: `config-v0.6.1`

## Limits requiring human or literature calibration

Priority 0.52; repetition count 4 and density 0.025; local-cluster window; prompt and necessary-term penalties; genre/history component weights; connective resource coverage and boundary rule; exercise maxima; token/POS/parser policies. These are prototype working assumptions, not educationally validated thresholds, ability judgements, CEFR levels, CALF scores, or teacher replacements. v0.7 and CALF remain `not_started`.
