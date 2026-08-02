from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.configuration import ConfigurationCreate, ConfigurationPayload, ConfigurationVersion, configuration_hash
from app.infrastructure.sqlite.connection import SQLiteConnectionManager


class SQLiteConfigurationRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    @staticmethod
    def _configuration_from_row(row: sqlite3.Row) -> ConfigurationVersion:
        item = dict(row)
        return ConfigurationVersion(
            configuration_id=item["configuration_id"], version=item["version"], status=item["status"],
            created_at=item["created_at"], created_by=item["created_by"], parent_version=item["parent_version"],
            payload=ConfigurationPayload.model_validate_json(item["payload_json"]),
            schema_version=item["schema_version"], change_note=item["change_note"],
            validation_status=item["validation_status"],
            validation_errors=json.loads(item["validation_errors_json"]),
            activated_at=item["activated_at"], deactivated_at=item["deactivated_at"],
            content_hash=item["content_hash"],
        )

    def list_configurations(self) -> list[ConfigurationVersion]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM configuration_versions ORDER BY configuration_row_id"
            ).fetchall()
        return [self._configuration_from_row(row) for row in rows]

    def get_configuration(self, configuration_id_or_version: str) -> ConfigurationVersion | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM configuration_versions WHERE configuration_id=? OR version=?",
                (configuration_id_or_version, configuration_id_or_version),
            ).fetchone()
        return self._configuration_from_row(row) if row else None

    def get_active_configuration(self) -> ConfigurationVersion:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM configuration_versions WHERE status='active'"
            ).fetchone()
        if row is None:
            raise RuntimeError("No active configuration exists.")
        return self._configuration_from_row(row)

    def create_configuration(self, request: ConfigurationCreate, parent_version: str | None) -> ConfigurationVersion:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection_manager.connect() as connection:
            number = int(connection.execute(
                "SELECT COALESCE(MAX(configuration_row_id),0)+1 FROM configuration_versions"
            ).fetchone()[0])
            existing = {str(row[0]) for row in connection.execute("SELECT version FROM configuration_versions")}
            active = self.get_active_configuration()
            family = "config-v0.8." if active.version.startswith("config-v0.8.") else "config-v0.7."
            suffix = max(
                [int(value.rsplit(".", 1)[1]) for value in existing if value.startswith(family)],
                default=-1,
            ) + 1
            version = f"{family}{suffix}"
            cursor = connection.execute(
                """INSERT INTO configuration_versions(
                    version,status,created_at,created_by,parent_version,payload_json,schema_version,
                    change_note,validation_status,validation_errors_json,content_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (version, "draft", now, request.created_by, parent_version,
                request.payload.model_dump_json(), "configuration-schema-v0.8.0", request.change_note,
                 "not_validated", "[]", configuration_hash(request.payload)),
            )
            configuration_id = f"CFG{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE configuration_versions SET configuration_id=? WHERE configuration_row_id=?",
                (configuration_id, int(cursor.lastrowid)),
            )
            self._insert_configuration_audit(
                connection, configuration_id, "create", request.created_by, request.change_note,
                {"parent_version": parent_version}, now,
            )
        result = self.get_configuration(configuration_id)
        assert result is not None
        return result

    def set_configuration_validation(self, configuration_id: str, *, passed: bool,
                                     errors: list[str], actor: str) -> ConfigurationVersion:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection_manager.connect() as connection:
            updated = connection.execute(
                """UPDATE configuration_versions SET status=?, validation_status=?, validation_errors_json=?
                   WHERE configuration_id=? AND status IN ('draft','validated')""",
                ("validated" if passed else "draft", "passed" if passed else "failed",
                 json.dumps(errors), configuration_id),
            ).rowcount
            if not updated:
                raise ValueError("Only draft or validated configurations can be validated.")
            self._insert_configuration_audit(
                connection, configuration_id, "validate", actor,
                "Validation passed." if passed else "Validation failed.", {"errors": errors}, now,
            )
        result = self.get_configuration(configuration_id)
        assert result is not None
        return result

    def activate_configuration(self, configuration_id: str, *, actor: str, reason: str,
                               action: str = "activate") -> ConfigurationVersion:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection_manager.connect() as connection:
            target = connection.execute(
                "SELECT * FROM configuration_versions WHERE configuration_id=?", (configuration_id,)
            ).fetchone()
            if target is None:
                raise LookupError("Configuration not found.")
            if target["validation_status"] != "passed":
                raise ValueError("Invalid or unvalidated configuration cannot be activated.")
            connection.execute(
                "UPDATE configuration_versions SET status='inactive', deactivated_at=? WHERE status='active' AND configuration_id<>?",
                (now, configuration_id),
            )
            connection.execute(
                "UPDATE configuration_versions SET status='active', activated_at=?, deactivated_at=NULL WHERE configuration_id=?",
                (now, configuration_id),
            )
            self._insert_configuration_audit(
                connection, configuration_id, action, actor, reason, {}, now,
            )
        result = self.get_configuration(configuration_id)
        assert result is not None
        return result

    def list_configuration_audit(self, configuration_id: str | None = None) -> list[dict[str, Any]]:
        with self._connection_manager.connect() as connection:
            if configuration_id:
                rows = connection.execute(
                    "SELECT * FROM configuration_audit WHERE configuration_id=? ORDER BY audit_row_id",
                    (configuration_id,),
                ).fetchall()
            else:
                rows = connection.execute("SELECT * FROM configuration_audit ORDER BY audit_row_id").fetchall()
        return [{**dict(row), "details": json.loads(row["details_json"])} for row in rows]

    @staticmethod
    def _insert_configuration_audit(connection: sqlite3.Connection, configuration_id: str,
                                    action: str, actor: str, reason: str,
                                    details: dict[str, Any], created_at: str) -> None:
        cursor = connection.execute(
            """INSERT INTO configuration_audit(
                configuration_id,action,actor,reason,details_json,created_at
            ) VALUES (?,?,?,?,?,?)""",
            (configuration_id, action, actor, reason, json.dumps(details), created_at),
        )
        connection.execute(
            "UPDATE configuration_audit SET audit_id=? WHERE audit_row_id=?",
            (f"CA{int(cursor.lastrowid):06d}", int(cursor.lastrowid)),
        )
