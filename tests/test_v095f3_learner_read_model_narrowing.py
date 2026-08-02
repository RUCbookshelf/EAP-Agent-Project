from __future__ import annotations

import ast
import inspect
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI

from app.analysis import default_metric_registry
from app.api.main import _build_full_app, _run_startup
from app.config import Settings
from app.config.longitudinal import RULES
from app.configuration import ConfigurationPayload, ConfigurationVersion
from app.database import Database
from app.feedback.service import FeedbackPipeline
from app.infrastructure.sqlite.repositories.configuration import SQLiteConfigurationRepository
from app.infrastructure.sqlite.repositories.learner import SQLiteLearnerRepository
from app.services.dashboard import DashboardReadPort, DashboardService
from app.services.factory import build_submission_service
from app.services.learner_profile import LearnerProfileReadPort, LearnerProfileService
from app.services.progress import ActiveConfigurationPort, LearnerProgressPort, ProgressService
from tests.test_longitudinal_v03 import record
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "f3.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _active_configuration() -> ConfigurationVersion:
    return ConfigurationVersion(
        configuration_id="CFG999999",
        version="config-v0.9.99",
        status="active",
        created_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        created_by="f3-test",
        payload=ConfigurationPayload(),
        change_note="F3 focused configuration stub.",
        validation_status="passed",
        activated_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        content_hash="f3-focused-content-hash",
    )


def _records(count: int = 4) -> list[dict]:
    rows = [record(index, 100 + index * 10) for index in range(1, count + 1)]
    for row in rows:
        essay_id = int(row["essay_id"])
        row.update({
            "is_longitudinal_representative": True,
            "revision_exclusion_reason": None,
            "analysis_run_id": f"AR{essay_id:06d}",
            "analyzer_id": "basic",
            "analyzer_version": row["analysis_version"],
            "configuration_version": "config-v0.9.0",
            "versioned_metrics": {
                "word_count": {
                    "value": row["metrics"]["word_count"],
                    "metric_version": "0.1.0",
                    "status": "available",
                    "limitations": [],
                    "confidence": "low",
                    "eligible_for_longitudinal_comparison": True,
                }
            },
        })
    return rows


class MinimalLearnerProgressRepository:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.save_count = 0

    def list_visualization_records(self, student_id: str) -> list[dict]:
        return [deepcopy(row) for row in self.rows if row["student_id"] == student_id]

    def save_learner_profile_snapshot(self, snapshot):
        self.save_count += 1
        return snapshot.model_copy(update={"snapshot_id": f"LPS{self.save_count:06d}"})


class MinimalConfigurationRepository:
    def __init__(self, active):
        self.active = active
        self.query_count = 0

    def get_active_configuration(self):
        self.query_count += 1
        return self.active


class MinimalLearnerProfileRepository:
    def __init__(self, latest=None, history=None):
        self.latest = latest
        self.rows = history or []

    def get_latest_learner_profile(self, student_id: str):
        return self.latest

    def list_learner_profile_snapshots(self, student_id: str):
        return list(self.rows)


