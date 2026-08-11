from __future__ import annotations

import sqlite3
import hashlib
import json
from collections.abc import Callable


"""Minimal native SQLite migration runner.

Migration-version note (supersedes the pre-Wave-2 numbering plan):

- Version 14 is the Wave-2 additive persistence migration
  (``wave2_revision_loop_and_learner_model``, Goal PDW2-A-CORE-PERSISTENCE):
  it creates only new tables (writing_tasks, submission_revisions,
  learning_observations, learning_items) plus indexes. It is additive and
  non-destructive; rollback 14->13 is a logical ledger-only rollback that
  preserves the new tables and their data.
- The previously planned ``essays.domain`` discriminator (recorded at
  CORE-MIGRATION14-AMENDMENTS, design-review finding F-6) remains DEFERRED
  and trigger-gated; it was NOT implemented. When its implementation Goal
  fires it must use the next free version number (>= 15), NOT 14. Its DROP
  COLUMN rollback contract is preserved below:

  - ``ALTER TABLE ... DROP COLUMN`` rollback requires SQLite >= 3.35 (bundled
    SQLite 3.53.1 satisfies this).
  - The deferred additive ``essays.domain`` discriminator must keep a
    COLUMN-level CHECK; any future index/view/trigger on the ``domain`` column
    must be dropped BEFORE ``DROP COLUMN``, because a dependent object blocks
    the drop.

Asserted by ``tests/test_migration_drop_column_rollback_note.py``.
"""


LATEST_MIGRATION_VERSION = 14


