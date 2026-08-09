"""Rollback note for the FUTURE migration 14 (design-review finding F-6).

This file records the DROP COLUMN rollback contract that the migration-14
implementation must preserve. Migration 14 is NOT implemented: no schema is
changed here; the tests only assert SQLite capabilities and the documented
caveat on a fresh temp database.

Contract (see ``docs/integration/wave1/13_MIGRATION_14_AMENDMENTS.md``):
- ``ALTER TABLE ... DROP COLUMN`` rollback requires SQLite >= 3.35.
- With a COLUMN-level CHECK, ``ALTER TABLE essays DROP COLUMN domain`` succeeds
  and later inserts work.
- Any index (likewise view/trigger) on the ``domain`` column blocks the DROP
  until that object is dropped first.
"""

from __future__ import annotations

import sqlite3

import pytest


DDL = """
CREATE TABLE essays(
    essay_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    essay_text TEXT NOT NULL,
    submitted_at TEXT NOT NULL
);
INSERT INTO essays(student_id, essay_text, submitted_at)
VALUES ('S1', 'legacy essay', '2026-01-01T00:00:00+00:00');
"""


def _apply_domain_discriminator(connection: sqlite3.Connection) -> None:
    connection.execute(
        "ALTER TABLE essays ADD COLUMN domain TEXT NOT NULL DEFAULT 'l2'"
        " CHECK (domain IN ('l2', 'academic'))"
    )


def test_bundled_sqlite_supports_drop_column_rollback():
    # F-6: DROP COLUMN rollback requires SQLite >= 3.35.
    assert sqlite3.sqlite_version_info >= (3, 35)


def test_drop_column_succeeds_in_fresh_temp_db(tmp_path):
    path = tmp_path / "rollback_note.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(DDL)
        _apply_domain_discriminator(connection)
        legacy = connection.execute(
            "SELECT domain FROM essays WHERE essay_id = 1"
        ).fetchone()
        assert legacy[0] == "l2"  # DEFAULT covers existing rows
        connection.execute("ALTER TABLE essays DROP COLUMN domain")
        connection.execute(
            "INSERT INTO essays(student_id, essay_text, submitted_at)"
            " VALUES ('S2', 'after rollback', '2026-01-02T00:00:00+00:00')"
        )
        assert connection.execute("SELECT COUNT(*) FROM essays").fetchone()[0] == 2


def test_index_on_domain_blocks_drop_until_dropped(tmp_path):
    path = tmp_path / "rollback_note_index.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(DDL)
        _apply_domain_discriminator(connection)
        connection.execute("CREATE INDEX idx_essays_domain ON essays(domain)")
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("ALTER TABLE essays DROP COLUMN domain")
        connection.execute("DROP INDEX idx_essays_domain")
        connection.execute("ALTER TABLE essays DROP COLUMN domain")  # now allowed
