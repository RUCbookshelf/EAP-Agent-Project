# RUN_VERIFICATION_V0.9.6_C.md

**Stage:** v0.9.6-C (C1 no-priority workflow completion, C2 sidebar/icon
repair, C3 combined closure). Owner gates: C1 accepted, C2 accepted.

## Isolation rules (all layers)

- `PYTHON_DOTENV_DISABLED=1`; `DATABASE_URL` absent; `DATABASE_PATH` =
  fresh unique temporary database; `LLM_PROVIDER=local`.
- Development database (`data/writing_feedback.db`) was never opened or
  written; SHA-256, size, and mtime recorded before and after every layer.
- C-stage incident baseline fingerprint (recorded at C3 start, after the
  owner's C2 acceptance session):
  `5352314D84CB2EA541E9AA86BB56B836AF2BF2B3F55863B030F85077D7E225BB`,
  14,151,680 bytes, mtime `2026-08-04T10:30:10.3545245+08:00`.
- Research exports guarded with `verification/v0.9.5-h2d2/
  export_workspace_guard.py` (baseline 776 files / 388 dirs).
- Ports 8000/8501 verified free before and after every run. The owner's
  running app session (started 10:30) was closed before layer 2 with the
  owner's workflow authorization; no data was written and the development
  database fingerprint did not change.

## Layer results (run in order, exactly once each)

| Layer | Target | Result |
|---|---|---|
| 1 C1 focused | tests/test_v096c1_no_priority_workflow.py | 20 passed |
| 2 C2 focused | tests/test_v096c2_sidebar_control.py, tests/test_v096c2_genre_icon_rendering.py | 29 passed |
| 3 Student pages | tests/test_student_experience_v094b.py, tests/test_v095c_ui_boundaries.py, tests/test_v071_reliability_ui.py, tests/test_streamlit.py, tests/test_streamlit_api_integration_v02.py | 52 passed, 3 skipped |
| 4 A/B reliability | tests/test_v096a_linked_revision_submission.py, tests/test_v096b_first_draft_submission.py | 51 passed |
| 5 UI client/locale contracts | tests/test_ui_api_client_v02.py, tests/test_v095d_api_contract.py, tests/test_v095d_port_contract.py, tests/test_v095c_feature_extraction.py | 36 passed |
| 6 Full non-live core | pytest --ignore=tests/live tests | 809 passed, 8 skipped, 0 failed, 0 errors, exit 0 |
| 7 Launcher | exact `cmd /c "run.bat --verify"` | PASS, exit 0 |

Layer 3 note: one stale v0.9.4-B assertion
(`test_feedback_content_orders_priority_before_action_and_evidence`) still
expected the pre-C1 literal `section_header("student_feedback_strengths")`
call; it was aligned to the accepted C1 conditional
`"student_feedback_strengths" if strengths else
"student_feedback_neutral_passage"` (one line in
`tests/test_student_experience_v094b.py`). No production behavior changed.

## Launcher output (layer 7)

```text
migration_version:                 12
database_table_count:              33
active_configuration_version:      config-v0.9.0
prompt_version:                    feedback-prompt-v0.7.1
health / docs / streamlit:         200 / 200 / 200
status:                            PASS
```

## Development database fingerprints (every layer)

Before and after each layer:
`5352314D84CB2EA541E9AA86BB56B836AF2BF2B3F55863B030F85077D7E225BB`,
14,151,680 bytes, mtime `2026-08-04T10:30:10.3545245+08:00`. Unchanged.

## Research exports

- Guard `--check` before layer 1: BASELINE OK (776 files / 388 dirs).
- After layer 6 (full core): test-created additions detected (8 export
  dirs, 16 files); guard `--delta` recorded them
  (`test_export_deltas.json`); guard `--restore` deleted only the
  allowlisted additions and re-verified: BASELINE OK, 776 files / 388
  dirs.
- Final guard `--check`: BASELINE OK.

## Final frozen invariants (source + launcher verified)

```text
API path+method pairs:              77   (tests/contracts/api_surface_contract.py)
Database public methods:             2   (connect, initialize)
Frontend client public methods:     53
Locale parity:                 540/540   (12 approved C1 keys added; 0 removed)
Migration:                          12
Tables:                             33
Active configuration:    config-v0.9.0
Active feedback prompt: feedback-prompt-v0.7.1
```

## Changed files (closure commit)

- `docs/development/V0.9.6_C_SPEC.md` (new)
- `RUN_VERIFICATION_V0.9.6_C.md` (new)
- `CHANGELOG.md`, `PROJECT_STATE.md`, `docs/development/MASTER_ROADMAP.md`,
  `docs/development/CURRENT_TASK_STATE.md`, `docs/development/DECISION_LOG.md`
  (minimal updates)
- `tests/test_student_experience_v094b.py` (one stale assertion aligned to
  accepted C1 behavior)
- `verification/v0.9.5-h2d2/test_export_deltas.json` (layer-6 delta record)

Preserved user-owned paths (`AGENTS.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `.claude/`,
`ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `CLAUDE.md`,
`data/demo_journey_manifest.json`, `data/writing_feedback.db`, backups,
all 776 export files) were not staged or modified.

## Closure

```text
test(v0.9.6-c): close no-priority and sidebar repairs
```