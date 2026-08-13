"""Option-A global integer ledger guard tests.

Goal PDW3-WU2-CORE-GLOBAL-LEDGER-GUARD-OPTION-A-20260812.

The project keeps ONE shared integer migration ledger
(``schema_migrations.version INTEGER PRIMARY KEY`` + the ``MIGRATIONS``
registry + ``app.database.upgrade``/``rollback``). After the user-authorized
Option A decision, global Migration 15 is CORE-owned as
``review_scheduling_foundation``; LEARNER acknowledgement persistence moves
to global Migration 16 later in the SAME runner/ledger. These tests pin the
CORE-owned source/consumer seam (constants + guard) that the later LEARNER
Migration 16 runner must consume, and prove the ledger stays unique at 15
with no second migration runner or second database.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.database import LATEST_MIGRATION_VERSION, rollback, upgrade
from app.database import migrations as migrations_module
from app.database.migrations import (
    GLOBAL_MIGRATION_LEDGER_OWNER,
    GLOBAL_MIGRATION_LEDGER_VERSION_15,
    GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME,
    MIGRATIONS,
    assert_global_migration_15_identity,
)
from app.version import PLATFORM_DATABASE_MIGRATION_VERSION


def test_global_ledger_constants_declare_option_a_identity() -> None:
    """CORE retains global integer 15 with the unique CORE identity."""
    assert GLOBAL_MIGRATION_LEDGER_OWNER == "CORE"
    assert GLOBAL_MIGRATION_LEDGER_VERSION_15 == 15
    assert GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME == (
        "review_scheduling_foundation"
    )
    assert LATEST_MIGRATION_VERSION == 15
    assert PLATFORM_DATABASE_MIGRATION_VERSION == 15
    assert MIGRATIONS[GLOBAL_MIGRATION_LEDGER_VERSION_15][0] == (
        GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME
    )
    # The real Wave-3 WU1 body is still the registry entry (no substitute
    # migration was attached to version 15).
    assert (
        MIGRATIONS[GLOBAL_MIGRATION_LEDGER_VERSION_15][1]
        is migrations_module._migration_15
    )


def test_version_15_identity_is_unique_in_global_ledger() -> None:
    """No second ledger version may reuse the CORE identity name."""
    holders = [
        version
        for version, (name, _) in MIGRATIONS.items()
        if name == GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME
    ]
    assert holders == [GLOBAL_MIGRATION_LEDGER_VERSION_15]
    assert GLOBAL_MIGRATION_LEDGER_VERSION_15 in MIGRATIONS


def test_fresh_database_ledger_has_exactly_one_row_15(tmp_path) -> None:
    connection = sqlite3.connect(tmp_path / "fresh.db")
    connection.row_factory = sqlite3.Row
    try:
        assert upgrade(connection) == 15
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations WHERE version=15"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["name"] == GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 15
        assert assert_global_migration_15_identity() == (
            15,
            GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME,
        )
    finally:
        connection.close()


def test_guard_detects_rename_at_15(monkeypatch) -> None:
    """A LEARNER-style collision at 15 is rejected by the guard."""
    monkeypatch.setitem(
        MIGRATIONS,
        15,
        ("learner_acknowledgement_persistence", migrations_module._migration_15),
    )
    with pytest.raises(RuntimeError, match="review_scheduling_foundation"):
        assert_global_migration_15_identity()


def test_guard_detects_latest_drift(monkeypatch) -> None:
    """LATEST_MIGRATION_VERSION drifting away from 15 fails the guard."""
    monkeypatch.setattr(migrations_module, "LATEST_MIGRATION_VERSION", 16)
    with pytest.raises(RuntimeError, match="LATEST_MIGRATION_VERSION"):
        assert_global_migration_15_identity()


def test_guard_detects_duplicate_identity_at_16(monkeypatch) -> None:
    """Reusing the CORE identity name at another version is rejected."""
    monkeypatch.setitem(
        MIGRATIONS,
        16,
        (GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME, migrations_module._migration_15),
    )
    with pytest.raises(RuntimeError, match="not unique"):
        assert_global_migration_15_identity()


def test_learner_runner_seam_is_single_runner_single_database(tmp_path) -> None:
    """The later LEARNER Migration 16 consumes this same runner/ledger."""
    from app.database import rollback as package_rollback
    from app.database import upgrade as package_upgrade

    assert package_upgrade is upgrade
    assert package_rollback is rollback
    assert migrations_module.upgrade is upgrade
    assert migrations_module.rollback is rollback

    connection = sqlite3.connect(tmp_path / "seam.db")
    connection.row_factory = sqlite3.Row
    try:
        assert upgrade(connection) == 15
        version, name = assert_global_migration_15_identity()
        assert version == 15
        assert name == GLOBAL_MIGRATION_LEDGER_VERSION_15_NAME
        # Same runner performs the non-destructive 15->14 rollback and the
        # re-apply; the ledger still carries exactly one row at 15.
        assert rollback(connection, 14) == 14
        assert upgrade(connection) == 15
        row_count = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE version=15"
        ).fetchone()[0]
        assert row_count == 1
    finally:
        connection.close()