def _public_protocol_methods(protocol) -> set[str]:
    return {
        name for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def _assert_extracted_chain(profile_service, database: Database) -> None:
    assert profile_service.repository is database._learner_repository
    assert profile_service.progress.learner_repository is database._learner_repository
    assert profile_service.progress.configuration_repository is database._configuration_repository
    assert not isinstance(profile_service.repository, Database)


def test_four_ports_have_exact_names_methods_and_source_signatures():
    assert _public_protocol_methods(DashboardReadPort) == {"list_visualization_records"}
    assert _public_protocol_methods(LearnerProfileReadPort) == {
        "get_latest_learner_profile", "list_learner_profile_snapshots",
    }
    assert _public_protocol_methods(LearnerProgressPort) == {
        "list_visualization_records", "save_learner_profile_snapshot",
    }
    assert _public_protocol_methods(ActiveConfigurationPort) == {"get_active_configuration"}

    learner_methods = {
        "list_visualization_records": SQLiteLearnerRepository.list_visualization_records,
        "save_learner_profile_snapshot": SQLiteLearnerRepository.save_learner_profile_snapshot,
        "get_latest_learner_profile": SQLiteLearnerRepository.get_latest_learner_profile,
        "list_learner_profile_snapshots": SQLiteLearnerRepository.list_learner_profile_snapshots,
    }
    for protocol in (DashboardReadPort, LearnerProfileReadPort, LearnerProgressPort):
        for name in _public_protocol_methods(protocol):
            assert inspect.signature(getattr(protocol, name)) == inspect.signature(learner_methods[name])
    assert inspect.signature(ActiveConfigurationPort.get_active_configuration) == inspect.signature(
        SQLiteConfigurationRepository.get_active_configuration
    )


def test_concrete_repositories_and_facade_structurally_satisfy_ports(tmp_path):
    database = Database(tmp_path / "ports.db")
    learner = database._learner_repository
    configuration = database._configuration_repository
    assert isinstance(learner, DashboardReadPort)
    assert isinstance(learner, LearnerProfileReadPort)
    assert isinstance(learner, LearnerProgressPort)
    assert isinstance(configuration, ActiveConfigurationPort)
    assert isinstance(database, DashboardReadPort)
    assert isinstance(database, LearnerProfileReadPort)
    assert isinstance(database, LearnerProgressPort)
    assert isinstance(database, ActiveConfigurationPort)


def test_progress_uses_only_exact_ports_and_preserves_persist_behavior():
    learner = MinimalLearnerProgressRepository(_records())
    configuration = MinimalConfigurationRepository(_active_configuration())
    service = ProgressService(learner, configuration)

    preview = service.create_snapshot("S001", persist=False)
    assert learner.save_count == 0
    assert configuration.query_count == 1
    assert preview.configuration_version == "config-v0.9.99"
    assert preview.included_submission_ids == ["E000001", "E000002", "E000003", "E000004"]

    stored = service.create_snapshot("S001", persist=True)
    assert learner.save_count == 1
    assert configuration.query_count == 2
    assert stored.snapshot_id == "LPS000001"
    assert stored.included_submission_ids == preview.included_submission_ids


def test_progress_none_configuration_preserves_default_and_queries_once():
    learner = MinimalLearnerProgressRepository(_records(3))
    configuration = MinimalConfigurationRepository(None)
    snapshot = ProgressService(learner, configuration).create_snapshot("S001", persist=False)
    assert configuration.query_count == 1
    assert learner.save_count == 0
    assert snapshot.configuration_version == RULES.configuration_version


def test_learner_profile_uses_minimal_read_port_and_injected_progress():
    learner = MinimalLearnerProgressRepository(_records())
    configuration = MinimalConfigurationRepository(None)
    progress = ProgressService(learner, configuration)
    reads = MinimalLearnerProfileRepository(history=[{"snapshot_id": "LPS000001"}])
    service = LearnerProfileService(reads, progress)

    assert service.progress is progress
    assert service.history("S001") == [{"snapshot_id": "LPS000001"}]
    preview = service.recalculate("S001", persist=False)
    assert learner.save_count == 0
    assert service.latest_or_recalculate("S001").snapshot_id == "LPS000001"
    assert learner.save_count == 1
    assert preview.student_id == "S001"


def test_dashboard_uses_minimal_read_port_persist_false_and_empty_state():
    dashboard_read = MinimalLearnerProgressRepository(_records())
    progress_read = MinimalLearnerProgressRepository(_records())
    configuration = MinimalConfigurationRepository(None)
    progress = ProgressService(progress_read, configuration)
    service = DashboardService(dashboard_read, default_metric_registry(), progress)

    result = service.build("S001", "word_count")
    assert result["student_id"] == "S001"
    assert [item["submission_id"] for item in result["timeline"]] == [1, 2, 3, 4]
    assert progress_read.save_count == 0
    assert dashboard_read.save_count == 0

    empty = MinimalLearnerProgressRepository([])
    with pytest.raises(LookupError, match="Student has no submissions"):
        DashboardService(empty, default_metric_registry(), progress).build("S001")
    assert empty.save_count == 0


def test_service_modules_have_no_broad_imports_fallback_or_internal_construction():
    paths = [
        ROOT / "app/services/progress.py",
        ROOT / "app/services/learner_profile.py",
        ROOT / "app/services/dashboard.py",
    ]
    sources = {path.name: path.read_text(encoding="utf-8") for path in paths}
    for source in sources.values():
        assert "app.database" not in source
        assert "SQLiteLearnerRepository" not in source
        assert "SQLiteConfigurationRepository" not in source
    assert "hasattr(" not in sources["progress.py"]
    assert "list_longitudinal_records" not in sources["progress.py"]

    for filename in ("learner_profile.py", "dashboard.py"):
        tree = ast.parse(sources[filename])
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "ProgressService"
        ]
        assert calls == []