def _add_column_if_missing(
    connection: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migration_1(connection: sqlite3.Connection) -> None:
    from app.database.repository import SCHEMA

    connection.executescript(SCHEMA)
    additions = {
        "essays": {"time_limit_minutes": "INTEGER"},
        "feedback_records": {
            "system_template_hash": "TEXT NOT NULL DEFAULT ''",
            "user_template_hash": "TEXT NOT NULL DEFAULT ''",
            "rendered_prompt_hash": "TEXT NOT NULL DEFAULT ''",
            "schema_version": "TEXT NOT NULL DEFAULT ''",
            "temperature": "REAL NOT NULL DEFAULT 0.0",
            "request_time": "TEXT", "response_time": "TEXT",
            "validation_status": "TEXT NOT NULL DEFAULT 'not_run'",
            "retry_count": "INTEGER NOT NULL DEFAULT 0",
        },
        "exercises": {"diagnosis_id": "TEXT NOT NULL DEFAULT ''"},
        "learner_history": {
            "comparability_status": "TEXT NOT NULL DEFAULT 'insufficient_history'",
            "history_evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "limitations_json": "TEXT NOT NULL DEFAULT '[]'",
            "comparability_reasons_json": "TEXT NOT NULL DEFAULT '[]'",
        },
    }
    for table, columns in additions.items():
        for column, definition in columns.items():
            _add_column_if_missing(connection, table, column, definition)


def _migration_2(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_essays_student_submitted ON essays(student_id, submitted_at)"
    )


def _migration_3(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS learner_profile_snapshots (
        snapshot_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL REFERENCES students(student_id),
        snapshot_json TEXT NOT NULL,
        analysis_version TEXT NOT NULL,
        configuration_version TEXT NOT NULL,
        included_submission_ids_json TEXT NOT NULL,
        created_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_profile_student_created ON learner_profile_snapshots(student_id, created_at, snapshot_row_id)"
    )


def _migration_4(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS analysis_runs (
            analysis_run_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_run_id TEXT UNIQUE,
            essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
            analyzer_id TEXT NOT NULL,
            analyzer_version TEXT NOT NULL,
            backend TEXT NOT NULL,
            nlp_library TEXT,
            nlp_library_version TEXT,
            nlp_model_name TEXT,
            nlp_model_version TEXT,
            parameters_json TEXT NOT NULL,
            resource_versions_json TEXT NOT NULL,
            configuration_version TEXT NOT NULL,
            fallback_used INTEGER NOT NULL DEFAULT 0,
            fallback_reason TEXT,
            analysis_duration_ms REAL NOT NULL,
            limitations TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_analysis_runs_essay_created
            ON analysis_runs(essay_id, analysis_run_row_id);
        CREATE TABLE IF NOT EXISTS metric_results (
            metric_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(analysis_run_id),
            metric_id TEXT NOT NULL,
            metric_version TEXT NOT NULL,
            value_json TEXT,
            unit TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            analyzer_version TEXT NOT NULL,
            resource_versions_json TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            limitations_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_metric_results_run_metric
            ON metric_results(analysis_run_id, metric_id, metric_version);
        CREATE TABLE IF NOT EXISTS analysis_artifacts (
            artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(analysis_run_id),
            artifact_type TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            artifact_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_analysis_artifacts_run
            ON analysis_artifacts(analysis_run_id, artifact_id);
        """
    )


def _migration_5(connection: sqlite3.Connection) -> None:
    additions = {
        "revision_of_submission_id": "INTEGER REFERENCES essays(essay_id)",
        "revision_group_id": "TEXT",
        "revision_sequence": "INTEGER",
        "revision_stage": "TEXT NOT NULL DEFAULT 'independent_submission'",
        "original_draft_stage": "TEXT",
    }
    for column, definition in additions.items():
        _add_column_if_missing(connection, "essays", column, definition)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS revision_groups (
            revision_group_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            revision_group_id TEXT UNIQUE,
            student_id TEXT NOT NULL REFERENCES students(student_id),
            writing_prompt TEXT NOT NULL,
            genre TEXT NOT NULL,
            root_submission_id INTEGER NOT NULL REFERENCES essays(essay_id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_consistency_json TEXT NOT NULL,
            limitations_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_revision_groups_student
            ON revision_groups(student_id, revision_group_row_id);
        CREATE INDEX IF NOT EXISTS idx_essays_revision_group
            ON essays(revision_group_id, revision_sequence);
        CREATE TABLE IF NOT EXISTS revision_snapshots (
            revision_snapshot_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            revision_snapshot_id TEXT UNIQUE,
            revision_group_id TEXT NOT NULL,
            source_submission_id INTEGER NOT NULL REFERENCES essays(essay_id),
            target_submission_id INTEGER NOT NULL REFERENCES essays(essay_id),
            snapshot_json TEXT NOT NULL,
            alignment_version TEXT NOT NULL,
            uptake_version TEXT NOT NULL,
            configuration_version TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_revision_snapshots_group
            ON revision_snapshots(revision_group_id, revision_snapshot_row_id);
        """
    )
    connection.execute(
        "UPDATE essays SET original_draft_stage=draft_stage WHERE original_draft_stage IS NULL"
    )


def _migration_6(connection: sqlite3.Connection) -> None:
    _ensure_feedback_append_only(connection)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS configuration_versions (
            configuration_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            configuration_id TEXT UNIQUE,
            version TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL CHECK(status IN ('draft','validated','active','inactive','archived')),
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            parent_version TEXT,
            payload_json TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            change_note TEXT NOT NULL,
            validation_status TEXT NOT NULL,
            validation_errors_json TEXT NOT NULL,
            activated_at TEXT,
            deactivated_at TEXT,
            content_hash TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_configuration_one_active
            ON configuration_versions(status) WHERE status='active';
        CREATE TABLE IF NOT EXISTS configuration_audit (
            audit_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id TEXT UNIQUE,
            configuration_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            reason TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_configuration_audit_config
            ON configuration_audit(configuration_id, audit_row_id);
        """
    )
    exists = connection.execute("SELECT 1 FROM configuration_versions LIMIT 1").fetchone()
    if not exists:
        payload = {
            "active_analyzer": "spacy", "fallback_analyzer": "basic", "mattr_window": 50,
            "local_repetition_window": 30, "long_sentence_threshold": 30,
            "prompt_keyword_weight": 0.35, "repetition_threshold": 3,
            "connective_resource_version": "connectives-v0.4.0",
            "comparability_rule_version": "comparability-v0.3.0", "minimum_baseline_points": 3,
            "persistent_threshold": 3, "recently_reduced_window": 2,
            "trend_relative_change": 0.10, "low_variability_cv": 0.10,
            "high_variability_cv": 0.30, "feedback_priority_count": 2,
            "llm_temperature": 0.2, "llm_max_tokens": 1800,
            "active_prompt_version": "feedback-prompt-v0.5.0",
            "revision_alignment_version": "local-sequence-alignment-v0.5.0",
            "uptake_rule_version": "feedback-uptake-v0.5.0",
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        now = "2026-07-29T00:00:00+00:00"
        cursor = connection.execute(
            """INSERT INTO configuration_versions(
                version,status,created_at,created_by,parent_version,payload_json,schema_version,
                change_note,validation_status,validation_errors_json,activated_at,content_hash
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("config-v0.6.1", "active", now, "system", None, canonical,
             "configuration-schema-v0.6.0", "Initial non-sensitive v0.6 configuration.",
             "passed", "[]", now, content_hash),
        )
        configuration_id = f"CFG{int(cursor.lastrowid):06d}"
        connection.execute(
            "UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?",
            (configuration_id, int(cursor.lastrowid)),
        )
        audit = connection.execute(
            """INSERT INTO configuration_audit(
                configuration_id,action,actor,reason,details_json,created_at
            ) VALUES (?,?,?,?,?,?)""",
            (configuration_id, "activate", "system", "Initial migration activation.", "{}", now),
        )
        connection.execute(
            "UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?",
            (f"CA{int(audit.lastrowid):06d}", int(audit.lastrowid)),
        )


def _migration_7(connection: sqlite3.Connection) -> None:
    metric_columns = {
        "measurement_status": "TEXT NOT NULL DEFAULT 'insufficient_data'",
        "confidence": "TEXT NOT NULL DEFAULT 'insufficient'",
        "confidence_reasons_json": "TEXT NOT NULL DEFAULT '[]'",
        "risk_factors_json": "TEXT NOT NULL DEFAULT '[]'",
        "eligible_for_diagnosis": "INTEGER NOT NULL DEFAULT 0",
        "eligible_for_longitudinal_comparison": "INTEGER NOT NULL DEFAULT 0",
        "measurement_metadata_json": "TEXT NOT NULL DEFAULT '{}'",
    }
    for column, definition in metric_columns.items():
        _add_column_if_missing(connection, "metric_results", column, definition)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS diagnostic_calibrations (
            calibration_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            calibration_id TEXT UNIQUE,
            essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
            analysis_run_id TEXT REFERENCES analysis_runs(analysis_run_id),
            calibration_json TEXT NOT NULL,
            calibration_version TEXT NOT NULL,
            gate_version TEXT NOT NULL,
            priority_version TEXT NOT NULL,
            evidence_validation_version TEXT NOT NULL,
            diagnosis_version TEXT NOT NULL,
            configuration_version TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_diagnostic_calibration_essay
            ON diagnostic_calibrations(essay_id, calibration_row_id);
        """
    )
    active = connection.execute(
        "SELECT * FROM configuration_versions WHERE status='active' ORDER BY configuration_row_id DESC LIMIT 1"
    ).fetchone()
    if active is None:
        return
    existing = connection.execute(
        "SELECT 1 FROM configuration_versions WHERE schema_version='configuration-schema-v0.6.1' LIMIT 1"
    ).fetchone()
    if existing:
        return
    from app.configuration import ConfigurationPayload

    old = dict(active)
    payload = ConfigurationPayload.model_validate(json.loads(old["payload_json"])).model_dump(mode="json")
    payload.update({
        "connective_resource_version": "connectives-v0.6.1",
        "active_prompt_version": "feedback-prompt-v0.6.1",
    })
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    versions = [str(row[0]) for row in connection.execute("SELECT version FROM configuration_versions")]
    suffixes = [int(value.rsplit(".", 1)[1]) for value in versions if value.startswith("config-v0.6.")]
    version = f"config-v0.6.{max(suffixes, default=0) + 1}"
    now = "2026-07-29T12:00:00+00:00"
    connection.execute(
        "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE configuration_id=?",
        (now, old["configuration_id"]),
    )
    cursor = connection.execute(
        """INSERT INTO configuration_versions(
            version,status,created_at,created_by,parent_version,payload_json,schema_version,
            change_note,validation_status,validation_errors_json,activated_at,content_hash
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (version, "active", now, "system", old["version"], canonical,
         "configuration-schema-v0.6.1", "Activate conservative v0.6.1 diagnostic calibration defaults.",
         "passed", "[]", now, content_hash),
    )
    configuration_id = f"CFG{int(cursor.lastrowid):06d}"
    connection.execute(
        "UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?",
        (configuration_id, int(cursor.lastrowid)),
    )
    audit = connection.execute(
        """INSERT INTO configuration_audit(
            configuration_id,action,actor,reason,details_json,created_at
        ) VALUES (?,?,?,?,?,?)""",
        (configuration_id, "activate", "system", "v0.6.1 diagnostic calibration migration activation.",
         json.dumps({"parent_version": old["version"], "prototype_defaults_unvalidated": True}), now),
    )
    connection.execute(
        "UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?",
        (f"CA{int(audit.lastrowid):06d}", int(audit.lastrowid)),
    )
def _ensure_feedback_append_only(connection: sqlite3.Connection) -> None:
    indexes = connection.execute("PRAGMA index_list(feedback_records)").fetchall()
    unique_essay = False
    for index in indexes:
        if not index[2]:
            continue
        columns = connection.execute(f"PRAGMA index_info({index[1]})").fetchall()
        if [column[2] for column in columns] == ["essay_id"]:
            unique_essay = True
            break
    if not unique_essay:
        return
    connection.executescript(
        """
        ALTER TABLE feedback_records RENAME TO feedback_records_v05_unique;
        CREATE TABLE feedback_records (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
            feedback_json TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            success_status TEXT NOT NULL,
            fallback_reason TEXT,
            prompt_version TEXT NOT NULL,
            analysis_version TEXT NOT NULL,
            system_template_hash TEXT NOT NULL DEFAULT '',
            user_template_hash TEXT NOT NULL DEFAULT '',
            rendered_prompt_hash TEXT NOT NULL DEFAULT '',
            schema_version TEXT NOT NULL DEFAULT '',
            temperature REAL NOT NULL DEFAULT 0.0,
            request_time TEXT,
            response_time TEXT,
            validation_status TEXT NOT NULL DEFAULT 'not_run',
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO feedback_records SELECT * FROM feedback_records_v05_unique;
        DROP TABLE feedback_records_v05_unique;
        CREATE INDEX IF NOT EXISTS idx_feedback_records_essay
            ON feedback_records(essay_id, feedback_id);
        """
    )


def _migration_8(connection: sqlite3.Connection) -> None:
    for column, definition in {
        "profile_version": "TEXT NOT NULL DEFAULT 'learner-profile-v0.3.0'",
        "source_submission_ids_json": "TEXT NOT NULL DEFAULT '[]'",
        "representative_submission_ids_json": "TEXT NOT NULL DEFAULT '[]'",
    }.items():
        _add_column_if_missing(connection, "learner_profile_snapshots", column, definition)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS history_evidence_registry (
            history_evidence_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_evidence_id TEXT UNIQUE,
            student_id TEXT NOT NULL REFERENCES students(student_id),
            snapshot_id TEXT,
            task_cluster_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            registry_version TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_history_evidence_student
            ON history_evidence_registry(student_id, history_evidence_row_id);
        """
    )
    active = connection.execute(
        "SELECT * FROM configuration_versions WHERE status='active' ORDER BY configuration_row_id DESC LIMIT 1"
    ).fetchone()
    if active is None or connection.execute(
        "SELECT 1 FROM configuration_versions WHERE version='config-v0.7.0' LIMIT 1"
    ).fetchone():
        return
    from app.configuration import ConfigurationPayload
    old = dict(active)
    payload = ConfigurationPayload.model_validate(json.loads(old["payload_json"])).model_dump(mode="json")
    payload.update({"active_prompt_version": "feedback-prompt-v0.7.0", "representative_draft_strategy": "final_or_latest"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    now = "2026-07-30T12:00:00+00:00"
    connection.execute(
        "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE configuration_id=?",
        (now, old["configuration_id"]),
    )
    cursor = connection.execute(
        """INSERT INTO configuration_versions(
            version,status,created_at,created_by,parent_version,payload_json,schema_version,
            change_note,validation_status,validation_errors_json,activated_at,content_hash
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("config-v0.7.0", "active", now, "system", old["version"], canonical,
         "configuration-schema-v0.7.0", "Activate conservative v0.7 learner-model defaults.",
         "passed", "[]", now, content_hash),
    )
    configuration_id = f"CFG{int(cursor.lastrowid):06d}"
    connection.execute(
        "UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?",
        (configuration_id, int(cursor.lastrowid)),
    )
    audit = connection.execute(
        """INSERT INTO configuration_audit(
            configuration_id,action,actor,reason,details_json,created_at
        ) VALUES (?,?,?,?,?,?)""",
        (configuration_id, "activate", "system", "v0.7 learner model migration activation.",
         json.dumps({"parent_version": old["version"], "prototype_defaults_unvalidated": True}), now),
    )
    connection.execute(
        "UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?",
        (f"CA{int(audit.lastrowid):06d}", int(audit.lastrowid)),
    )


def _migration_9(connection: sqlite3.Connection) -> None:
    """Add safe provider metadata and activate the preserved v0.7.1 configuration child."""
    _add_column_if_missing(
        connection, "feedback_records", "provider_status_json", "TEXT NOT NULL DEFAULT '{}'"
    )
    active = connection.execute(
        "SELECT * FROM configuration_versions WHERE status='active' ORDER BY configuration_row_id DESC LIMIT 1"
    ).fetchone()
    if active is None:
        return
    existing = connection.execute(
        "SELECT * FROM configuration_versions WHERE version='config-v0.7.1' LIMIT 1"
    ).fetchone()
    from app.configuration import ConfigurationPayload
    old = dict(active)
    now = "2026-07-30T16:00:00+00:00"
    if existing is None:
        payload = ConfigurationPayload.model_validate(json.loads(old["payload_json"])).model_dump(mode="json")
        payload["active_prompt_version"] = "feedback-prompt-v0.7.1"
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        connection.execute(
            "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE configuration_id=?",
            (now, old["configuration_id"]),
        )
        cursor = connection.execute(
            """INSERT INTO configuration_versions(
                version,status,created_at,created_by,parent_version,payload_json,schema_version,
                change_note,validation_status,validation_errors_json,activated_at,content_hash
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("config-v0.7.1", "active", now, "system", old["version"], canonical,
             "configuration-schema-v0.7.1", "Activate v0.7.1 reliability and UI defaults.",
             "passed", "[]", now, content_hash),
        )
        configuration_id = f"CFG{int(cursor.lastrowid):06d}"
        connection.execute(
            "UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?",
            (configuration_id, int(cursor.lastrowid)),
        )
    else:
        item = dict(existing)
        configuration_id = item["configuration_id"]
        connection.execute(
            "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE status='active'",
            (now,),
        )
        connection.execute(
            "UPDATE configuration_versions SET status='active', activated_at=?, deactivated_at=NULL WHERE configuration_id=?",
            (now, configuration_id),
        )
    audit = connection.execute(
        """INSERT INTO configuration_audit(
            configuration_id,action,actor,reason,details_json,created_at
        ) VALUES (?,?,?,?,?,?)""",
        (configuration_id, "activate", "system", "v0.7.1 reliability migration activation.",
         json.dumps({"parent_version": "config-v0.7.0", "prototype_defaults_unvalidated": True}), now),
    )
    connection.execute(
        "UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?",
        (f"CA{int(audit.lastrowid):06d}", int(audit.lastrowid)),
    )


def _migration_10(connection: sqlite3.Connection) -> None:
    """Add auditable CALF foundations and activate a preserved v0.8 configuration child."""
    for column, definition in {
        "writing_started_at": "TEXT", "writing_submitted_at": "TEXT",
        "active_writing_duration_seconds": "REAL", "timing_source": "TEXT NOT NULL DEFAULT 'unknown'",
        "timing_quality": "TEXT NOT NULL DEFAULT 'unavailable'",
        "unexplained_interruption": "INTEGER NOT NULL DEFAULT 0",
    }.items():
        _add_column_if_missing(connection, "essays", column, definition)
    for column, definition in {
        "construct_id": "TEXT", "subconstruct_id": "TEXT", "automation_level": "TEXT",
        "analysis_unit_version": "TEXT", "numerator_json": "TEXT NOT NULL DEFAULT 'null'",
        "denominator_json": "TEXT NOT NULL DEFAULT 'null'",
        "intermediate_values_json": "TEXT NOT NULL DEFAULT '{}'",
        "eligible_for_revision_priority": "INTEGER NOT NULL DEFAULT 0",
        "eligible_for_targeted_practice": "INTEGER NOT NULL DEFAULT 0",
    }.items():
        _add_column_if_missing(connection, "metric_results", column, definition)
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS analysis_units (
            analysis_unit_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_unit_id TEXT UNIQUE,
            submission_id INTEGER NOT NULL REFERENCES essays(essay_id),
            analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(analysis_run_id),
            unit_id TEXT NOT NULL,
            unit_version TEXT NOT NULL,
            validation_status TEXT NOT NULL,
            unit_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_analysis_units_submission_run
            ON analysis_units(submission_id, analysis_run_id, unit_id);
        CREATE TABLE IF NOT EXISTS error_annotations (
            error_annotation_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_annotation_id TEXT UNIQUE,
            submission_id INTEGER NOT NULL REFERENCES essays(essay_id),
            start_offset INTEGER NOT NULL,
            end_offset INTEGER NOT NULL,
            annotation_source TEXT NOT NULL,
            annotation_status TEXT NOT NULL,
            eligible_for_formal_accuracy INTEGER NOT NULL DEFAULT 0,
            annotation_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_error_annotations_submission
            ON error_annotations(submission_id, annotation_status, annotation_source);
    """)
    active = connection.execute(
        "SELECT * FROM configuration_versions WHERE status='active' ORDER BY configuration_row_id DESC LIMIT 1"
    ).fetchone()
    if active is None:
        return
    existing = connection.execute(
        "SELECT * FROM configuration_versions WHERE version='config-v0.8.0' LIMIT 1"
    ).fetchone()
    from app.configuration import ConfigurationPayload
    now = "2026-07-30T18:00:00+00:00"
    if existing is None:
        parent = dict(active)
        payload = ConfigurationPayload.model_validate(json.loads(parent["payload_json"])).model_dump(mode="json")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        connection.execute(
            "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE configuration_id=?",
            (now, parent["configuration_id"]),
        )
        cursor = connection.execute(
            """INSERT INTO configuration_versions(
                version,status,created_at,created_by,parent_version,payload_json,schema_version,
                change_note,validation_status,validation_errors_json,activated_at,content_hash
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("config-v0.8.0", "active", now, "system", parent["version"], canonical,
             "configuration-schema-v0.8.0", "Activate auditable CALF measurement foundations.",
             "passed", "[]", now, content_hash),
        )
        configuration_id = f"CFG{int(cursor.lastrowid):06d}"
        connection.execute(
            "UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?",
            (configuration_id, int(cursor.lastrowid)),
        )
    else:
        configuration_id = dict(existing)["configuration_id"]
        connection.execute("UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE status='active'", (now,))
        connection.execute(
            "UPDATE configuration_versions SET status='active', activated_at=?, deactivated_at=NULL WHERE configuration_id=?",
            (now, configuration_id),
        )
    cursor = connection.execute(
        """INSERT INTO configuration_audit(configuration_id,action,actor,reason,details_json,created_at)
           VALUES (?,?,?,?,?,?)""",
        (configuration_id, "activate", "system", "v0.8 CALF foundation migration activation.",
         json.dumps({"parent_version": "config-v0.7.1", "prototype_defaults_unvalidated": True}), now),
    )
    connection.execute(
        "UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?",
        (f"CA{int(cursor.lastrowid):06d}", int(cursor.lastrowid)),
    )


def _migration_11(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS human_reviews (review_id TEXT PRIMARY KEY, target_type TEXT NOT NULL, target_id TEXT NOT NULL, reviewer_id TEXT NOT NULL, decision TEXT NOT NULL, confidence TEXT NOT NULL DEFAULT 'medium', reason_code TEXT, comment TEXT NOT NULL DEFAULT '', guideline_version TEXT NOT NULL DEFAULT 'human-review-v0.1', review_status TEXT NOT NULL DEFAULT 'completed', created_at TEXT NOT NULL, updated_at TEXT, superseded_by TEXT, source_system_result_snapshot TEXT)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_hr_target ON human_reviews(target_type, target_id)")
    connection.execute("CREATE TABLE IF NOT EXISTS pii_candidates (pii_candidate_id TEXT PRIMARY KEY, submission_id INTEGER NOT NULL, category TEXT NOT NULL, start_offset INTEGER NOT NULL, end_offset INTEGER NOT NULL, matched_text TEXT NOT NULL, confidence TEXT NOT NULL DEFAULT 'medium', rule_id TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'candidate', action TEXT, reviewer_id TEXT, reviewed_at TEXT, replacement_marker TEXT)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_pii_sub ON pii_candidates(submission_id)")
    connection.execute("CREATE TABLE IF NOT EXISTS export_jobs (export_id TEXT PRIMARY KEY, filter_json TEXT NOT NULL, privacy_mode TEXT NOT NULL, formats_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'preview', created_at TEXT NOT NULL, completed_at TEXT, export_directory TEXT, file_count INTEGER NOT NULL DEFAULT 0, record_counts_json TEXT, excluded_counts_json TEXT, manifest_path TEXT)")
    active = connection.execute(
        "SELECT * FROM configuration_versions WHERE status='active' ORDER BY configuration_row_id DESC LIMIT 1"
    ).fetchone()
    if active is not None:
        existing = connection.execute(
            "SELECT * FROM configuration_versions WHERE version='config-v0.8.2' LIMIT 1"
        ).fetchone()
        from app.configuration import ConfigurationPayload
        now = "2026-07-30T20:00:00+00:00"
        if existing is None:
            parent = dict(active)
            payload = ConfigurationPayload.model_validate(json.loads(parent["payload_json"])).model_dump(mode="json")
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            connection.execute(
                "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE configuration_id=?",
                (now, parent["configuration_id"]),
            )
            cursor = connection.execute(
                """INSERT INTO configuration_versions(
                    version,status,created_at,created_by,parent_version,payload_json,schema_version,
                    change_note,validation_status,validation_errors_json,activated_at,content_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("config-v0.8.2", "active", now, "system", parent["version"], canonical,
                 "configuration-schema-v0.8.2", "Activate research data export, PII, and human review infrastructure.",
                 "passed", "[]", now, content_hash),
            )
            cfg_id = f"CFG{int(cursor.lastrowid):06d}"
            connection.execute("UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?", (cfg_id, int(cursor.lastrowid)))
        else:
            cfg_id = dict(existing)["configuration_id"]
            connection.execute("UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE status='active'", (now,))
            connection.execute("UPDATE configuration_versions SET status='active', activated_at=?, deactivated_at=NULL WHERE configuration_id=?", (now, cfg_id))
        cursor = connection.execute(
            """INSERT INTO configuration_audit(configuration_id,action,actor,reason,details_json,created_at) VALUES (?,?,?,?,?,?)""",
            (cfg_id, "activate", "system", "v0.8.2 research data infrastructure migration activation.",
             json.dumps({"parent_version": "config-v0.8.0", "prototype_defaults_unvalidated": True}), now),
        )
        connection.execute("UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?", (f"CA{int(cursor.lastrowid):06d}", int(cursor.lastrowid)))
    connection.execute("PRAGMA user_version = 11")


def _migration_12(connection: sqlite3.Connection) -> None:
        for stmt in [
            "CREATE TABLE IF NOT EXISTS practice_targets (practice_target_id TEXT PRIMARY KEY, student_id TEXT NOT NULL, source_submission_id INTEGER NOT NULL, source_diagnosis_id TEXT NOT NULL, target_code TEXT NOT NULL, target_label TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL, target_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS exercise_instances (exercise_id TEXT PRIMARY KEY, practice_target_id TEXT NOT NULL, student_id TEXT NOT NULL, exercise_type TEXT NOT NULL, created_at TEXT NOT NULL, instance_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS exercise_attempts (attempt_id TEXT PRIMARY KEY, exercise_id TEXT NOT NULL, student_id TEXT NOT NULL, attempt_number INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'submitted', created_at TEXT NOT NULL, attempt_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS practice_evaluations (evaluation_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL, practice_target_id TEXT NOT NULL, created_at TEXT NOT NULL, evaluation_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS feedback_engagement_traces (trace_id TEXT PRIMARY KEY, student_id TEXT NOT NULL, target_code TEXT NOT NULL, created_at TEXT NOT NULL, trace_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS within_task_response_candidates (response_id TEXT PRIMARY KEY, student_id TEXT NOT NULL, practice_target_id TEXT NOT NULL, created_at TEXT NOT NULL, response_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS transfer_evidence_candidates (transfer_evidence_id TEXT PRIMARY KEY, student_id TEXT NOT NULL, practice_target_id TEXT NOT NULL, created_at TEXT NOT NULL, transfer_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS practice_state_snapshots (practice_state_snapshot_id TEXT PRIMARY KEY, student_id TEXT NOT NULL, created_at TEXT NOT NULL, snapshot_json TEXT NOT NULL)",
        ]:
            connection.execute(stmt)
        active = connection.execute("SELECT * FROM configuration_versions WHERE status='active' ORDER BY configuration_row_id DESC LIMIT 1").fetchone()
        if active is not None:
            existing = connection.execute("SELECT * FROM configuration_versions WHERE version='config-v0.9.0' LIMIT 1").fetchone()
            from app.configuration import ConfigurationPayload
            now = "2026-07-30T22:00:00+00:00"
            if existing is None:
                parent = dict(active)
                payload = ConfigurationPayload.model_validate(json.loads(parent["payload_json"])).model_dump(mode="json")
                canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                connection.execute("UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE configuration_id=?", (now, parent["configuration_id"]))
                cursor = connection.execute("INSERT INTO configuration_versions(version,status,created_at,created_by,parent_version,payload_json,schema_version,change_note,validation_status,validation_errors_json,activated_at,content_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", ("config-v0.9.0", "active", now, "system", parent["version"], canonical, "configuration-schema-v0.9.0", "Activate feedback practice and transfer evidence foundation.", "passed", "[]", now, content_hash))
                cfg_id = f"CFG{int(cursor.lastrowid):06d}"
                connection.execute("UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?", (cfg_id, int(cursor.lastrowid)))
            else:
                cfg_id = dict(existing)["configuration_id"]
                connection.execute("UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE status='active'", (now,))
                connection.execute("UPDATE configuration_versions SET status='active', activated_at=?, deactivated_at=NULL WHERE configuration_id=?", (now, cfg_id))
            cursor = connection.execute("INSERT INTO configuration_audit(configuration_id,action,actor,reason,details_json,created_at) VALUES (?,?,?,?,?,?)", (cfg_id, "activate", "system", "v0.9 practice infrastructure migration activation.", json.dumps({"parent_version": "config-v0.8.2"}), now))
            connection.execute("UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?", (f"CA{int(cursor.lastrowid):06d}", int(cursor.lastrowid)))
        connection.execute("PRAGMA user_version = 12")


def _migration_13(connection: sqlite3.Connection) -> None:
    """Additive one-active-priority-key uniqueness (v0.9.7-B WU3).

    Enforces at most one ACTIVE practice target per
    (student_id, source_submission_id, source_priority_id). The key's third
    component lives inside target_json (WU1 audit finding: provenance is
    JSON-only), so the partial unique index reads it via json_extract;
    existing rows are preserved; legacy targets without a priority reference
    (NULL source_priority_id) are exempt. Non-destructive: rollback only
    drops the index.
    """
    connection.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS ux_practice_targets_active_priority_key
        ON practice_targets(student_id, source_submission_id,
            json_extract(target_json, '$.source_priority_id'))
        WHERE status = 'active'
            AND json_extract(target_json, '$.source_priority_id') IS NOT NULL"""
    )
    connection.execute("PRAGMA user_version = 13")


def _migration_14(connection: sqlite3.Connection) -> None:
    """Wave-2 additive persistence: L2 revision loop + longitudinal learner model.

    Goal PDW2-A-CORE-PERSISTENCE, amended by the F-5 repair
    (PDW2-WU2-INT-INTEGRATION-GATE-RE-GATE__REPAIR): the migration is still
    unpromoted, so the amendment extends the SAME lane in place. Additive and
    non-destructive: creates only new tables/columns and indexes; no existing
    table DDL is altered; the deferred ``essays.domain`` discriminator and
    D-09 lanes are NOT touched. All new columns are DEFAULT-covered so
    existing write paths remain valid.

    Entities (minimum qualified set):
    - writing_tasks: task/context metadata for the L2 revision loop. F-5
      amendment: two-level task contract -- ``writing_context`` (the L2
      context id; authoritative for L2-shaped tasks) plus
      ``classification_json``/``status``; the legacy ``genre`` column remains
      for CORE-origin compatibility rows.
    - submission_revisions: revision relationship records with ancestry,
      timestamps, task-context, analysis, and feedback links. Existing
      revision_groups/revision_snapshots remain authoritative for grouping
      and analysis payloads; this table adds the qualified relationship
      contract (explicit ancestry chain + task/analysis/feedback link refs)
      without duplicating their payloads.
    - submission_versions: F-5 amendment -- the L2 RevisionLoopRepository
      version family (V1/V2/... with ancestry, timestamps, task-context
      snapshot, analysis/feedback links, corpus routing, reanalysis events).
      Append-only: a revision always creates a NEW row; prior versions are
      preserved as evidence.
    - revision_observations: F-5 amendment -- bounded observational
      comparisons between versions (what changed, feedback areas
      appears_addressed/appears_remaining, new observations, apparent
      independent corrections; no intent inference).
    - priority_plans: F-5 amendment -- small actionable revision plans
      (local + global observations, historical feedback, observation-only
      claims).
    - scaffold_events: F-5 amendment -- recorded scaffold requests (7-level
      SCAFFOLD FIRST; learner/learning-item/plan-item linkage).
    - learning_observations: longitudinal learner observations (type,
      evidence refs, task/context, occurrence/recency, revision response).
    - learning_items: learner-owned items (originating evidence, feedback,
      revision history, task/context, status). F-5 amendment: LearningItem
      v1 contract fields -- ``category``, ``task_context``, ``limitations``,
      ``no_fsrs_note``, ``no_practice_note``; the legacy ``context`` column
      remains for CORE-origin rows.

    Rollback 14->13 is a logical ledger-only rollback (see ``rollback``);
    tables and data are preserved and re-apply is idempotent.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS writing_tasks (
            task_id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL REFERENCES students(student_id),
            writing_prompt TEXT NOT NULL,
            genre TEXT NOT NULL DEFAULT 'argumentative essay',
            writing_context TEXT NOT NULL DEFAULT 'other',
            task_type TEXT NOT NULL DEFAULT 'independent_writing',
            modality TEXT NOT NULL DEFAULT 'written',
            reference_group_id TEXT,
            classification_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            limitations_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_writing_tasks_student
            ON writing_tasks(student_id, created_at);
        CREATE TABLE IF NOT EXISTS submission_revisions (
            revision_link_id TEXT PRIMARY KEY,
            revision_group_id TEXT NOT NULL
                REFERENCES revision_groups(revision_group_id),
            source_submission_id INTEGER NOT NULL REFERENCES essays(essay_id),
            target_submission_id INTEGER NOT NULL REFERENCES essays(essay_id),
            ancestry_json TEXT NOT NULL DEFAULT '[]',
            task_id TEXT REFERENCES writing_tasks(task_id),
            analysis_run_id TEXT REFERENCES analysis_runs(analysis_run_id),
            feedback_record_id INTEGER REFERENCES feedback_records(feedback_id),
            revision_sequence INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            limitations_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_submission_revisions_group_target
            ON submission_revisions(revision_group_id, target_submission_id);
        CREATE INDEX IF NOT EXISTS idx_submission_revisions_group
            ON submission_revisions(revision_group_id, revision_sequence);
        CREATE INDEX IF NOT EXISTS idx_submission_revisions_target
            ON submission_revisions(target_submission_id);
        CREATE INDEX IF NOT EXISTS idx_submission_revisions_task
            ON submission_revisions(task_id);
        CREATE TABLE IF NOT EXISTS submission_versions (
            task_id TEXT NOT NULL REFERENCES writing_tasks(task_id),
            submission_id INTEGER NOT NULL REFERENCES essays(essay_id),
            version_number INTEGER NOT NULL,
            revision_of_submission_id INTEGER,
            ancestry_json TEXT NOT NULL DEFAULT '[]',
            submitted_at TEXT NOT NULL,
            task_context_json TEXT NOT NULL DEFAULT '{}',
            essay_text_hash TEXT NOT NULL,
            draft_stage TEXT NOT NULL DEFAULT 'first draft',
            analysis_run_id TEXT,
            analysis_version TEXT,
            feedback_record_id INTEGER,
            revision_group_id TEXT,
            revision_snapshot_id TEXT,
            corpus_routing_json TEXT,
            reanalysis_events_json TEXT NOT NULL DEFAULT '[]',
            limitations_json TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY (task_id, submission_id)
        );
        CREATE INDEX IF NOT EXISTS idx_submission_versions_submission
            ON submission_versions(submission_id);
        CREATE INDEX IF NOT EXISTS idx_submission_versions_task_version
            ON submission_versions(task_id, version_number);
        CREATE TABLE IF NOT EXISTS revision_observations (
            observation_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES writing_tasks(task_id),
            source_submission_id INTEGER NOT NULL,
            target_submission_id INTEGER NOT NULL,
            observed_at TEXT NOT NULL,
            what_changed_json TEXT NOT NULL DEFAULT '{}',
            feedback_areas_json TEXT NOT NULL DEFAULT '[]',
            new_observations_json TEXT NOT NULL DEFAULT '[]',
            apparent_independent_corrections_json TEXT NOT NULL DEFAULT '[]',
            no_intent_inference TEXT NOT NULL,
            limitations_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_revision_observations_task
            ON revision_observations(task_id, observed_at);
        CREATE TABLE IF NOT EXISTS priority_plans (
            plan_id TEXT PRIMARY KEY,
            learner_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            submission_id INTEGER NOT NULL,
            generated_at TEXT NOT NULL,
            items_json TEXT NOT NULL DEFAULT '[]',
            history_state TEXT NOT NULL DEFAULT 'insufficient_history',
            history_reasons_json TEXT NOT NULL DEFAULT '[]',
            local_observations_json TEXT NOT NULL DEFAULT '[]',
            global_observations_json TEXT NOT NULL DEFAULT '[]',
            historical_feedback_json TEXT NOT NULL DEFAULT '[]',
            limitations_json TEXT NOT NULL DEFAULT '[]',
            claims_status TEXT NOT NULL DEFAULT 'observation_only'
        );
        CREATE INDEX IF NOT EXISTS idx_priority_plans_learner
            ON priority_plans(learner_id, generated_at);
        CREATE TABLE IF NOT EXISTS scaffold_events (
            scaffold_event_id TEXT PRIMARY KEY,
            learner_id TEXT NOT NULL,
            learning_item_id TEXT,
            plan_item_id TEXT,
            category TEXT NOT NULL,
            level INTEGER NOT NULL,
            requested_at TEXT NOT NULL,
            default_first INTEGER NOT NULL DEFAULT 0,
            limitations_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_scaffold_events_learner
            ON scaffold_events(learner_id, learning_item_id, requested_at);
        CREATE TABLE IF NOT EXISTS learning_observations (
            observation_id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL REFERENCES students(student_id),
            observation_type TEXT NOT NULL DEFAULT 'difficulty',
            evidence_refs_json TEXT NOT NULL DEFAULT '[]',
            task_id TEXT REFERENCES writing_tasks(task_id),
            context_json TEXT NOT NULL DEFAULT '{}',
            occurrence_count INTEGER NOT NULL DEFAULT 1,
            first_observed_at TEXT NOT NULL,
            last_observed_at TEXT NOT NULL,
            recency TEXT NOT NULL DEFAULT 'unknown',
            revision_response_json TEXT NOT NULL DEFAULT '{}',
            limitations_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_learning_observations_student
            ON learning_observations(student_id, observation_type, last_observed_at);
        CREATE INDEX IF NOT EXISTS idx_learning_observations_task
            ON learning_observations(task_id);
        CREATE TABLE IF NOT EXISTS learning_items (
            learning_item_id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL REFERENCES students(student_id),
            originating_evidence_json TEXT NOT NULL DEFAULT '{}',
            feedback_reference TEXT,
            revision_history_json TEXT NOT NULL DEFAULT '[]',
            task_id TEXT REFERENCES writing_tasks(task_id),
            context_json TEXT NOT NULL DEFAULT '{}',
            category TEXT NOT NULL DEFAULT 'unclassified',
            task_context_json TEXT NOT NULL DEFAULT '{}',
            no_fsrs_note TEXT NOT NULL DEFAULT 'no FSRS scheduling or spaced-repetition state is stored in LearningItem v1',
            no_practice_note TEXT NOT NULL DEFAULT 'no practice or tutor expansion is attached to LearningItem v1',
            limitations_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'proposed',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_learning_items_student
            ON learning_items(student_id, status, updated_at);
        CREATE INDEX IF NOT EXISTS idx_learning_items_task
            ON learning_items(task_id);
        """
    )
    connection.execute("PRAGMA user_version = 14")


MIGRATIONS: dict[int, tuple[str, Callable[[sqlite3.Connection], None]]] = {
    1: ("preserve_v0_1_1_schema", _migration_1),
    2: ("cloud_ready_repository_indexes", _migration_2),
    3: ("longitudinal_profile_snapshots", _migration_3),
    4: ("versioned_nlp_analysis_runs", _migration_4),
    5: ("revision_relationships_and_snapshots", _migration_5),
    6: ("versioned_non_sensitive_configuration", _migration_6),
    7: ("diagnostic_calibration_and_metric_confidence", _migration_7),
    8: ("learner_model_v2_and_history_evidence", _migration_8),
    9: ("longitudinal_reliability_and_provider_status", _migration_9),
    10: ("calf_measurement_foundation", _migration_10),
    11: ("research_data_infrastructure", _migration_11),
    12: ("practice_and_transfer_foundation", _migration_12),
    13: ("practice_target_priority_key_uniqueness", _migration_13),
    14: ("wave2_revision_loop_and_learner_model", _migration_14),
}


def upgrade(connection: sqlite3.Connection) -> int:
    current = int(connection.execute("PRAGMA user_version").fetchone()[0])
    for version in range(current + 1, LATEST_MIGRATION_VERSION + 1):
        name, migration = MIGRATIONS[version]
        with connection:
            migration(connection)
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
                (version, name),
            )
            connection.execute(f"PRAGMA user_version = {version}")
    if int(connection.execute("PRAGMA user_version").fetchone()[0]) >= 6:
        with connection:
            _ensure_feedback_append_only(connection)
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def rollback(connection: sqlite3.Connection, target_version: int) -> int:
    """Logically roll the latest additive version back one step without deleting data."""
    current = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if current == target_version:
        return current
    if (current, target_version) not in {(14, 13), (13, 12), (12, 11), (11, 10), (10, 9), (9, 8)}:
        raise ValueError("Only non-destructive one-step rollback is supported.")
    with connection:
        if current == 14:
            # Logical rollback: migration 14 only added tables/indexes, so the
            # rollback is ledger-only; tables and data are preserved and
            # re-apply (CREATE IF NOT EXISTS) is idempotent.
            connection.execute("DELETE FROM schema_migrations WHERE version=14")
        elif current == 13:
            connection.execute("DROP INDEX IF EXISTS ux_practice_targets_active_priority_key")
        else:
            expected = "config-v0.9.0" if current == 12 else ("config-v0.8.2" if current == 11 else ("config-v0.8.0" if current == 10 else "config-v0.7.1"))
            active = connection.execute(
                "SELECT * FROM configuration_versions WHERE status='active' AND version=?", (expected,)
            ).fetchone()
            if active:
                item = dict(active)
                parent = connection.execute(
                    "SELECT * FROM configuration_versions WHERE version=?", (item["parent_version"],)
                ).fetchone()
                if parent is None:
                    raise RuntimeError("config-v0.7.1 parent is unavailable; rollback was not applied.")
                now = "2026-07-30T18:00:01+00:00" if current == 10 else "2026-07-30T16:00:01+00:00"
                connection.execute(
                    "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE configuration_id=?",
                    (now, item["configuration_id"]),
                )
                connection.execute(
                    "UPDATE configuration_versions SET status='active', activated_at=?, deactivated_at=NULL WHERE configuration_id=?",
                    (now, dict(parent)["configuration_id"]),
                )
        connection.execute("DELETE FROM schema_migrations WHERE version=?", (current,))
        connection.execute(f"PRAGMA user_version = {target_version}")
    return target_version
