"""v0.9.5-F6B focused tests: AdminReanalysisService persistence dependency narrowing.

Proves the three consumer-owned Ports, exact six-method routing, preserved
Service collaborations, preview zero-write behavior, run call-order and
partial-commit semantics, and facade-owned composition identity at both
application-construction paths.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI

from app.api.main import _build_full_app, _run_startup
from app.database import Database
from app.repositories import RevisionRepository
from app.services.admin_reanalysis import (
    AdminAnalysisPort,
    AdminConfigurationReadPort,
    AdminReanalysisService,
    AdminSubmissionReadPort,
    ReanalysisRequest,
)
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle
from tests.test_v06_configuration_dashboard import (
    _configuration_service,
    _essay,
    _seed,
    _service,
    _settings,
)


ROOT = Path(__file__).resolve().parents[1]


def _public_protocol_methods(protocol) -> set[str]:
    return {
        name for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def _admin(repository, settings, configurations, service):
    return AdminReanalysisService(
        settings=settings,
        configuration_reader=repository._configuration_repository,
        submission_reader=repository._submission_repository,
        analysis_repository=repository._analysis_repository,
        configurations=configurations,
        submission_service=service,
        revision_repository=repository._revision_repository,
    )


class _ConfigReaderStub:
    def __init__(self):
        self.calls = []

    def get_configuration(self, configuration_id_or_version):
        self.calls.append(configuration_id_or_version)
        return None


class _SubmissionReaderStub:
    def __init__(self, bundle=None):
        self.calls = []
        self.bundle = bundle

    def get_submission_bundle(self, essay_id):
        self.calls.append(("bundle", essay_id))
        return self.bundle

    def list_student_submissions(self, student_id):
        self.calls.append(("list", student_id))
        return []


class _AnalysisRepoStub:
    def __init__(self):
        self.calls = []

    def get_analysis_run(self, analysis_run_id):
        self.calls.append(("get", analysis_run_id))
        return None

    def save_analysis_run(self, essay_id, analysis):
        self.calls.append(("save", essay_id))
        return analysis


class _RevisionRepoStub:
    def __init__(self):
        self.calls = []

    def get_revision_group(self, revision_group_id):
        self.calls.append(revision_group_id)
        return None


class _ConfigServiceStub:
    def __init__(self):
        self.calls = []

    def active(self):
        self.calls.append("active")
        return None


class _SubmissionServiceStub:
    def __init__(self):
        self.calls = []

    def regenerate_feedback(self, essay_id, analysis):
        self.calls.append(essay_id)
        return None


def _stub_service(configuration_reader, submission_reader, analysis_repository,
                  configurations, submission_service, revision_repository):
    return AdminReanalysisService(
        settings=None,
        configuration_reader=configuration_reader,
        submission_reader=submission_reader,
        analysis_repository=analysis_repository,
        configurations=configurations,
        submission_service=submission_service,
        revision_repository=revision_repository,
    )


class TestPortContracts:
    def test_exact_names_methods_and_source_signatures(self):
        from app.infrastructure.sqlite.repositories.analysis import SQLiteAnalysisRepository
        from app.infrastructure.sqlite.repositories.configuration import SQLiteConfigurationRepository
        from app.infrastructure.sqlite.repositories.submission import SQLiteSubmissionRepository

        assert _public_protocol_methods(AdminConfigurationReadPort) == {"get_configuration"}
        assert _public_protocol_methods(AdminSubmissionReadPort) == {
            "get_submission_bundle", "list_student_submissions",
        }
        assert _public_protocol_methods(AdminAnalysisPort) == {
            "get_analysis_run", "save_analysis_run",
        }

        def sig(cls, name):
            return inspect.signature(getattr(cls, name))

        assert sig(AdminConfigurationReadPort, "get_configuration") == sig(
            SQLiteConfigurationRepository, "get_configuration")
        assert sig(AdminSubmissionReadPort, "get_submission_bundle") == sig(
            SQLiteSubmissionRepository, "get_submission_bundle")
        assert sig(AdminSubmissionReadPort, "list_student_submissions") == sig(
            SQLiteSubmissionRepository, "list_student_submissions")
        assert sig(AdminAnalysisPort, "get_analysis_run") == sig(
            SQLiteAnalysisRepository, "get_analysis_run")
        assert sig(AdminAnalysisPort, "save_analysis_run") == sig(
            SQLiteAnalysisRepository, "save_analysis_run")

    def test_concrete_repositories_and_facade_structurally_satisfy_ports(self, tmp_path):
        database = Database(tmp_path / "ports.db")
        database.initialize()
        assert isinstance(database._configuration_repository, AdminConfigurationReadPort)
        assert isinstance(database._submission_repository, AdminSubmissionReadPort)
        assert isinstance(database._analysis_repository, AdminAnalysisPort)
        from app.infrastructure.sqlite.repositories.revision import SQLiteRevisionRepository
        for name, member in vars(RevisionRepository).items():
            if name.startswith("_") or not callable(member):
                continue
            assert hasattr(SQLiteRevisionRepository, name), name
            assert inspect.signature(
                getattr(SQLiteRevisionRepository, name)) == inspect.signature(member), name


class TestServiceContract:
    def test_constructor_signature_exact_and_no_broad_repository(self):
        parameters = inspect.signature(AdminReanalysisService.__init__).parameters
        assert list(parameters) == [
            "self", "settings", "configuration_reader", "submission_reader",
            "analysis_repository", "configurations", "submission_service",
            "revision_repository",
        ]
        assert parameters["revision_repository"].kind is inspect.Parameter.KEYWORD_ONLY
        assert "repository" not in parameters
        assert "AdminConfigurationReadPort" in str(parameters["configuration_reader"].annotation)
        assert "AdminSubmissionReadPort" in str(parameters["submission_reader"].annotation)
        assert "AdminAnalysisPort" in str(parameters["analysis_repository"].annotation)
        assert "RevisionRepository" in str(parameters["revision_repository"].annotation)

    def test_service_module_has_no_broad_import_any_repository_or_discovery(self):
        source = (ROOT / "app/services/admin_reanalysis.py").read_text(encoding="utf-8")
        assert "app.database" not in source
        assert "SQLite" not in source
        assert "hasattr(" not in source
        assert "self.repository" not in source
        assert "self.repo" not in source
        assert "fallback" not in source
        assert "ServiceLocator" not in source
        assert "UnitOfWork" not in source
        tree = ast.parse(source)
        init = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        annotations = {
            ast.unparse(argument.annotation)
            for argument in [*init.args.args, *init.args.kwonlyargs]
            if argument.annotation is not None
        }
        assert annotations == {
            "Settings", "AdminConfigurationReadPort", "AdminSubmissionReadPort",
            "AdminAnalysisPort", "ConfigurationService", "SubmissionService",
            "RevisionRepository",
        }

    def test_no_seventh_direct_persistence_method_exists(self):
        source = (ROOT / "app/services/admin_reanalysis.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Attribute) and node.func.value.attr in {
                    "configuration_reader", "submission_reader",
                    "analysis_repository", "revision_repository",
                }:
                    calls.add(node.func.attr)
        assert calls == {
            "get_configuration", "get_submission_bundle", "list_student_submissions",
            "get_analysis_run", "save_analysis_run", "get_revision_group",
        }

    def test_minimal_stubs_route_each_scope_to_its_approved_port(self):
        config = _ConfigReaderStub()
        submission = _SubmissionReaderStub()
        analysis = _AnalysisRepoStub()
        revision = _RevisionRepoStub()
        service = _stub_service(
            config, submission, analysis, _ConfigServiceStub(),
            _SubmissionServiceStub(), revision,
        )
        assert service.revisions.repository is revision

        with pytest.raises(LookupError, match="Submission not found."):
            service.preview(ReanalysisRequest(
                scope_type="submission", scope_id="2", analyzer_id="basic"))
        assert submission.calls == [("bundle", 2)]

        with pytest.raises(LookupError, match="Student has no submissions."):
            service.preview(ReanalysisRequest(
                scope_type="student", scope_id="S", analyzer_id="basic"))
        assert submission.calls == [("bundle", 2), ("list", "S")]

        with pytest.raises(LookupError, match="Revision group not found."):
            service.preview(ReanalysisRequest(
                scope_type="revision_group", scope_id="RG", analyzer_id="basic"))
        assert revision.calls == ["RG"]

        with pytest.raises(LookupError, match="AnalysisRun not found."):
            service.preview(ReanalysisRequest(
                scope_type="analysis_run", scope_id="AR", analyzer_id="basic"))
        assert analysis.calls == [("get", "AR")]
        assert config.calls == []

    def test_minimal_one_method_configuration_stub_is_sufficient(self):
        config = _ConfigReaderStub()
        configurations = _ConfigServiceStub()
        service = _stub_service(
            config, _SubmissionReaderStub(bundle={"essay_id": 1}), _AnalysisRepoStub(),
            configurations, _SubmissionServiceStub(), _RevisionRepoStub(),
        )
        with pytest.raises(LookupError, match="Configuration not found."):
            service.preview(ReanalysisRequest(
                scope_type="submission", scope_id="1", analyzer_id="basic",
                configuration_version="config-v0.9.0",
            ))
        assert config.calls == ["config-v0.9.0"]
        assert configurations.calls == []


class TestPreviewZeroWrite:
    def test_preview_performs_zero_writes_and_preserves_read_order(self, tmp_path, monkeypatch):
        settings, repository, _, service, ids = _seed(tmp_path, count=1)
        configurations = _configuration_service(repository)
        admin = _admin(repository, settings, configurations, service)
        calls: list[str] = []

        def rec(label, target, name):
            original = getattr(target, name)

            def wrapper(*args, **kwargs):
                calls.append(label)
                return original(*args, **kwargs)

            monkeypatch.setattr(target, name, wrapper)

        rec("bundle", repository._submission_repository, "get_submission_bundle")
        rec("save_analysis_run", repository._analysis_repository, "save_analysis_run")
        rec("create_revision_group", repository._revision_repository, "create_revision_group")
        rec("link_revision", repository._revision_repository, "link_revision")
        rec("save_revision_snapshot", repository._revision_repository, "save_revision_snapshot")
        rec("regenerate_feedback", service, "regenerate_feedback")

        before = len(repository._analysis_repository.list_analysis_runs(ids[0]))
        preview = admin.preview(ReanalysisRequest(
            scope_type="submission", scope_id=str(ids[0]), analyzer_id="basic"))
        assert preview["submission_count"] == 1
        assert calls == ["bundle"]
        assert len(repository._analysis_repository.list_analysis_runs(ids[0])) == before


class TestRunBehavior:
    def test_run_success_preserves_call_order_and_write_counts(self, tmp_path, monkeypatch):
        settings, repository, _, service, ids = _seed(tmp_path, count=1)
        configurations = _configuration_service(repository)
        admin = _admin(repository, settings, configurations, service)
        calls: list[str] = []

        def rec(label, target, name):
            original = getattr(target, name)

            def wrapper(*args, **kwargs):
                calls.append(label)
                return original(*args, **kwargs)

            monkeypatch.setattr(target, name, wrapper)

        rec("bundle", repository._submission_repository, "get_submission_bundle")
        rec("active", configurations, "active")
        rec("get_configuration", repository._configuration_repository, "get_configuration")
        rec("save_analysis_run", repository._analysis_repository, "save_analysis_run")
        rec("regenerate_feedback", service, "regenerate_feedback")
        rec("recalculate", admin.revisions, "recalculate")

        result = admin.run(ReanalysisRequest(
            scope_type="submission", scope_id=str(ids[0]), analyzer_id="basic"))
        assert result["llm_called"] is False and result["feedback_records"] == []
        assert result["analysis_runs"][0]["submission_id"] == ids[0]
        assert calls == [
            "bundle",          # preview _scope submission lookup
            "active",          # preview active-configuration resolution
            "get_configuration",   # run validated-configuration lookup
            "bundle",          # run row bundle
            "save_analysis_run",
            "bundle",          # run revision-group-id bundle
        ]
        assert calls.count("save_analysis_run") == 1
        assert "regenerate_feedback" not in calls
        assert "recalculate" not in calls

    def test_feedback_enabled_calls_regeneration_exactly_once_after_save(self, tmp_path, monkeypatch):
        settings, repository, _, service, ids = _seed(tmp_path, count=1)
        admin = _admin(repository, settings, _configuration_service(repository), service)
        calls: list[str] = []
        original_save = repository._analysis_repository.save_analysis_run
        original_regenerate = service.regenerate_feedback

        def save(*args, **kwargs):
            calls.append("save_analysis_run")
            return original_save(*args, **kwargs)

        def regenerate(*args, **kwargs):
            calls.append("regenerate_feedback")
            return original_regenerate(*args, **kwargs)

        monkeypatch.setattr(repository._analysis_repository, "save_analysis_run", save)
        monkeypatch.setattr(service, "regenerate_feedback", regenerate)

        result = admin.run(ReanalysisRequest(
            scope_type="submission", scope_id=str(ids[0]), analyzer_id="basic",
            call_llm=True, confirm_llm_cost=True,
        ))
        assert result["llm_called"] is True
        assert result["feedback_records"][0]["provider"] == "local-demo"
        assert calls == ["save_analysis_run", "regenerate_feedback"]

    def test_failure_before_analysis_save_performs_zero_writes(self, tmp_path, monkeypatch):
        settings, repository, _, service, ids = _seed(tmp_path, count=1)
        admin = _admin(repository, settings, _configuration_service(repository), service)
        original = repository._submission_repository.get_submission_bundle

        def broken(essay_id):
            row = original(essay_id)
            if row is not None:
                row = {key: value for key, value in row.items() if key != "essay_text"}
            return row

        monkeypatch.setattr(repository._submission_repository, "get_submission_bundle", broken)
        before = len(repository._analysis_repository.list_analysis_runs(ids[0]))
        with pytest.raises(KeyError):
            admin.run(ReanalysisRequest(
                scope_type="submission", scope_id=str(ids[0]), analyzer_id="basic"))
        assert len(repository._analysis_repository.list_analysis_runs(ids[0])) == before

    def test_failure_in_save_analysis_run_propagates_without_later_calls(self, tmp_path, monkeypatch):
        settings, repository, _, service, ids = _seed(tmp_path, count=1)
        admin = _admin(repository, settings, _configuration_service(repository), service)
        calls: list[str] = []
        original_regenerate = service.regenerate_feedback

        before = len(repository._analysis_repository.list_analysis_runs(ids[0]))

        def boom(*args, **kwargs):
            raise RuntimeError("save exploded")

        def regenerate(*args, **kwargs):
            calls.append("regenerate_feedback")
            return original_regenerate(*args, **kwargs)

        monkeypatch.setattr(repository._analysis_repository, "save_analysis_run", boom)
        monkeypatch.setattr(service, "regenerate_feedback", regenerate)
        with pytest.raises(RuntimeError, match="save exploded"):
            admin.run(ReanalysisRequest(
                scope_type="submission", scope_id=str(ids[0]), analyzer_id="basic",
                call_llm=True, confirm_llm_cost=True,
            ))
        assert calls == []
        assert len(repository._analysis_repository.list_analysis_runs(ids[0])) == before

    def test_failure_after_save_preserves_committed_analysis(self, tmp_path, monkeypatch):
        settings, repository, _, service, ids = _seed(tmp_path, count=1)
        admin = _admin(repository, settings, _configuration_service(repository), service)
        before = len(repository._analysis_repository.list_analysis_runs(ids[0]))

        def boom(*args, **kwargs):
            raise RuntimeError("feedback exploded")

        monkeypatch.setattr(service, "regenerate_feedback", boom)
        with pytest.raises(RuntimeError, match="feedback exploded"):
            admin.run(ReanalysisRequest(
                scope_type="submission", scope_id=str(ids[0]), analyzer_id="basic",
                call_llm=True, confirm_llm_cost=True,
            ))
        assert len(repository._analysis_repository.list_analysis_runs(ids[0])) == before + 1

    def test_revision_failure_preserves_analysis_and_exception_after_revision_group_run(
            self, tmp_path, monkeypatch):
        settings, repository, revisions, service = _service(tmp_path)
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        first = service.submit(_essay(
            "F6B-RG", "Quiet rooms help students focus during study.", now))
        revised = service.submit(_essay(
            "F6B-RG", "Quiet rooms help students focus during demanding study periods.",
            now + timedelta(days=1), source=first.essay_id, stage="revised draft",
        ))
        group_id = revised.revision_snapshot.revision_group_id
        before = len(revisions.history(group_id))
        admin = _admin(repository, settings, _configuration_service(repository), service)

        def boom(*args, **kwargs):
            raise RuntimeError("recalculate exploded")

        monkeypatch.setattr(admin.revisions, "recalculate", boom)
        with pytest.raises(RuntimeError, match="recalculate exploded"):
            admin.run(ReanalysisRequest(
                scope_type="revision_group", scope_id=group_id, analyzer_id="basic"))
        assert len(repository._analysis_repository.list_analysis_runs(first.essay_id)) == 2
        assert len(repository._analysis_repository.list_analysis_runs(revised.essay_id)) == 2
        assert len(revisions.history(group_id)) == before


class TestAppConstructionIdentity:
    def _assert_admin_wiring(self, api):
        database = api.state.repository
        admin = api.state.admin_reanalysis
        assert admin.configuration_reader is database._configuration_repository
        assert admin.submission_reader is database._submission_repository
        assert admin.analysis_repository is database._analysis_repository
        assert admin.revision_repository is database._revision_repository
        assert admin.revisions.repository is database._revision_repository
        assert not hasattr(admin, "repository")
        assert not isinstance(admin.configuration_reader, Database)
        assert admin.configuration_reader._connection_manager is database._connection_manager
        assert admin.submission_reader._connection_manager is database._connection_manager
        assert admin.analysis_repository._connection_manager is database._connection_manager
        assert admin.revision_repository._connection_manager is database._connection_manager
        assert database._revision_repository._submission_reader is database._submission_repository
        assert database._revision_repository._analysis_reader is database._analysis_repository

    def test_build_full_app_wires_facade_owned_repositories(self, tmp_path):
        api = _build_full_app(_settings(tmp_path))
        self._assert_admin_wiring(api)

    def test_run_startup_wires_facade_owned_repositories(self, tmp_path, monkeypatch):
        saved = _snapshot_lifecycle()
        try:
            monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
            monkeypatch.delenv("DATABASE_URL", raising=False)
            monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "startup.db"))
            monkeypatch.setenv("LLM_PROVIDER", "local")
            api = FastAPI()
            _run_startup(api)
            self._assert_admin_wiring(api)
        finally:
            _restore_lifecycle(saved)