def test_submission_factory_explicit_and_legacy_composition(tmp_path, monkeypatch):
    from app.services import factory as factory_module

    monkeypatch.setattr(factory_module, "build_analyzer", lambda settings: object())
    settings = _settings(tmp_path)
    database = Database(settings.database_path)
    database.initialize()

    explicit = build_submission_service(
        settings,
        system_repository=database._system_repository,
        submission_repository=database._submission_repository,
        analysis_repository=database._analysis_repository,
        calibration_repository=database._calf_repository,
        learner_repository=database._learner_repository,
        configuration_repository=database._configuration_repository,
        revision_repository=database._revision_repository,
    )
    _assert_extracted_chain(explicit.learner_profile_service, database)
    assert explicit.learner_profile_service.repository is database._learner_repository
    assert explicit.learner_profile_service.progress.learner_repository is database._learner_repository
    assert explicit.learner_profile_service.progress.configuration_repository is database._configuration_repository


def test_build_full_app_uses_extracted_repositories_for_all_f3_chains(tmp_path):
    api = _build_full_app(_settings(tmp_path))
    database = api.state.repository
    _assert_extracted_chain(api.state.learner_profiles, database)
    _assert_extracted_chain(api.state.submission_service.learner_profile_service, database)
    assert api.state.dashboards.repository is database._learner_repository
    assert api.state.dashboards.progress.learner_repository is database._learner_repository
    assert api.state.dashboards.progress.configuration_repository is database._configuration_repository
    assert api.state.learner_profiles.progress is not api.state.dashboards.progress
    assert api.state.configurations.repository is database._configuration_repository


def test_run_startup_uses_extracted_repositories_for_all_f3_chains(tmp_path, monkeypatch):
    saved = _snapshot_lifecycle()
    try:
        monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "startup.db"))
        monkeypatch.setenv("LLM_PROVIDER", "local")
        api = FastAPI()
        _run_startup(api)
        database = api.state.repository
        _assert_extracted_chain(api.state.learner_profiles, database)
        _assert_extracted_chain(api.state.submission_service.learner_profile_service, database)
        assert api.state.dashboards.repository is database._learner_repository
        assert api.state.dashboards.progress.learner_repository is database._learner_repository
        assert api.state.dashboards.progress.configuration_repository is database._configuration_repository
        assert api.state.learner_profiles.progress is not api.state.dashboards.progress
        assert api.state.configurations.repository is database._configuration_repository
    finally:
        _restore_lifecycle(saved)


def test_feedback_pipeline_reuses_one_database_repository_graph(tmp_path):
    settings = _settings(tmp_path)
    database = Database(settings.database_path)
    learner = database._learner_repository
    configuration = database._configuration_repository
    connection_manager = database._connection_manager

    pipeline = FeedbackPipeline(settings, database=database)
    assert pipeline.database is database
    profile_service = pipeline._service.learner_profile_service
    _assert_extracted_chain(profile_service, database)
    assert database._learner_repository is learner
    assert database._configuration_repository is configuration
    assert learner._connection_manager is connection_manager
    assert configuration._connection_manager is connection_manager

    source = (ROOT / "app/feedback/service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    database_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "Database"
    ]
    assert len(database_calls) == 1


def test_f2_dependency_contracts_remain_unchanged(tmp_path):
    api = _build_full_app(_settings(tmp_path))
    database = api.state.repository
    assert api.state.configurations.repository is database._configuration_repository
    assert isinstance(api.state.configurations.repository, SQLiteConfigurationRepository)
    assert api.state.submission_service.history.database is database._submission_repository
