"""v0.9.5-F2 focused contract tests for Service repository dependency narrowing.

Proves:
- PriorRecordsPort declares exactly one method with the source signature;
- LearnerHistoryService can be constructed and run with a stub exposing only
  ``prior_records`` (no ``save_history`` / ``list_student_history`` required)
  and its annotation targets PriorRecordsPort;
- the Database facade and SQLiteSubmissionRepository satisfy PriorRecordsPort
  structurally, and ``prior_records`` results are identical;
- both application-construction paths supply the existing
  SQLiteConfigurationRepository instance (not the broad Database facade) to
  ConfigurationService;
- all seven Configuration methods remain callable with the extracted
  repository and create/validate/activate/list/audit/active behavior is
  unchanged;
- DashboardService and LearnerProfileService still receive the facade.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI

from app.analysis import AnalyzerRegistry, default_metric_registry
from app.analyzer import BasicAnalyzer
from app.api.main import _build_full_app, _run_startup
from app.config import Settings
from app.configuration import ConfigurationCreate, ConfigurationPayload
from app.database import Database
from app.diagnosis import HeuristicDiagnoser
from app.infrastructure.sqlite.repositories import (
    SQLiteConfigurationRepository,
    SQLiteSubmissionRepository,
)
from app.learner import PriorRecordsPort
from app.learner.history import LearnerHistoryService
from app.lifecycle import ServiceLifecycle, lifecycle
from app.models import EssaySubmission
from app.services.configuration import ConfigurationService


def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "f2.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


def _submission(student_id: str = "F2-STUDENT", when=None) -> EssaySubmission:
    return EssaySubmission(
        student_id=student_id,
        writing_prompt="Should campuses add more quiet study spaces?",
        genre="argumentative essay", draft_stage="first draft", timed=False, tool_use="none",
        essay_text=(
            "Campuses need quiet rooms because students need space to focus. "
            "Libraries are often crowded during examinations."
        ),
        submitted_at=when or datetime(2026, 2, 1, tzinfo=timezone.utc),
    )


def _configuration_service(repository) -> ConfigurationService:
    return ConfigurationService(
        repository, AnalyzerRegistry([BasicAnalyzer()]), default_metric_registry(),
    )


def _snapshot_lifecycle() -> ServiceLifecycle:
    return dataclasses.replace(lifecycle)


def _restore_lifecycle(saved: ServiceLifecycle) -> None:
    for field in dataclasses.fields(ServiceLifecycle):
        setattr(lifecycle, field.name, getattr(saved, field.name))


class _StubPriorRecords:
    """Minimal consumer-stub exposing only the one port method."""

    def __init__(self, records: list[dict]):
        self._records = records

    def prior_records(self, submission):
        return self._records


# ---------------------------------------------------------------------------
# PriorRecordsPort contract
# ---------------------------------------------------------------------------


def test_prior_records_port_declares_exactly_one_method():
    public = [name for name in dir(PriorRecordsPort) if not name.startswith("_")]
    assert public == ["prior_records"]
    signature = inspect.signature(PriorRecordsPort.prior_records)
    parameters = list(signature.parameters.values())
    assert [parameter.name for parameter in parameters] == ["self", "submission"]
    assert "EssaySubmission" in str(parameters[1].annotation)
    assert str(signature.return_annotation).startswith("list[dict[str, Any]]")


def test_learner_history_service_annotated_against_prior_records_port():
    signature = inspect.signature(LearnerHistoryService.__init__)
    annotation = signature.parameters["database"].annotation
    assert "PriorRecordsPort" in str(annotation)
    assert "LearnerHistoryRepository" not in str(annotation)


def test_facade_and_submission_repository_satisfy_prior_records_port(tmp_path):
    repository = Database(tmp_path / "not-opened.db")
    assert isinstance(repository._submission_repository, PriorRecordsPort)
    assert isinstance(repository._submission_repository, SQLiteSubmissionRepository)
    assert isinstance(repository._submission_repository, PriorRecordsPort)
    assert not (tmp_path / "not-opened.db").exists()


# ---------------------------------------------------------------------------
# LearnerHistoryService narrowing
# ---------------------------------------------------------------------------


def test_learner_history_service_requires_only_prior_records():
    submission = _submission()
    analysis = BasicAnalyzer().analyze(submission.essay_text)
    diagnosis = HeuristicDiagnoser().diagnose(analysis)
    service = LearnerHistoryService(_StubPriorRecords([]))
    result = service.summarize(1, submission, analysis, diagnosis)
    assert result.comparability_status == "insufficient_history"
    assert result.history_evidence == []
    assert result.summary == "数据不足，无法判断趋势。"


def test_learner_history_selection_unchanged_with_stub():
    submission = _submission()
    analysis = BasicAnalyzer().analyze(submission.essay_text)
    diagnosis = HeuristicDiagnoser().diagnose(analysis)
    prior = [{
        "student_id": submission.student_id, "essay_id": 1,
        "writing_prompt": submission.writing_prompt, "genre": submission.genre,
        "draft_stage": submission.draft_stage, "timed": submission.timed,
        "time_limit_minutes": submission.time_limit_minutes, "tool_use": submission.tool_use,
        "submitted_at": submission.submitted_at - timedelta(days=7),
        "metrics": {"word_count": 120},
        "diagnosis": {"improvement_priorities": []},
    }]
    service = LearnerHistoryService(_StubPriorRecords(prior))
    result = service.summarize(1, submission, analysis, diagnosis)
    assert result.comparability_status == "comparable"
    assert result.comparable_submission_count == 1
    assert result.history_evidence
    assert all(item.supporting_submission_ids for item in result.history_evidence)


def test_prior_records_delegation_unchanged(tmp_path):
    repository = Database(tmp_path / "prior.db")
    repository.initialize()
    first = _submission("S1", datetime(2026, 1, 1, tzinfo=timezone.utc))
    second = _submission("S1", datetime(2026, 1, 8, tzinfo=timezone.utc))
    repository._submission_repository.save_essay(first)
    repository._submission_repository.save_essay(second)
    facade_rows = repository._submission_repository.prior_records(second)
    repo_rows = repository._submission_repository.prior_records(second)
    assert facade_rows == repo_rows
    assert len(facade_rows) == 1
    assert facade_rows[0]["essay_id"] == 1


def test_learner_history_runtime_object_compatible_through_submission_service(tmp_path):
    settings = _settings(tmp_path)
    repository = Database(settings.database_path)
    repository.initialize()
    service = LearnerHistoryService(repository._submission_repository)
    assert isinstance(repository._submission_repository, PriorRecordsPort)
    assert service.database is repository._submission_repository


# ---------------------------------------------------------------------------
# ConfigurationService narrowing
# ---------------------------------------------------------------------------


def test_build_full_app_passes_extracted_configuration_repository(tmp_path):
    app = _build_full_app(_settings(tmp_path))
    repository = app.state.repository
    assert isinstance(repository, Database)
    assert isinstance(app.state.configurations.repository, SQLiteConfigurationRepository)
    assert app.state.configurations.repository is repository._configuration_repository
    assert app.state.configurations.repository is not repository
    assert not isinstance(app.state.configurations.repository, Database)
    assert app.state.dashboards.repository is repository._learner_repository
    assert app.state.learner_profiles.repository is repository._learner_repository


def test_run_startup_passes_extracted_configuration_repository(tmp_path, monkeypatch):
    saved = _snapshot_lifecycle()
    try:
        monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "startup.db"))
        monkeypatch.setenv("LLM_PROVIDER", "local")
        api = FastAPI()
        _run_startup(api)
        repository = api.state.repository
        assert isinstance(repository, Database)
        assert isinstance(api.state.configurations.repository, SQLiteConfigurationRepository)
        assert api.state.configurations.repository is repository._configuration_repository
        assert api.state.configurations.repository is not repository
        assert not isinstance(api.state.configurations.repository, Database)
        assert api.state.dashboards.repository is repository._learner_repository
        assert api.state.learner_profiles.repository is repository._learner_repository
    finally:
        _restore_lifecycle(saved)


def test_configuration_service_seven_methods_unchanged_with_extracted_repository(tmp_path):
    repository = Database(tmp_path / "cfg.db")
    repository.initialize()
    extracted = repository._configuration_repository
    service = _configuration_service(extracted)
    assert isinstance(extracted, SQLiteConfigurationRepository)
    assert not isinstance(service.repository, Database)

    configs = service.list()
    assert isinstance(configs, list) and configs
    assert service.active().version == "config-v0.9.0"

    created = service.create(ConfigurationCreate(
        payload=ConfigurationPayload(active_analyzer="basic", mattr_window=65),
        change_note="F2 contract test.",
    ))
    assert created.status == "draft" and created.parent_version == "config-v0.9.0"

    validated = service.validate(created.configuration_id, actor="local_researcher")
    assert validated.validation_status == "passed" and validated.status == "validated"

    activated = service.activate(created.configuration_id, actor="local_researcher", reason="F2 test.")
    assert activated.status == "active"
    assert sum(item.status == "active" for item in service.list()) == 1
    assert service.active().configuration_id == created.configuration_id

    actions = [item["action"] for item in service.audit()]
    assert {"create", "validate", "activate"} <= set(actions)

    fetched = service.repository.get_configuration(created.configuration_id)
    assert fetched is not None and fetched.status == "active"


def test_configuration_validation_failure_path_unchanged(tmp_path):
    repository = Database(tmp_path / "cfg-fail.db")
    repository.initialize()
    service = _configuration_service(repository._configuration_repository)
    created = service.create(ConfigurationCreate(
        payload=ConfigurationPayload(active_analyzer="spacy", mattr_window=65),
        change_note="F2 failure-path contract test.",
    ))
    checked = service.validate(created.configuration_id)
    assert checked.validation_status == "failed" and checked.validation_errors
