"""Independent Option-A ledger probe (LEARNER composed path).

Goal PDW3-WU2-LEARNER-MIGRATION16-PINS-OPTION-A-20260812.

Proves, on a REAL sqlite3 file outside product data:
  1. Fresh upgrade() lands at LATEST=16 with exact ledger rows 14/15/16.
  2. A genuine v14-era database (real migrations 1..14 only, Wave-2 rows,
     user_version=14) upgrades 14->15->16 with data preserved.
  3. Logical rollback 16->15->14 removes exactly the 15/16 ledger rows while
     CORE review tables and the acknowledgement table/data are preserved.
  4. Idempotent re-apply restores exactly one row at 15 and one at 16.
  5. The composed-path guards assert_global_migration_15_identity() /
     assert_global_migration_16_identity() return (15, ...) / (16, ...).

Run from the learner worktree root:
  .venv/Scripts/python.exe docs/integration/pdw3-wu2-learner-migration16-pins-option-a-20260812/evidence/probe_migration16_option_a.py
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

from app.database import LATEST_MIGRATION_VERSION, rollback, upgrade
from app.database.migrations import MIGRATIONS
from app.database.migrations import (
    assert_global_migration_15_identity,
    assert_global_migration_16_identity,
)
from app.version import PLATFORM_DATABASE_MIGRATION_VERSION


M15 = "review_scheduling_foundation"
M16 = "learner_acknowledgement_persistence"
CORE_REVIEW_TABLES = (
    "practice_activities",
    "review_events",
    "learning_item_scheduler_states",
)


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def _ledger(connection: sqlite3.Connection, version: int) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            "SELECT name FROM schema_migrations WHERE version=?", (version,)
        )
    ]


def _seed_v14(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO students(student_id, created_at, is_synthetic)"
        " VALUES ('S1', '2026-01-01T00:00:00+00:00', 0)"
    )
    connection.execute(
        "INSERT INTO essays(student_id, writing_prompt, genre, draft_stage,"
        " timed, tool_use, essay_text, submitted_at)"
        " VALUES ('S1', 'Prompt A', 'argumentative essay', 'first draft',"
        " 0, 'none', 'Text one.', '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO writing_tasks(task_id, student_id, writing_prompt,"
        " created_at) VALUES ('WT000001', 'S1', 'Prompt A',"
        " '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO learning_items(learning_item_id, student_id,"
        " created_at, updated_at) VALUES ('LI000001', 'S1',"
        " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
    )


def _seed_ack(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO learner_acknowledgements("
        " acknowledgement_id, learner_id, source_kind,"
        " source_evidence_ids_json, evidence_status, epistemic_status,"
        " outcome_claim, provenance_json, record_version,"
        " acknowledgement_text, consent_json, recorded_at)"
        " VALUES ('ACK-PROBE-1', 'S1', 'observed_evidence', '[]',"
        " 'verified', 'observed_descriptive', 'none', '{}',"
        " 'acknowledgement-record-v0.1.0', 'Descriptive text.', '{}',"
        " '2026-08-12T00:00:00+00:00')"
    )


def main() -> int:
    work_dir = Path(tempfile.mkdtemp(prefix="mig16-option-a-probe-"))
    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {label}" + (f" -- {detail}" if detail else ""))
        if not condition:
            failures.append(label)

    # 0. Composed constants and guards
    check(
        "composed latest pins are 16",
        LATEST_MIGRATION_VERSION == 16
        and PLATFORM_DATABASE_MIGRATION_VERSION == 16,
        f"LATEST={LATEST_MIGRATION_VERSION} "
        f"PLATFORM={PLATFORM_DATABASE_MIGRATION_VERSION}",
    )
    check(
        "guard 15 returns CORE identity",
        assert_global_migration_15_identity() == (15, M15),
    )
    check(
        "guard 16 returns LEARNER identity",
        assert_global_migration_16_identity() == (16, M16),
    )

    # 1. Fresh upgrade -> 16 with exact ledger rows
    fresh = work_dir / "fresh16.db"
    connection = sqlite3.connect(fresh)
    connection.row_factory = sqlite3.Row
    result = upgrade(connection)
    check("fresh upgrade() == 16", result == 16, f"upgrade()={result}")
    check("fresh user_version == 16", connection.execute("PRAGMA user_version").fetchone()[0] == 16)
    check(
        "fresh ledger 14/15/16 identities exact",
        _ledger(connection, 14) == ["wave2_revision_loop_and_learner_model"]
        and _ledger(connection, 15) == [M15]
        and _ledger(connection, 16) == [M16],
        f"ledger14={_ledger(connection, 14)} ledger15={_ledger(connection, 15)} "
        f"ledger16={_ledger(connection, 16)}",
    )
    check(
        "fresh tables include CORE-15 families and learner_acknowledgements",
        set(CORE_REVIEW_TABLES) <= _tables(connection)
        and "learner_acknowledgements" in _tables(connection),
    )
    connection.close()

    # 2. Genuine v14-era database: real migrations 1..14, Wave-2 rows
    v14 = work_dir / "v14era.db"
    connection = sqlite3.connect(v14)
    connection.row_factory = sqlite3.Row
    for version in range(1, 15):
        MIGRATIONS[version][1](connection)
        connection.execute(f"PRAGMA user_version={version}")
    check("v14-era built at user_version=14", connection.execute("PRAGMA user_version").fetchone()[0] == 14)
    check(
        "v14-era has no review_events/learner_acknowledgements",
        "review_events" not in _tables(connection)
        and "learner_acknowledgements" not in _tables(connection),
    )
    _seed_v14(connection)
    connection.commit()
    result = upgrade(connection)
    check("v14-era upgrade() == 16", result == 16, f"upgrade()={result}")
    check(
        "v14-era ledger rows 15/16 exact after upgrade",
        _ledger(connection, 15) == [M15] and _ledger(connection, 16) == [M16],
    )
    check(
        "v14-era Wave-2 rows preserved",
        connection.execute("SELECT task_id FROM writing_tasks WHERE task_id='WT000001'").fetchone() is not None
        and connection.execute("SELECT learning_item_id FROM learning_items WHERE learning_item_id='LI000001'").fetchone() is not None,
    )
    connection.close()

    # 3. Rollback 16 -> 15 -> 14 (ledger-only) on the v14-era database
    connection = sqlite3.connect(v14)
    connection.row_factory = sqlite3.Row
    _seed_ack(connection)
    connection.commit()
    check("rollback(16->15) == 15", rollback(connection, 15) == 15)
    check("user_version == 15 after one step", connection.execute("PRAGMA user_version").fetchone()[0] == 15)
    check(
        "ledger16 empty, ledger15 exact after rollback to 15",
        _ledger(connection, 15) == [M15] and _ledger(connection, 16) == [],
    )
    check(
        "CORE tables + acknowledgement data preserved at 15",
        set(CORE_REVIEW_TABLES) <= _tables(connection)
        and connection.execute("SELECT acknowledgement_id FROM learner_acknowledgements").fetchone()[0] == "ACK-PROBE-1",
    )
    check("rollback(15->14) == 14", rollback(connection, 14) == 14)
    check("user_version == 14 after two steps", connection.execute("PRAGMA user_version").fetchone()[0] == 14)
    check(
        "ledger15/16 empty at 14; tables and ack data preserved",
        _ledger(connection, 15) == [] and _ledger(connection, 16) == []
        and set(CORE_REVIEW_TABLES) <= _tables(connection)
        and connection.execute("SELECT acknowledgement_id FROM learner_acknowledgements").fetchone()[0] == "ACK-PROBE-1",
    )
    connection.close()

    # 4. Idempotent re-apply 14 -> 15 -> 16
    connection = sqlite3.connect(v14)
    connection.row_factory = sqlite3.Row
    result = upgrade(connection)
    check("re-apply upgrade() == 16", result == 16, f"upgrade()={result}")
    check(
        "re-apply restores exactly one row at 15 and one at 16",
        _ledger(connection, 15) == [M15] and _ledger(connection, 16) == [M16],
    )
    check(
        "re-apply preserves acknowledgement data",
        connection.execute("SELECT acknowledgement_id FROM learner_acknowledgements").fetchone()[0] == "ACK-PROBE-1",
    )
    connection.close()

    print(f"probe work dir: {work_dir}")
    if failures:
        print(f"PROBE_FAILED: {failures}")
        return 1
    print("PROBE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
