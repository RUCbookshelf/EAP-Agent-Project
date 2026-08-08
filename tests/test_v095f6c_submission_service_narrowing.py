"""v0.9.5-F6C focused tests: SubmissionService persistence dependency narrowing.

Proves the four owner-aligned Ports, exact 11-method routing, constructor
`record_versions` side effect, submit and regenerate-feedback call ordering,
CALF capability-guard removal, partial-commit failure semantics, and
facade-owned composition identity at both application-construction paths,
the factory, and FeedbackPipeline.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI

from app.api.main import _build_full_app, _run_startup
from app.database import Database
from app.models import EssaySubmission
from app.services import build_submission_service
from app.version import PLATFORM_APPLICATION_VERSION as _PLATFORM_APP_VERSION
from app.services.submission import (
    SubmissionAnalysisPort,
    SubmissionCalibrationPort,
    SubmissionDataPort,
    SubmissionService,
    SubmissionSystemPort,
)
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]


def _public_protocol_methods(protocol) -> set[str]:
    return {
        name for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def _settings(tmp_path):
    from app.config import Settings
    return Settings(
        database_path=tmp_path / "f6c.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


def _submission(student_id: str = "F6C-S", *, stage: str = "first draft",
                source: int | None = None) -> EssaySubmission:
    return EssaySubmission(
        student_id=student_id,
        writing_prompt="Should campuses add more quiet study spaces?",
        genre="argumentative essay",
        draft_stage=stage,
        timed=False,
        tool_use="none",
        essay_text=(
            "Campuses need quiet rooms because students need space to focus. "
            "Libraries are often crowded during examinations."
        ),
        submitted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        revision_of_submission_id=source,
    )


def _factory_service(database: Database, settings):
    return build_submission_service(
        settings,
        system_repository=database._system_repository,
        submission_repository=database._submission_repository,
        analysis_repository=database._analysis_repository,
        calibration_repository=database._calf_repository,
        learner_repository=database._learner_repository,
        configuration_repository=database._configuration_repository,
        revision_repository=database._revision_repository,
    )


class _SystemStub:
    def __init__(self):
        self.calls = []

    def record_versions(self, versions):
        self.calls.append(versions)


class _DataStub:
    def __init__(self):
        self.calls = []

    def save_essay(self, submission, *, synthetic=False):
        self.calls.append("save_essay")
        return 1

    def prior_records(self, submission):
        self.calls.append("prior_records")
        return []

    def get_submission_bundle(self, essay_id):
        self.calls.append("get_submission_bundle")
        return None

    def save_feedback(self, essay_id, result, analysis_version):
        self.calls.append("save_feedback")

    def save_history(self, student_id, essay_id, history):
        self.calls.append("save_history")


class _AnalysisStub:
    def __init__(self):
        self.calls = []

    def save_analysis_run(self, essay_id, analysis):
        self.calls.append("save_analysis_run")
        return analysis

    def save_analysis(self, essay_id, analysis):
        self.calls.append("save_analysis")

    def save_diagnosis(self, essay_id, diagnosis):
        self.calls.append("save_diagnosis")


class _CalibrationStub:
    def __init__(self):
        self.calls = []

    def save_diagnostic_calibration(self, essay_id, calibration):
        self.calls.append("save_diagnostic_calibration")
        return calibration

    def get_diagnostic_calibration(self, essay_id):
        self.calls.append("get_diagnostic_calibration")
        return None


class TestPortContracts:
    def test_exact_names_methods_and_source_signatures(self):
        from app.infrastructure.sqlite.repositories.analysis import SQLiteAnalysisRepository
        from app.infrastructure.sqlite.repositories.calf import SQLiteCalfRepository
        from app.infrastructure.sqlite.repositories.submission import SQLiteSubmissionRepository
        from app.infrastructure.sqlite.repositories.system import SQLiteSystemRepository

        assert _public_protocol_methods(SubmissionSystemPort) == {"record_versions"}
        assert _public_protocol_methods(SubmissionDataPort) == {
            "save_essay", "prior_records", "get_submission_bundle",
            "save_feedback", "save_history",
        }
        assert _public_protocol_methods(SubmissionAnalysisPort) == {
            "save_analysis_run", "save_analysis", "save_diagnosis",
        }
        assert _public_protocol_methods(SubmissionCalibrationPort) == {
            "save_diagnostic_calibration", "get_diagnostic_calibration",
        }

        def sig(cls, name):
            return inspect.signature(getattr(cls, name))

        assert sig(SubmissionSystemPort, "record_versions") == sig(
            SQLiteSystemRepository, "record_versions")
        for name in ("save_essay", "prior_records", "get_submission_bundle",
                     "save_feedback", "save_history"):
            assert sig(SubmissionDataPort, name) == sig(SQLiteSubmissionRepository, name), name
        for name in ("save_analysis_run", "save_analysis", "save_diagnosis"):
            assert sig(SubmissionAnalysisPort, name) == sig(SQLiteAnalysisRepository, name), name
        for name in ("save_diagnostic_calibration", "get_diagnostic_calibration"):
            assert sig(SubmissionCalibrationPort, name) == sig(SQLiteCalfRepository, name), name

    def test_concrete_repositories_and_facade_structurally_satisfy_ports(self, tmp_path):
        database = Database(tmp_path / "ports.db")
        database.initialize()
        assert isinstance(database._system_repository, SubmissionSystemPort)
        assert isinstance(database._submission_repository, SubmissionDataPort)
        assert isinstance(database._analysis_repository, SubmissionAnalysisPort)
        assert isinstance(database._calf_repository, SubmissionCalibrationPort)

    def test_no_cross_port_method_and_exact_eleven_method_union(self):
        all_methods = (
            _public_protocol_methods(SubmissionSystemPort)
            | _public_protocol_methods(SubmissionDataPort)
            | _public_protocol_methods(SubmissionAnalysisPort)
            | _public_protocol_methods(SubmissionCalibrationPort)
        )
        assert len(all_methods) == 11
        assert len(_public_protocol_methods(SubmissionSystemPort)
                   & _public_protocol_methods(SubmissionDataPort)
                   & _public_protocol_methods(SubmissionAnalysisPort)
                   & _public_protocol_methods(SubmissionCalibrationPort)) == 0


class TestServiceContract:
    def test_constructor_signature_exact_and_no_broad_repository(self):
        parameters = inspect.signature(SubmissionService.__init__).parameters
        assert list(parameters) == [
            "self", "system_repository", "submission_repository",
            "analysis_repository", "calibration_repository", "analyzer",
            "diagnoser", "router", "learner_profile_service",
            "revision_service", "calibrator", "calf_configuration",
        ]
        assert "repository" not in parameters
        assert "SubmissionSystemPort" in str(parameters["system_repository"].annotation)
        assert "SubmissionDataPort" in str(parameters["submission_repository"].annotation)
        assert "SubmissionAnalysisPort" in str(parameters["analysis_repository"].annotation)
        assert "SubmissionCalibrationPort" in str(parameters["calibration_repository"].annotation)
        assert parameters["analyzer"].default is inspect.Parameter.empty
        assert parameters["learner_profile_service"].default is None
        assert parameters["revision_service"].default is None
        assert parameters["calibrator"].default is None
        assert parameters["calf_configuration"].default is None

    def test_service_module_has_no_broad_import_any_repository_or_discovery(self):
        source = (ROOT / "app/services/submission.py").read_text(encoding="utf-8")
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
        assert {
            "SubmissionSystemPort", "SubmissionDataPort", "SubmissionAnalysisPort",
            "SubmissionCalibrationPort", "Analyzer", "Diagnoser", "ProviderRouter",
        } <= annotations
        assert "SubmissionRepository" not in annotations

    def test_exact_eleven_direct_persistence_calls_via_ports(self):
        source = (ROOT / "app/services/submission.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Attribute) and node.func.value.attr in {
                    "system_repository", "submission_repository",
                    "analysis_repository", "calibration_repository",
                }:
                    calls.add(node.func.attr)
        assert calls == {
            "record_versions", "save_essay", "prior_records", "get_submission_bundle",
            "save_feedback", "save_history", "save_analysis_run", "save_analysis",
            "save_diagnosis", "save_diagnostic_calibration", "get_diagnostic_calibration",
        }

    def test_legacy_submission_repository_not_required_by_active_composition(self):
        source = (ROOT / "app/services/submission.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        init = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        assert "SubmissionRepository" not in ast.unparse(init.args)
        factory = (ROOT / "app/services/factory.py").read_text(encoding="utf-8")
        assert "SubmissionRepository" not in factory
        factory_tree = ast.parse(factory)
        builder = next(
            node for node in ast.walk(factory_tree)
            if isinstance(node, ast.FunctionDef) and node.name == "build_submission_service"
        )
        parameter_names = [
            argument.arg for argument in [*builder.args.args, *builder.args.kwonlyargs]
        ]
        assert "repository" not in parameter_names

    def test_minimal_stubs_are_sufficient_and_record_versions_is_constructor_time(self):
        from app.analyzer import BasicAnalyzer
        from app.diagnosis import HeuristicDiagnoser
        from app.llm import LocalDemoProvider, ProviderRouter

        system = _SystemStub()
        data = _DataStub()
        analysis = _AnalysisStub()
        calibration = _CalibrationStub()
        service = SubmissionService(
            system_repository=system,
            submission_repository=data,
            analysis_repository=analysis,
            calibration_repository=calibration,
            analyzer=BasicAnalyzer(),
            diagnoser=HeuristicDiagnoser(),
            router=ProviderRouter(LocalDemoProvider(), LocalDemoProvider()),
        )
        assert len(system.calls) == 1
        assert system.calls[0]["application"] == _PLATFORM_APP_VERSION
        assert system.calls[0]["feedback_schema"] == "structured-feedback-v0.7.1"
        assert data.calls == [] and analysis.calls == [] and calibration.calls == []
        assert service.history.database is data

    def test_record_versions_failure_propagates_from_constructor(self):
        from app.analyzer import BasicAnalyzer
        from app.diagnosis import HeuristicDiagnoser
        from app.llm import LocalDemoProvider, ProviderRouter

        system = _SystemStub()

        def boom(versions):
            raise RuntimeError("version write exploded")

        system.record_versions = boom
        with pytest.raises(RuntimeError, match="version write exploded"):
            SubmissionService(
                system_repository=system,
                submission_repository=_DataStub(),
                analysis_repository=_AnalysisStub(),
                calibration_repository=_CalibrationStub(),
                analyzer=BasicAnalyzer(),
                diagnoser=HeuristicDiagnoser(),
                router=ProviderRouter(LocalDemoProvider(), LocalDemoProvider()),
            )


class TestFactoryContract:
    def test_factory_signature_requires_seven_keyword_only_repositories(self):
        parameters = inspect.signature(build_submission_service).parameters
        assert list(parameters) == [
            "settings", "system_repository", "submission_repository",
            "analysis_repository", "calibration_repository", "learner_repository",
            "configuration_repository", "revision_repository",
        ]
        assert "repository" not in parameters
        for name in ("system_repository", "submission_repository", "analysis_repository",
                     "calibration_repository", "learner_repository",
                     "configuration_repository", "revision_repository"):
            assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
            assert parameters[name].default is inspect.Parameter.empty

    def test_factory_wires_facade_owned_repositories(self, tmp_path):
        database = Database(tmp_path / "factory.db")
        database.initialize()
        service = _factory_service(database, _settings(tmp_path))
        assert service.system_repository is database._system_repository
        assert service.submission_repository is database._submission_repository
        assert service.analysis_repository is database._analysis_repository
        assert service.calibration_repository is database._calf_repository
        assert service.history.database is database._submission_repository
        assert service.learner_profile_service.repository is database._learner_repository
        assert service.revision_service.repository is database._revision_repository
        assert service.system_repository._connection_manager is database._connection_manager
        assert service.submission_repository._connection_manager is database._connection_manager
        assert service.analysis_repository._connection_manager is database._connection_manager
        assert service.calibration_repository._connection_manager is database._connection_manager


class TestAppConstructionIdentity:
    def _assert_wiring(self, api):
        database = api.state.repository
        service = api.state.submission_service
        assert service.system_repository is database._system_repository
        assert service.submission_repository is database._submission_repository
        assert service.analysis_repository is database._analysis_repository
        assert service.calibration_repository is database._calf_repository
        assert service.history.database is database._submission_repository
        assert service.learner_profile_service.repository is database._learner_repository
        assert service.revision_service.repository is database._revision_repository
        assert not hasattr(service, "repository")
        assert not isinstance(service.system_repository, Database)
        assert database._revision_repository._submission_reader is database._submission_repository
        assert database._revision_repository._analysis_reader is database._analysis_repository

    def test_build_full_app_wires_facade_owned_repositories(self, tmp_path):
        api = _build_full_app(_settings(tmp_path))
        self._assert_wiring(api)

    def test_run_startup_wires_facade_owned_repositories(self, tmp_path, monkeypatch):
        saved = _snapshot_lifecycle()
        try:
            monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
            monkeypatch.delenv("DATABASE_URL", raising=False)
            monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "startup.db"))
            monkeypatch.setenv("LLM_PROVIDER", "local")
            api = FastAPI()
            _run_startup(api)
            self._assert_wiring(api)
        finally:
            _restore_lifecycle(saved)

    def test_feedback_pipeline_uses_facade_owned_repositories(self, tmp_path):
        from app.feedback.service import FeedbackPipeline

        database = Database(tmp_path / "pipeline.db")
        pipeline = FeedbackPipeline(_settings(tmp_path), database=database)
        service = pipeline._service
        assert service.system_repository is database._system_repository
        assert service.submission_repository is database._submission_repository
        assert service.analysis_repository is database._analysis_repository
        assert service.calibration_repository is database._calf_repository
        assert service.history.database is database._submission_repository
        assert service.revision_service.repository is database._revision_repository
        assert service.calibrator is None


class TestSubmitBehavior:
    def _seed_service(self, tmp_path):
        settings = _settings(tmp_path)
        database = Database(settings.database_path)
        database.initialize()
        return settings, database, _factory_service(database, settings)

    def test_initial_submit_preserves_call_order_and_write_counts(self, tmp_path, monkeypatch):
        settings, database, service = self._seed_service(tmp_path)
        calls: list[str] = []

        def rec(label, target, name):
            original = getattr(target, name)

            def wrapper(*args, **kwargs):
                calls.append(label)
                return original(*args, **kwargs)

            monkeypatch.setattr(target, name, wrapper)

        rec("save_essay", database._submission_repository, "save_essay")
        rec("save_analysis_run", database._analysis_repository, "save_analysis_run")
        rec("save_analysis", database._analysis_repository, "save_analysis")
        rec("prior_records", database._submission_repository, "prior_records")
        rec("save_diagnosis", database._analysis_repository, "save_diagnosis")
        rec("save_diagnostic_calibration", database._calf_repository, "save_diagnostic_calibration")
        rec("recalculate", service.learner_profile_service, "recalculate")
        rec("generate", service.router, "generate")
        rec("save_feedback", database._submission_repository, "save_feedback")
        rec("save_history", database._submission_repository, "save_history")

        result = service.submit(_submission(), synthetic=True)
        assert result.essay_id == 1
        assert calls == [
            "save_essay", "save_analysis_run", "save_analysis", "prior_records",
            "save_diagnosis", "save_diagnostic_calibration", "prior_records",
            "recalculate", "generate", "save_feedback", "save_history",
        ]
        counts = database._system_repository.counts()
        assert counts["essays"] == 1
        assert counts["analysis_runs"] == 1
        assert counts["diagnoses"] == 1
        assert counts["diagnostic_calibrations"] == 1
        assert counts["feedback_records"] == 1
        assert counts["learner_history"] == 1

    def test_revised_submit_includes_revision_collaborator_calls(self, tmp_path, monkeypatch):
        settings, database, service = self._seed_service(tmp_path)
        first = service.submit(_submission("F6C-R"), synthetic=True)
        calls: list[str] = []

        def rec(label, target, name):
            original = getattr(target, name)

            def wrapper(*args, **kwargs):
                calls.append(label)
                return original(*args, **kwargs)

            monkeypatch.setattr(target, name, wrapper)

        rec("validate_relationship", service.revision_service, "validate_relationship")
        rec("create_relationship", service.revision_service, "create_relationship")
        rec("group_summary", service.revision_service, "group_summary")
        rec("trajectory", service.revision_service, "trajectory")

        result = service.submit(
            _submission("F6C-R", stage="revised draft", source=first.essay_id),
            synthetic=True,
        )
        assert result.revision_snapshot is not None
        assert calls == [
            "validate_relationship", "create_relationship",
            "validate_relationship", "group_summary", "trajectory",
        ]
        with database.connect() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM revision_groups").fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(*) FROM revision_snapshots").fetchone()[0] == 1

    def test_feedback_pipeline_calibrator_absent_skips_calibration_branch(self, tmp_path, monkeypatch):
        from app.feedback.service import FeedbackPipeline

        database = Database(tmp_path / "nocal.db")
        pipeline = FeedbackPipeline(_settings(tmp_path), database=database)
        calls: list[str] = []
        original_prior = database._submission_repository.prior_records

        def prior(*args, **kwargs):
            calls.append("prior_records")
            return original_prior(*args, **kwargs)

        monkeypatch.setattr(database._submission_repository, "prior_records", prior)
        result = pipeline.submit(_submission("F6C-NC"), synthetic=True)
        assert result.diagnostic_calibration is None
        assert calls == ["prior_records"]
        with database.connect() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM diagnostic_calibrations").fetchone()[0] == 0


class TestRegenerateFeedbackBehavior:
    def _seeded(self, tmp_path):
        settings = _settings(tmp_path)
        database = Database(settings.database_path)
        database.initialize()
        service = _factory_service(database, settings)
        result = service.submit(_submission("F6C-RG"), synthetic=True)
        return database, service, result

    def test_regenerate_feedback_preserves_call_order(self, tmp_path, monkeypatch):
        database, service, result = self._seeded(tmp_path)
        calls: list[str] = []

        def rec(label, target, name):
            original = getattr(target, name)

            def wrapper(*args, **kwargs):
                calls.append(label)
                return original(*args, **kwargs)

            monkeypatch.setattr(target, name, wrapper)

        rec("get_submission_bundle", database._submission_repository, "get_submission_bundle")
        rec("latest_or_recalculate", service.learner_profile_service, "latest_or_recalculate")
        rec("get_diagnostic_calibration", database._calf_repository, "get_diagnostic_calibration")
        rec("generate", service.router, "generate")
        rec("save_feedback", database._submission_repository, "save_feedback")

        regenerated = service.regenerate_feedback(result.essay_id, result.analysis)
        assert regenerated.provider_name == "local-demo"
        assert calls == [
            "get_submission_bundle", "latest_or_recalculate",
            "get_diagnostic_calibration", "generate", "save_feedback",
        ]

    def test_regenerate_feedback_missing_submission_raises_before_any_call(self, tmp_path, monkeypatch):
        database, service, result = self._seeded(tmp_path)
        calls: list[str] = []
        original = database._submission_repository.save_feedback

        def feedback(*args, **kwargs):
            calls.append("save_feedback")
            return original(*args, **kwargs)

        monkeypatch.setattr(database._submission_repository, "save_feedback", feedback)
        with pytest.raises(LookupError, match="Submission not found."):
            service.regenerate_feedback(9999, result.analysis)
        assert calls == []

    def test_regenerate_feedback_missing_diagnosis_raises(self, tmp_path):
        settings = _settings(tmp_path)
        database = Database(settings.database_path)
        database.initialize()
        service = _factory_service(database, settings)
        essay_id = database._submission_repository.save_essay(_submission("F6C-ND"))
        with pytest.raises(ValueError, match="Stored structured diagnosis is unavailable."):
            service.regenerate_feedback(essay_id, None)


class TestFailurePartialCommits:
    def _seed_service(self, tmp_path):
        settings = _settings(tmp_path)
        database = Database(settings.database_path)
        database.initialize()
        return settings, database, _factory_service(database, settings)

    def _seeded(self, tmp_path):
        settings = _settings(tmp_path)
        database = Database(settings.database_path)
        database.initialize()
        service = _factory_service(database, settings)
        result = service.submit(_submission("F6C-FAIL"), synthetic=True)
        return database, service, result

    @pytest.mark.parametrize("boundary", [
        "save_essay", "save_analysis_run", "save_analysis", "save_diagnosis",
        "save_diagnostic_calibration", "save_feedback", "save_history",
    ])
    def test_failure_at_each_write_boundary_preserves_earlier_commits(self, tmp_path, monkeypatch, boundary):
        settings, database, service = self._seed_service(tmp_path)
        calls: list[str] = []

        def boom(*args, **kwargs):
            raise RuntimeError(f"{boundary} exploded")

        if boundary == "save_essay":
            monkeypatch.setattr(database._submission_repository, boundary, boom)
        elif boundary in {"save_analysis_run", "save_analysis", "save_diagnosis"}:
            monkeypatch.setattr(database._analysis_repository, boundary, boom)
        elif boundary == "save_diagnostic_calibration":
            monkeypatch.setattr(database._calf_repository, boundary, boom)
        else:
            monkeypatch.setattr(database._submission_repository, boundary, boom)

        def rec(label, target, name):
            original = getattr(target, name)

            def wrapper(*args, **kwargs):
                calls.append(label)
                return original(*args, **kwargs)

            monkeypatch.setattr(target, name, wrapper)

        rec("save_essay", database._submission_repository, "save_essay")
        rec("save_analysis_run", database._analysis_repository, "save_analysis_run")
        rec("save_analysis", database._analysis_repository, "save_analysis")
        rec("save_diagnosis", database._analysis_repository, "save_diagnosis")
        rec("save_diagnostic_calibration", database._calf_repository, "save_diagnostic_calibration")
        rec("save_feedback", database._submission_repository, "save_feedback")
        rec("save_history", database._submission_repository, "save_history")

        with pytest.raises(RuntimeError, match=f"{boundary} exploded"):
            service.submit(_submission(f"F6C-{boundary}"), synthetic=True)

        counts = database._system_repository.counts()
        order = ["save_essay", "save_analysis_run", "save_analysis", "save_diagnosis",
                 "save_diagnostic_calibration", "save_feedback", "save_history"]
        boundary_index = order.index(boundary)
        assert calls[: boundary_index + 1][-1] == boundary
        assert len(calls) == boundary_index + 1
        expected_committed = {
            "essays": 1 if boundary_index >= 1 else 0,
            "analysis_runs": 1 if boundary_index >= 2 else 0,
            "diagnoses": 1 if boundary_index >= 4 else 0,
            "diagnostic_calibrations": 1 if boundary_index >= 5 else 0,
            "feedback_records": 1 if boundary_index >= 6 else 0,
            "learner_history": 0,
        }
        for table, expected in expected_committed.items():
            assert counts[table] == expected, f"{table}: {counts[table]} != {expected}"

    def test_save_essay_failure_commits_nothing(self, tmp_path, monkeypatch):
        settings, database, service = self._seed_service(tmp_path)

        def boom(*args, **kwargs):
            raise RuntimeError("save_essay exploded")

        monkeypatch.setattr(database._submission_repository, "save_essay", boom)
        with pytest.raises(RuntimeError, match="save_essay exploded"):
            service.submit(_submission("F6C-Z"), synthetic=True)
        counts = database._system_repository.counts()
        assert counts["essays"] == 0

    def test_regenerate_feedback_failure_preserves_committed_feedback(self, tmp_path, monkeypatch):
        database, service, result = self._seeded(tmp_path)
        before = len(database._analysis_repository.list_analysis_runs(result.essay_id))

        def boom(*args, **kwargs):
            raise RuntimeError("feedback write exploded")

        monkeypatch.setattr(database._submission_repository, "save_feedback", boom)
        with pytest.raises(RuntimeError, match="feedback write exploded"):
            service.regenerate_feedback(result.essay_id, result.analysis)
        assert len(database._analysis_repository.list_analysis_runs(result.essay_id)) == before
        with database.connect() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM feedback_records WHERE essay_id=?",
                (result.essay_id,),
            ).fetchone()[0] == 1
