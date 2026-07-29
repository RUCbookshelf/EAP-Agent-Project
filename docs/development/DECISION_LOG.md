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
