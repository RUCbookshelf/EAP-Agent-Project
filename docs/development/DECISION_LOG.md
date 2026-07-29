# Decision log

## D001 — Preserve v0.1.1 as an incremental compatibility layer

- Date: 2026-07-29
- Status: accepted
- Decision: retain Analyzer, Diagnoser, Prompt Builder, Provider Router, and feedback validator; wrap them with new services and Repository protocols rather than rewrite them.
- Reason: protects proven evidence validation and fallback behavior.

## D002 — Use numbered native SQLite migrations for v0.2

- Date: 2026-07-29
- Status: accepted
- Decision: use small, versioned Python migration functions with `PRAGMA user_version` and a migration history table, not SQLAlchemy/Alembic.
- Reason: the existing system is small and sqlite3-based; a native runner is the minimum reliable non-destructive mechanism and keeps dependencies limited. PostgreSQL remains an explicit future adapter seam, not a fake implementation.

## D003 — Keep API routes thin and application services framework-neutral

- Date: 2026-07-29
- Status: accepted
- Decision: FastAPI dependency wiring may construct services, but routes only validate, invoke, and translate results. Services contain no FastAPI or Streamlit imports.

## D004 — Fixed local ports fail clearly

- Date: 2026-07-29
- Status: accepted
- Decision: local FastAPI and Streamlit ports are configured once; startup fails with a clear error when unavailable and never silently selects another port.

## D005 — v0.2 acceptance and transition

- Date: 2026-07-29
- Status: accepted
- Decision: v0.2 passed all gates and was committed as `155df8a6a6a2800205b6dc821d1e51cf135b78a1`; the post-gate architecture backup is `docs/visualizations/V0.2_FUNCTION_ARCHITECTURE.md`. v0.3 may begin automatically.

## D006 — Transparent v0.3 longitudinal heuristics

- Date: 2026-07-29
- Status: accepted for prototype review
- Decision: anchor comparisons on the newest submission; admit only `comparable` records to primary baselines/trends; require 3 observations; use ordered-index OLS slope, ±10% first/last change, CV variability, and at most `medium` confidence. Track issue trajectories from structured diagnoses only.
- Reason: this is the smallest explainable approach that preserves uncertainty and can be replaced after literature and empirical calibration. It is not claimed as a validated theoretical or measurement model.

## D007 — Screen Snapshot evidence before LLM use

- Date: 2026-07-29
- Status: accepted
- Decision: FeedbackContext receives a screened Snapshot without excluded submissions or raw historical observations. Local code converts selected conclusions into H evidence IDs. The LLM may cite those IDs but may not recalculate trends or strengthen confidence.

## D008 — Accept v0.3 and stop for human review

- Date: 2026-07-29
- Status: accepted
- Decision: v0.3 passed the 27-item acceptance gate and real DeepSeek verification. The implementation commit is `0ce8f1a`; the post-gate architecture backup is `docs/visualizations/V0.3_FUNCTION_ARCHITECTURE.md`.
- Stop condition: do not implement v0.4 or later work until a human reviews the architecture, comparability rules, longitudinal heuristics, learner profile, and research assumptions documented in `docs/development/V0.3_HUMAN_REVIEW_GUIDE.md`.

## D009 — Authorize the bounded v0.4 → v0.5 → v0.6 sequence

- Date: 2026-07-29
- Status: accepted
- Decision: the project owner supplied an explicit continuation goal authorizing v0.4, v0.5 and v0.6 in sequence. This satisfies the v0.3 human-review stop gate for engineering continuation without treating the reviewed heuristics as educationally validated.
- Boundary: complete each independent acceptance gate and Git commit; stop after v0.6. Do not begin v0.7, full CALF measurement, cloud deployment or a WeChat client.
- Recovery point: annotated Git tag `pre-v0.4-baseline-20260729` points to the verified v0.3 documentation commit.

## D010 — Accept v0.4 Analyzer 2.0 and continue to v0.5

- Date: 2026-07-29
- Status: accepted
- Decision: use spaCy 3.8.7 and en_core_web_sm 3.8.0 as the default local backend, with an explicit BasicAnalyzer fallback; store token-scale evidence in append-only JSON artifacts and versioned MetricResults rather than fixed columns.
- Evidence: 97 passed, 1 opt-in live test skipped; migration 4; current and clean-environment `run.bat --verify` passed; FastAPI/docs/Streamlit returned 200; clean Python 3.11.15 environment passed `pip check`.
- Research boundary: parser, dictionary, MATTR, lexical density and diagnostic thresholds remain automatic unverified prototype signals.

## D011 — Accept v0.5 revision-aware feedback and continue to v0.6

- Date: 2026-07-29
- Status: accepted
- Decision: revision relationships must be explicit; use deterministic local paragraph/sentence/token alignment and append-only Revision Snapshots; default longitudinal analysis uses final-draft-else-latest per Revision Group.
- Evidence: 121 passed, 1 opt-in live test skipped; migration 5; real DeepSeek Prompt/Schema v0.5 revision call cited R001–R005 and passed after one correction retry without fallback; FastAPI/docs/Streamlit and `run.bat --verify` passed.
- Research boundary: alignment and uptake are observed heuristic candidates, not revision-quality scores, proficiency growth or causal feedback effects.

## D012 — Accept v0.6 and stop before v0.7

- Date: 2026-07-29
- Status: accepted for final human review
- Decision: expose only API-computed, version-separated progress evidence; version only allowlisted non-sensitive configuration; preserve exactly one active configuration with append-only audit; make reanalysis local-only by default and require explicit LLM cost confirmation.
- Evidence: 149 passed, 1 opt-in live test skipped; migration 6; configuration activate/rollback/persistence, four reanalysis scopes, FastAPI/docs/Streamlit and `run.bat --verify` passed.
- Boundary: registries and verification statuses prepare CALF-family extensions but no CALF total, proficiency score or CEFR inference exists. Stop now; v0.7 remains not started until explicit authorization after final human review.
