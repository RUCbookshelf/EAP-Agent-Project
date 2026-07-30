from __future__ import annotations

import sqlite3
import hashlib
import json
from collections.abc import Callable


LATEST_MIGRATION_VERSION = 9


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
    """Logically roll migration 9 back without deleting its additive data or column."""
    current = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if current == target_version:
        return current
    if current != 9 or target_version != 8:
        raise ValueError("Only the non-destructive v0.7.1 migration 9 -> 8 rollback is supported.")
    with connection:
        active = connection.execute(
            "SELECT * FROM configuration_versions WHERE status='active' AND version='config-v0.7.1'"
        ).fetchone()
        if active:
            item = dict(active)
            parent = connection.execute(
                "SELECT * FROM configuration_versions WHERE version=?", (item["parent_version"],)
            ).fetchone()
            if parent is None:
                raise RuntimeError("config-v0.7.1 parent is unavailable; rollback was not applied.")
            now = "2026-07-30T16:00:01+00:00"
            connection.execute(
                "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE configuration_id=?",
                (now, item["configuration_id"]),
            )
            connection.execute(
                "UPDATE configuration_versions SET status='active', activated_at=?, deactivated_at=NULL WHERE configuration_id=?",
                (now, dict(parent)["configuration_id"]),
            )
        connection.execute("DELETE FROM schema_migrations WHERE version=9")
        connection.execute("PRAGMA user_version = 8")
    return 8
