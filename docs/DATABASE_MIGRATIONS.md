# Database migrations

The project uses a minimal native SQLite migration runner because the existing repository is small and sqlite3-based. This is a deliberate local prototype choice, not an Alembic or PostgreSQL implementation.

- Current version: 14 (`LATEST_MIGRATION_VERSION = 14`, `app/database/migrations.py`).
- Authority: `PRAGMA user_version` plus `schema_migrations` audit rows.
- The runner applies versions in order inside transactions, never drops the database, and is repeatable. Each applied version inserts or ignores a `schema_migrations` row (version, name, applied_at) and sets `PRAGMA user_version`.

## Applied migrations (1..14)

| # | Name | Summary |
|---|---|---|
| 1 | `preserve_v0_1_1_schema` | Creates/preserves the base schema and adds missing legacy columns (`essays.time_limit_minutes`; `feedback_records` template/rendered-prompt hashes, schema_version, temperature, request/response time, validation_status, retry_count; `exercises.diagnosis_id`; `learner_history` comparability fields). |
| 2 | `cloud_ready_repository_indexes` | Adds the `schema_migrations` ledger and the student/submission lookup index. |
| 3 | `longitudinal_profile_snapshots` | Adds append-only learner profile snapshots and their student/time index. |
| 4 | `versioned_nlp_analysis_runs` | Adds `analysis_runs`, `metric_results`, and `analysis_artifacts` with versioned analysis provenance. |
| 5 | `revision_relationships_and_snapshots` | Adds revision metadata to `essays` plus append-only `revision_groups`/`revision_snapshots`. |
| 6 | `versioned_non_sensitive_configuration` | Adds `configuration_versions` and `configuration_audit` with at-most-one-active enforcement. |
| 7 | `diagnostic_calibration_and_metric_confidence` | Extends `metric_results` and adds append-only `diagnostic_calibrations`. |
| 8 | `learner_model_v2_and_history_evidence` | Extends `learner_profile_snapshots` and adds the append-only `history_evidence_registry`. |
| 9 | `longitudinal_reliability_and_provider_status` | Adds `feedback_records.provider_status_json` and activates a preserved config-v0.7.1 child. |
| 10 | `calf_measurement_foundation` | Adds timing fields to `essays`, CALF semantic/provenance fields to `metric_results`, and append-only `analysis_units`/`error_annotations`; activates config-v0.8.0. |
| 11 | `research_data_infrastructure` | Adds `human_reviews`, `pii_candidates`, and `export_jobs`; activates config-v0.8.2. |
| 12 | `practice_and_transfer_foundation` | Adds the practice/transfer table family (`practice_targets`, `exercise_instances`, `exercise_attempts`, `practice_evaluations`, `feedback_engagement_traces`, `within_task_response_candidates`, `transfer_evidence_candidates`, `practice_state_snapshots`); activates config-v0.9.0. |
| 13 | `practice_target_priority_key_uniqueness` | Adds the partial unique index `ux_practice_targets_active_priority_key` enforcing at most one ACTIVE practice target per (student, submission, source priority); rollback only drops the index. |
| 14 | `wave2_revision_loop_and_learner_model` | Wave-2 additive persistence (Goal PDW2-A-CORE-PERSISTENCE): creates only new tables `writing_tasks`, `submission_revisions`, `learning_observations`, and `learning_items` plus indexes; no existing-table DDL. Rollback 14→13 is ledger-only (non-destructive: tables and data preserved; re-apply idempotent). |

Rollback (`rollback()`) is logical and non-destructive, one step at a time, for applied versions 14→13 through 9→8: it deletes the matching `schema_migrations` row and lowers `PRAGMA user_version` without deleting additive data. Re-upgrade is idempotent.

Tests prove empty initialization, legacy-row preservation, idempotence and separate test databases (`tests/test_migrations_v02.py`, `tests/shared/test_version_single_sourcing.py`). `run.bat` executes `python -m scripts.migrate_database` before either service starts.

## Numbering supersession (migration 14)

Version 14 is the Wave-2 additive persistence migration
(`wave2_revision_loop_and_learner_model`, Goal PDW2-A-CORE-PERSISTENCE), not
the previously planned `essays.domain` discriminator lane. The deferred
`essays.domain`/language discriminator and Academic table family remain
trigger-gated and were NOT implemented; when its implementation Goal fires it
must use the next free version number (>= 15), NOT 14. Its DROP COLUMN
rollback contract is preserved in the `app/database/migrations.py` header note
(F-6; asserted by `tests/test_migration_drop_column_rollback_note.py`). See
`docs/integration/wave1/06_MIGRATION_14_DECISION.md` (decision) and
`docs/integration/wave1/13_MIGRATION_14_AMENDMENTS.md` (amendment record
F-1..F-6).

Back up research data before future migrations. PostgreSQL requires a separate adapter and migration strategy and is not currently implemented.
