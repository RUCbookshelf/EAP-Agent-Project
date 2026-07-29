# v0.7 verification record

Date: 2026-07-30. Platform: Windows 11, project `.venv` on CPython 3.11.

## Executed verification

| Check | Command or method | Result |
|---|---|---|
| Normal tests | `.venv\Scripts\python.exe -m pytest -q` | PASS: 195 passed, 3 skipped; live tests remain opt-in |
| Live DeepSeek | `RUN_LIVE_LLM_TESTS=1` with `tests\test_live_deepseek_v07.py` | PASS: 1 passed |
| One-click verification | `run.bat --verify` | PASS |
| FastAPI health | bounded startup probe | HTTP 200 |
| API docs | bounded startup probe | HTTP 200 |
| Streamlit | bounded startup probe | HTTP 200 |
| Prompt manifest | `python -m scripts.initialize_project` | v0.7 manifest/hash PASS |
| Database | additive migration/read-only counts/model parsing | migration 8; old data readable |
| Security | ignore/tracked/exact-key scans | `.env` ignored; no tracked env/db; 0 exact key matches in tracked files or DB |

The three default-skipped tests are explicit quota-consuming live-provider tests. Two deprecation warnings concern Starlette TestClient/httpx and spaCy Click integration; neither affected acceptance.

## Live longitudinal result

- Synthetic student; three comparable independent argumentative tasks, 45 minutes, no tools.
- Provider `deepseek`; model `deepseek-v4-flash`; status `success`; StructuredFeedback `passed`.
- Prompt `feedback-prompt-v0.7.0`; schema `structured-feedback-v0.7.0`.
- Retry count 0; fallback false; fallback reason null.
- Snapshot `learner-profile-v0.7.0`; 3 representatives; Data Sufficiency `provisional`; 1 current target; 1 append-only HE record.
- Only current Gate-selected categories and their bound History Evidence entered feedback.

## Case A–I

- A: one task → insufficient; no trend/persistent claim.
- B: two tasks → limited pairwise comparison, not a trend.
- C: repeated selected current issue → versioned persistent-pattern rule.
- D: current suppressed issue → no current target.
- E: three drafts in one Revision Group → one default representative; revision records retained.
- F/G/H: genre, tool condition and analyzer/version differences split clusters.
- I: no current selected diagnosis → zero targets, no padding.

## Migration and preservation

The working database upgraded from migration 7 to 8 without deletion. Five essays, five AnalysisRuns, three Revision Snapshots and five historical Learner Profile Snapshots remained readable. Migration 8 created `history_evidence_registry` and additive snapshot metadata columns; old rows were not rewritten. `config-v0.7.0` is active and `config-v0.6.2` remains available for rollback.

## Known limits and stop boundary

Task equivalence, thresholds, direction labels and pattern labels are prototype working assumptions without literature, educational, reliability or validity calibration. No proficiency, mastery, causal learning, CEFR, CALF, T-unit, grammar-error total, overall score, cloud deployment, paid embedding, WeChat, v0.8 or later feature was implemented.

Git release action: one isolated commit with message `feat(v0.7): strengthen task-aware longitudinal learner modeling`; commit hash is reported in the final acceptance summary because a commit cannot contain its own hash.
