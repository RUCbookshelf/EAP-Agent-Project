"""v0.9.5-F5A focused tests: CALF Service dependency narrowing.

Covers the four consumer-owned Ports, minimal-stub behavior for
CalfService (report, trajectories, annotation import), write-count and
exception-propagation contracts, app-composition wiring in both construction
paths, the unchanged CALF router seam, and the one operational-script
constructor site.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.main import _build_full_app, _run_startup, create_app
from app.calf import ErrorAnnotation, default_calf_registry
from app.config import Settings
from app.database import Database
from app.infrastructure.sqlite.repositories.analysis import SQLiteAnalysisRepository
from app.infrastructure.sqlite.repositories.calf import SQLiteCalfRepository
from app.infrastructure.sqlite.repositories.learner import SQLiteLearnerRepository
from app.infrastructure.sqlite.repositories.submission import SQLiteSubmissionRepository
from app.services.calf import (
    CalfAnalysisReadPort,
    CalfDataPort,
    CalfService,
    CalfStudentReadPort,
    CalfSubmissionReadPort,
)
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "f5a.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _public_protocol_methods(protocol) -> set[str]:
    return {
        name for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def _bundle_row() -> dict:
    return {
        "essay_id": 7,
        "student_id": "F5A-CALF",
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay",
        "draft_stage": "first draft",
        "timed": False,
        "time_limit_minutes": None,
        "tool_use": "none",
        "essay_text": "People should protect the environment. People should recycle more. "
                      "People should save water.",
        "submitted_at": datetime(2026, 8, 2, tzinfo=timezone.utc),
        "revision_of_submission_id": None,
        "writing_started_at": None,
        "writing_submitted_at": None,
        "active_writing_duration_seconds": None,
        "timing_source": "unknown",
        "timing_quality": "unavailable",
        "unexplained_interruption": False,
    }


def _run_row(metric_results=None) -> dict:
    return {
        "analysis_run_id": "AR000001",
        "configuration_version": "config-v0.9.0",
        "metric_results": [] if metric_results is None else metric_results,
    }


def _mtld_item(*, eligible: bool = True) -> dict:
    specification = default_calf_registry().get_specification("mtld")
    return {
        "metric_id": "mtld",
        "metric_version": specification.metric_version,
        "analysis_unit_version": specification.analysis_unit_version,
        "value": 30.0,
        "confidence": "medium",
        "status": "available",
        "eligible_for_longitudinal_comparison": eligible,
    }


class MinimalCalfData:
    def __init__(self, *, annotations=None, units=None, saved=None):
        self.annotations = list(annotations or [])
        self.units = list(units or [])
        self.saved = saved if saved is not None else []
        self.calls: list[str] = []
        self.save_exception: Exception | None = None

    def list_analysis_units(self, submission_id: int, analysis_run_id: str | None = None):
        self.calls.append("list_analysis_units")
        return [dict(item) for item in self.units]

    def list_error_annotations(self, submission_id: int):
        self.calls.append("list_error_annotations")
        return list(self.annotations)

    def save_error_annotations(self, submission_id: int, annotations: list[ErrorAnnotation]):
        self.calls.append("save_error_annotations")
        if self.save_exception is not None:
            raise self.save_exception
        stored = list(annotations)
        self.saved.extend(stored)
        return stored


class MinimalSubmissionReader:
    def __init__(self, bundle=None, submissions=None):
        self.bundle = bundle
        self.submissions = list(submissions or [])
        self.calls: list[str] = []

    def get_submission_bundle(self, essay_id: int):
        self.calls.append("get_submission_bundle")
        return None if self.bundle is None else dict(self.bundle)

    def list_student_submissions(self, student_id: str):
        self.calls.append("list_student_submissions")
        return [dict(item) for item in self.submissions]


class MinimalAnalysisReader:
    def __init__(self, run=None):
        self.run = run
        self.calls: list[str] = []

    def get_latest_analysis_run(self, essay_id: int):
        self.calls.append("get_latest_analysis_run")
        return None if self.run is None else dict(self.run)


class MinimalStudentReader:
    def __init__(self, student=None):
        self.student = student
        self.calls: list[str] = []

    def get_student(self, student_id: str):
        self.calls.append("get_student")
        return None if self.student is None else dict(self.student)


def _service(**overrides) -> CalfService:
    kwargs = {
        "calf_repository": MinimalCalfData(),
        "submission_reader": MinimalSubmissionReader(_bundle_row()),
        "analysis_reader": MinimalAnalysisReader(_run_row()),
        "student_reader": MinimalStudentReader({"student_id": "F5A-CALF"}),
    }
    kwargs.update(overrides)
    return CalfService(**kwargs)


class TestFourPorts:
    def test_exact_names_methods_and_source_signatures(self):
        assert _public_protocol_methods(CalfDataPort) == {
            "list_analysis_units",
            "list_error_annotations",
            "save_error_annotations",
        }
        assert _public_protocol_methods(CalfSubmissionReadPort) == {
            "get_submission_bundle",
            "list_student_submissions",
        }
        assert _public_protocol_methods(CalfAnalysisReadPort) == {"get_latest_analysis_run"}
        assert _public_protocol_methods(CalfStudentReadPort) == {"get_student"}

        assert inspect.signature(CalfDataPort.list_analysis_units) == inspect.signature(
            SQLiteCalfRepository.list_analysis_units
        )
        assert inspect.signature(CalfDataPort.list_error_annotations) == inspect.signature(
            SQLiteCalfRepository.list_error_annotations
        )
        assert inspect.signature(CalfDataPort.save_error_annotations) == inspect.signature(
            SQLiteCalfRepository.save_error_annotations
        )
        assert inspect.signature(CalfSubmissionReadPort.get_submission_bundle) == inspect.signature(
            SQLiteSubmissionRepository.get_submission_bundle
        )
        assert inspect.signature(CalfSubmissionReadPort.list_student_submissions) == inspect.signature(
            SQLiteSubmissionRepository.list_student_submissions
        )
        assert inspect.signature(CalfAnalysisReadPort.get_latest_analysis_run) == inspect.signature(
            SQLiteAnalysisRepository.get_latest_analysis_run
        )
        assert inspect.signature(CalfStudentReadPort.get_student) == inspect.signature(
            SQLiteLearnerRepository.get_student
        )

    def test_concrete_repositories_and_facade_structurally_satisfy_ports(self, tmp_path):
        database = Database(tmp_path / "ports.db")
        calf = database._calf_repository
        submission = database._submission_repository
        analysis = database._analysis_repository
        learner = database._learner_repository

        assert isinstance(calf, CalfDataPort)
        assert isinstance(submission, CalfSubmissionReadPort)
        assert isinstance(analysis, CalfAnalysisReadPort)
        assert isinstance(learner, CalfStudentReadPort)
        # Legacy verification only: the facade remains structurally compatible.
        assert isinstance(database, CalfDataPort)
        assert isinstance(database, CalfSubmissionReadPort)
        assert isinstance(database, CalfAnalysisReadPort)
        assert isinstance(database, CalfStudentReadPort)


class TestCalfServiceNarrowing:
    def test_minimal_stubs_are_sufficient_and_report_preserves_call_order_and_output(self):
        calf = MinimalCalfData(units=[{"unit_id": "sentence", "span": [0, 10]}])
        submission = MinimalSubmissionReader(_bundle_row())
        analysis = MinimalAnalysisReader(_run_row())
        student = MinimalStudentReader({"student_id": "F5A-CALF"})
        service = CalfService(calf, submission, analysis, student)

        report = service.submission_report(7)

        assert submission.calls == ["get_submission_bundle"]
        assert analysis.calls == ["get_latest_analysis_run"]
        assert calf.calls == ["list_error_annotations", "list_analysis_units"]
        assert report["submission_id"] == 7
        assert report["analysis_run_id"] == "AR000001"
        assert report["configuration_version"] == "config-v0.9.0"
        assert report["interpretation_boundary"]
        assert report["accuracy_annotation_availability"]["measurement_status"] == "unavailable"
        assert report["analysis_units"] == [{"unit_id": "sentence", "span": [0, 10]}]
        assert report["construct_groups"]
        assert report["timing"]["timed"] is False
        assert report["timing"]["time_limit_is_actual_duration"] is False

    def test_missing_submission_raises_before_any_other_read_or_write(self):
        calf = MinimalCalfData()
        submission = MinimalSubmissionReader(None)
        analysis = MinimalAnalysisReader(_run_row())
        service = CalfService(calf, submission, analysis, MinimalStudentReader({}))

        with pytest.raises(LookupError, match="Submission not found."):
            service.submission_report(99)

        assert submission.calls == ["get_submission_bundle"]
        assert analysis.calls == []
        assert calf.calls == []

    def test_missing_analysis_run_preserves_empty_report_state(self):
        service = _service(analysis_reader=MinimalAnalysisReader(None))

        report = service.submission_report(7)

        assert report["analysis_run_id"] is None
        assert report["configuration_version"] is None
        assert report["metric_results"]
        assert all(item["status"] == "insufficient_data" for item in report["metric_results"])
        assert report["analysis_units"] == []

    def test_trajectories_preserves_call_order_and_exclusion_behavior(self):
        submissions = [{
            "essay_id": 1, "student_id": "F5A-CALF", "genre": "argumentative essay",
            "timed": False, "time_limit_minutes": None, "tool_use": "none",
            "submitted_at": "2026-08-01T10:00:00+00:00",
        }]
        calf = MinimalCalfData()
        submission = MinimalSubmissionReader(_bundle_row(), submissions)
        analysis = MinimalAnalysisReader(_run_row([_mtld_item(eligible=False)]))
        student = MinimalStudentReader({"student_id": "F5A-CALF"})
        service = CalfService(calf, submission, analysis, student)

        result = service.trajectories("F5A-CALF")

        assert student.calls == ["get_student"]
        assert submission.calls == ["list_student_submissions"]
        assert analysis.calls == ["get_latest_analysis_run"]
        assert result["series"] == []
        assert result["excluded_observations"] == [{
            "submission_id": 1, "metric_id": "mtld",
            "reason": "Metric confidence or data requirements exclude this observation.",
        }]

    def test_trajectories_populated_series_preserves_observations_and_order(self):
        submissions = [{
            "essay_id": 1, "student_id": "F5A-CALF", "genre": "argumentative essay",
            "timed": False, "time_limit_minutes": None, "tool_use": "none",
            "submitted_at": "2026-08-01T10:00:00+00:00",
        }]
        calf = MinimalCalfData()
        submission = MinimalSubmissionReader(_bundle_row(), submissions)
        analysis = MinimalAnalysisReader(_run_row([_mtld_item(eligible=True)]))
        service = CalfService(calf, submission, analysis, MinimalStudentReader({}))

        result = service.trajectories("F5A-CALF")

        assert len(result["series"]) == 1
        series = result["series"][0]
        assert series["metric_id"] == "mtld"
        assert series["version_compatibility_rule"] == "exact"
        assert series["observations"] == [{
            "submission_id": 1, "submitted_at": "2026-08-01T10:00:00+00:00",
            "value": 30.0, "confidence": "medium",
            "task_conditions": {
                "genre": "argumentative essay", "timed": False,
                "time_limit_minutes": None, "tool_use": "none",
            },
        }]
        assert result["excluded_observations"] == []

    def test_missing_student_raises_and_performs_zero_submission_reads(self):
        calf = MinimalCalfData()
        submission = MinimalSubmissionReader()
        service = CalfService(calf, submission, MinimalAnalysisReader(), MinimalStudentReader(None))

        with pytest.raises(LookupError, match="Student not found."):
            service.trajectories("NOPE")

        assert submission.calls == []

    def test_import_success_performs_exactly_one_save_after_one_bundle_read(self):
        annotation = ErrorAnnotation(
            submission_id=7, start_offset=0, end_offset=5, original_text="Peopl",
            error_category="grammar", correction="People", annotation_source="human",
            annotation_status="confirmed", annotator_id="R01",
            guideline_version="error-guideline-v0.8.0", confidence="high",
        )
        calf = MinimalCalfData()
        submission = MinimalSubmissionReader(_bundle_row())
        service = CalfService(calf, submission, MinimalAnalysisReader(), MinimalStudentReader({}))

        result = service.import_error_annotations(7, [annotation])

        assert submission.calls == ["get_submission_bundle"]
        assert calf.calls == ["save_error_annotations"]
        assert calf.saved == [annotation]
        assert result == [annotation]

    def test_validation_failure_performs_zero_saves(self):
        annotation = ErrorAnnotation(
            submission_id=7, start_offset=0, end_offset=999, original_text="Peopl",
            error_category="grammar", correction="People", annotation_source="human",
            annotation_status="confirmed", annotator_id="R01", guideline_version="g-v1", confidence="high",
        )
        calf = MinimalCalfData()
        service = CalfService(calf, MinimalSubmissionReader(_bundle_row()),
                              MinimalAnalysisReader(), MinimalStudentReader({}))

        with pytest.raises(ValueError, match="offsets exceed"):
            service.import_error_annotations(7, [annotation])

        assert calf.calls == []
        assert calf.saved == []

    def test_original_text_mismatch_performs_zero_saves(self):
        annotation = ErrorAnnotation(
            submission_id=7, start_offset=0, end_offset=5, original_text="WRONG",
            error_category="grammar", correction="People", annotation_source="human",
            annotation_status="confirmed", annotator_id="R01", guideline_version="g-v1", confidence="high",
        )
        calf = MinimalCalfData()
        service = CalfService(calf, MinimalSubmissionReader(_bundle_row()),
                              MinimalAnalysisReader(), MinimalStudentReader({}))

        with pytest.raises(ValueError, match="must exactly match"):
            service.import_error_annotations(7, [annotation])

        assert calf.calls == []
        assert calf.saved == []

    def test_repository_exceptions_propagate_unchanged(self):
        calf = MinimalCalfData()
        calf.save_exception = LookupError("Submission not found.")
        annotation = ErrorAnnotation(
            submission_id=7, start_offset=0, end_offset=5, original_text="Peopl",
            error_category="grammar", correction="People", annotation_source="human",
            annotation_status="confirmed", annotator_id="R01", guideline_version="g-v1", confidence="high",
        )
        service = CalfService(calf, MinimalSubmissionReader(_bundle_row()),
                              MinimalAnalysisReader(), MinimalStudentReader({}))

        with pytest.raises(LookupError, match="Submission not found."):
            service.import_error_annotations(7, [annotation])

        assert calf.calls == ["save_error_annotations"]

    def test_service_module_has_no_broad_import_any_repository_or_discovery(self):
        source = (ROOT / "app/services/calf.py").read_text(encoding="utf-8")
        assert "app.database" not in source
        assert "SQLite" not in source
        assert "self.repository" not in source
        assert "hasattr(" not in source
        tree = ast.parse(source)
        init = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        annotations = [
            arg.annotation
            for arg in [*init.args.args, *init.args.kwonlyargs]
            if arg.annotation is not None
        ]
        assert all(
            isinstance(annotation, ast.Name) and annotation.id in {
                "CalfDataPort", "CalfSubmissionReadPort",
                "CalfAnalysisReadPort", "CalfStudentReadPort",
            }
            for annotation in annotations
        )


class TestComposition:
    def _assert_wiring(self, api: FastAPI) -> None:
        database = api.state.repository
        calf = api.state.calf
        assert calf.calf_repository is database._calf_repository
        assert calf.submission_reader is database._submission_repository
        assert calf.analysis_reader is database._analysis_repository
        assert calf.student_reader is database._learner_repository
        assert calf.calf_repository._connection_manager is database._connection_manager
        assert calf.submission_reader._connection_manager is database._connection_manager
        assert calf.analysis_reader._connection_manager is database._connection_manager
        assert calf.student_reader._connection_manager is database._connection_manager
        assert not isinstance(calf, Database)

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

    def test_calf_router_source_does_not_construct_or_import_the_service(self):
        source = (ROOT / "app/api/routers/calf.py").read_text(encoding="utf-8")
        assert "get_calf" in source
        assert "CalfService(" not in source
        assert "app.services.calf" not in source

    def test_calf_api_report_import_and_trajectory_paths(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            assert client.get("/api/v1/submissions/999/calf").status_code == 404
            assert client.get("/api/v1/students/S999/calf-trajectories").status_code == 404
            payload = {
                "student_id": "F5A-API", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft",
                "timed": False, "tool_use": "none",
                "essay_text": "People should protect the environment. People should recycle more. "
                              "People should save water. People should plant trees. "
                              "People should reduce waste.",
            }
            created = client.post("/api/v1/submissions", json=payload)
            assert created.status_code == 201
            submission_id = created.json()["submission_id"]
            report = client.get(f"/api/v1/submissions/{submission_id}/calf")
            assert report.status_code == 200
            assert report.json()["interpretation_boundary"]
            imported = client.post(
                f"/api/v1/submissions/{submission_id}/error-annotations/import",
                json=[{
                    "submission_id": submission_id, "start_offset": 0, "end_offset": 5,
                    "original_text": payload["essay_text"][:5], "error_category": "grammar",
                    "correction": "People", "annotation_source": "human",
                    "annotation_status": "confirmed", "annotator_id": "R01",
                    "guideline_version": "error-guideline-v0.8.0", "confidence": "high",
                }],
            )
            assert imported.status_code == 201
            assert imported.json()["error_annotations"][0]["eligible_for_formal_accuracy"] is True
            invalid = client.post(
                f"/api/v1/submissions/{submission_id}/error-annotations/import",
                json=[{
                    "submission_id": submission_id, "start_offset": 0, "end_offset": 9999,
                    "original_text": "People", "error_category": "grammar",
                    "correction": "People", "annotation_source": "human",
                    "annotation_status": "confirmed", "guideline_version": "g-v1",
                    "confidence": "high",
                }],
            )
            assert invalid.status_code == 422
            trajectory = client.get("/api/v1/students/F5A-API/calf-trajectories")
            assert trajectory.status_code == 200
            assert trajectory.json()["student_id"] == "F5A-API"


class TestOperationalScriptConstructor:
    def test_script_uses_four_explicit_facade_owned_repositories(self):
        source = (ROOT / "scripts/verify_live_deepseek_v08.py").read_text(encoding="utf-8")
        assert source.count("CalfService(") == 1
        assert "local_repo._calf_repository" in source
        assert "local_repo._submission_repository" in source
        assert "local_repo._analysis_repository" in source
        assert "local_repo._learner_repository" in source
        assert "CalfService(local_repo)" not in source
        assert "CalfService(repository)" not in source
