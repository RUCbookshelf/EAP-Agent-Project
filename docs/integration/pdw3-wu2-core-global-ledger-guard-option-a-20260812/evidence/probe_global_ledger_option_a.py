"""Option-A global integer ledger probe (PDW3-WU2-CORE-GLOBAL-LEDGER-
GUARD-OPTION-A-20260812).

Runs the REAL migration functions against temporary SQLite files
(auto-cleaned) and prints:

- the single global integer ledger identity at 15;
- fresh DB: upgrade -> 15, exactly one schema_migrations row at 15,
  the three CORE review/scheduling table families;
- v14-era DB upgrade: Wave-2 rows preserved and the three families added;
- non-destructive rollback 15->14 and idempotent re-apply;
- the CORE-owned consumer seam (constants + guard + single runner).

No product file, database, or Program Control artifact is written.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from app.database import LATEST_MIGRATION_VERSION, rollback, upgrade
from app.database.migrations import (
    GLOBAL_MIGRATION_LEDGER_OWNER,
    GLOBAL_MIGRATION_LEDGER_VERSION_15,
    GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME,
    MIGRATIONS,
    assert_global_migration_15_identity,
)
from app.version import PLATFORM_DATABASE_MIGRATION_VERSION

REVIEW_TABLES = {
    "practice_activities",
    "review_events",
    "learning_item_scheduler_states",
}


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def _upgrade_to(connection: sqlite3.Connection, target: int) -> None:
    for version in range(1, target + 1):
        name, migration = MIGRATIONS[version]
        with connection:
            migration(connection)
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER"
                " PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL"
                " DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, name)"
                " VALUES (?, ?)",
                (version, name),
            )
            connection.execute(f"PRAGMA user_version = {version}")


def main() -> None:
    print(f"LATEST_MIGRATION_VERSION={LATEST_MIGRATION_VERSION}")
    print(
        "PLATFORM_DATABASE_MIGRATION_VERSION="
        f"{PLATFORM_DATABASE_MIGRATION_VERSION}"
    )
    print(f"GLOBAL_MIGRATION_LEDGER_OWNER={GLOBAL_MIGRATION_LEDGER_OWNER}")
    print(
        "GLOBAL_MIGRATION_LEDGER_VERSION_15="
        f"{GLOBAL_MIGRATION_LEDGER_VERSION_15}"
    )
    print(
        "GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME="
        f"{GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME}"
    )
    print(f"MIGRATIONS[15]={MIGRATIONS[15]}")
    print(
        "assert_global_migration_15_identity()="
        f"{assert_global_migration_15_identity()}"
    )

    with tempfile.TemporaryDirectory(
        prefix="codex-global-ledger-option-a-"
    ) as tmp:
        root = Path(tmp)

        # Fresh database.
        connection = sqlite3.connect(root / "fresh.db")
        connection.row_factory = sqlite3.Row
        try:
            result = upgrade(connection)
            print(f"fresh upgrade()={result}")
            print(
                "fresh PRAGMA user_version="
                f"{connection.execute('PRAGMA user_version').fetchone()[0]}"
            )
            rows = connection.execute(
                "SELECT version, name FROM schema_migrations WHERE version=15"
            ).fetchall()
            print(f"fresh schema_migrations rows at 15={[tuple(r) for r in rows]}")
            missing = REVIEW_TABLES - _tables(connection)
            print(
                "fresh review table families present="
                f"{not missing} missing={sorted(missing)}"
            )
        finally:
            connection.close()

        # Genuine migration-14-era database with Wave-2 rows.
        connection = sqlite3.connect(root / "v14-era.db")
        connection.row_factory = sqlite3.Row
        try:
            _upgrade_to(connection, 14)
            connection.execute(
                "INSERT INTO students(student_id, created_at, is_synthetic)"
                " VALUES ('S1', '2026-01-01T00:00:00+00:00', 0)"
            )
            connection.execute(
                "INSERT INTO writing_tasks(task_id, student_id, writing_prompt,"
                " writing_context, task_type, created_at) VALUES"
                " ('WT-V14-001', 'S1', 'Should cities add more parks?',"
                " 'cet6', 'argumentative', '2026-01-01T00:00:00+00:00')"
            )
            connection.execute(
                "INSERT INTO learning_items(learning_item_id, student_id,"
                " originating_evidence_json, task_id, category, status,"
                " created_at, updated_at) VALUES"
                " ('LI-V14-001', 'S1',"
                " '{\"source\":\"priority_plan\",\"kind\":\"l2\"}',"
                " 'WT-V14-001', 'grammar', 'proposed',"
                " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
            )
            connection.commit()
            print(
                "v14-era PRAGMA user_version before upgrade="
                f"{connection.execute('PRAGMA user_version').fetchone()[0]}"
            )
            print(
                "v14-era review tables before upgrade="
                f"{sorted(REVIEW_TABLES & _tables(connection))}"
            )
            assert upgrade(connection) == 15
            print(
                "v14-era upgrade()=15; PRAGMA user_version="
                f"{connection.execute('PRAGMA user_version').fetchone()[0]}"
            )
            task = connection.execute(
                "SELECT task_id, student_id FROM writing_tasks"
                " WHERE task_id='WT-V14-001'"
            ).fetchone()
            item = connection.execute(
                "SELECT learning_item_id FROM learning_items"
                " WHERE learning_item_id='LI-V14-001'"
            ).fetchone()
            print(
                "v14-era Wave-2 rows preserved:"
                f" task={task is not None} item={item is not None}"
            )
            print(
                "v14-era review table families present="
                f"{REVIEW_TABLES <= _tables(connection)}"
            )
            assert rollback(connection, 14) == 14
            print(
                "rollback 15->14="
                f"{connection.execute('PRAGMA user_version').fetchone()[0]}"
                "; review tables preserved="
                f"{REVIEW_TABLES <= _tables(connection)}"
                "; ledger rows at 15="
                f"{connection.execute('SELECT COUNT(*) FROM schema_migrations WHERE version=15').fetchone()[0]}"
            )
            assert upgrade(connection) == 15
            print(
                "re-apply upgrade()=15; ledger rows at 15="
                f"{connection.execute('SELECT COUNT(*) FROM schema_migrations WHERE version=15').fetchone()[0]}"
            )
        finally:
            connection.close()

    print("PROBE_OK")


if __name__ == "__main__":
    main()
