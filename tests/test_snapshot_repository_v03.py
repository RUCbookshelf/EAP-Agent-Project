from __future__ import annotations

from app.database import Database, LATEST_MIGRATION_VERSION
from app.services import ProgressService
from tests.test_longitudinal_api_v03 import seed


def test_snapshot_save_latest_history_and_restart(tmp_path):
    path = tmp_path / "snapshots.db"
    repository = Database(path); repository.initialize()
    seed(repository, "SNAP001", [100, 120, 140])
    service = ProgressService(repository)
    first = service.create_snapshot("SNAP001")
    second = service.create_snapshot("SNAP001")
    assert first.snapshot_id != second.snapshot_id
    reopened = Database(path); reopened.initialize()
    assert reopened.migration_version() == LATEST_MIGRATION_VERSION == 9
    assert reopened.get_latest_learner_profile("SNAP001")["snapshot_id"] == second.snapshot_id
    history = reopened.list_learner_profile_snapshots("SNAP001")
    assert [item["snapshot_id"] for item in history] == [first.snapshot_id, second.snapshot_id]
    assert history[0]["configuration_version"] == "config-v0.7.1"


def test_v02_database_upgrades_to_snapshot_schema_without_losing_rows(tmp_path):
    repository = Database(tmp_path / "upgrade.db")
    repository.initialize()
    seed(repository, "UPGRADE03", [100])
    with repository.connect() as connection:
        connection.execute("PRAGMA user_version = 2")
        connection.execute("DROP TABLE learner_profile_snapshots")
    repository.initialize()
    assert repository.migration_version() == LATEST_MIGRATION_VERSION == 9
    assert repository.get_student("UPGRADE03")["submission_count"] == 1
    assert repository.get_latest_learner_profile("UPGRADE03") is None
