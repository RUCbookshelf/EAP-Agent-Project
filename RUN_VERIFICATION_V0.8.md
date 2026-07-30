# v0.8 Verification — 2026-07-30

## Automated verification

- Full suite: 225 passed, 5 skipped; live/provider tests are opt-in because they consume external quota.
- CALF Cases A–M cover registries, duplicate rejection, reference MTLD/HD-D values, short text, normalization, candidates/manual confirmation, error evidence, timing, migration/rollback, API, reanalysis, configuration isolation, version isolation, and no student total.
- Fresh migration reached schema 10 and `config-v0.8.0`; migration 10→9→10 preserved data and configuration lineage.

## Sanitized live A–D

- A ordinary essay: DeepSeek `deepseek-v4-flash`; initial/final validation passed; retry 0; server repair false; fallback false; `spacy-analyzer-v0.8.0`; `config-v0.8.0`; migration 10; MTLD/HD-D available; CALF priority isolation passed.
- B short essay: DeepSeek validation passed; retry 0; server repair false; fallback false; HD-D `insufficient_data`, value `null`, no fake zero.
- C timed with 45-minute limit but no actual duration: WPM `insufficient_data`, value `null`; limit not used as duration.
- D timed with 900 actual seconds: 207 words / 15 minutes = 13.8 WPM, exactly reproducible.

No key, raw provider response, or full essay text is stored in this report.

## Service and rendered UI gate

`run.bat --verify` passed migration 10, initialization, FastAPI health 200, docs 200, and Streamlit 200. Browser plugin was unavailable, so Playwright 1.62 with installed Microsoft Edge verified the submission → research view → CALF tab flow on desktop and 390×844 mobile: page identity, nonblank render, no framework overlay, no console errors, Accuracy boundary, and real view/form/tab interaction. The stale v0.7.1 page title found during this check was corrected to v0.8.
